import math

from flask import Flask, request, jsonify, abort
import json
import db
from sqlalchemy import exc
from sqlalchemy.orm import sessionmaker
from rq import Retry, Queue
from rq.job import Job
from worker import conn
from tasks import update_scan_confirm, update_order_status, orders_poll, invoices_poll
from exceptions import CancelledOrderException, OrderDoesNotExistException
from logging.config import dictConfig
import logging
import config
from freight_tables import item_matrix, order_matrix, single_dropship, dropship_zone, multi_parcel_dropship, \
    multi_ltl_dropship, dealer_zone
from zipcode_data import zip_codes
from math import ceil
from functools import reduce

app = Flask(__name__)

dictConfig(config.log_config)
app.config.from_pyfile('config.py', silent=True)

q = Queue(connection=conn)


# call to update dashboard database
@app.cli.command()
def order_poll():
    orders_poll()
    invoices_poll(config)


def order_filter(output, filter_value):
    if filter_value and filter_value.strip('}{') != '':
        filter_dict = json.loads(filter_value)
        print(filter_dict)
        try:
            if 'q' in filter_dict:
                output = fulltext_search(filter_dict['q'], output)
            else:
                for name in filter_dict.keys():
                    output = list(filter(lambda x: x[name] == filter_dict[name], output))
        except (KeyError, IndexError):
            pass
    return output


def item_filter(output, filter_value):
    if filter_value and filter_value.strip('}{') != '':
        filter_dict = json.loads(filter_value)
        print(filter_dict)
        try:
            if 'q' in filter_dict:
                output = fulltext_item_search(filter_dict['q'], output)
            else:
                for name in filter_dict.keys():
                    output = list(filter(lambda x: x[name] == filter_dict[name], output))
        except (KeyError, IndexError):
            pass
    return output


def order_sort(output, sort_value):
    if sort_value:
        sort_args = sort_value.strip('][').strip('"').split(',')
        rever = False
        sort_parm = sort_args[0].strip('"')
        if sort_args[1].strip('"') == 'DESC':
            rever = True
        try:
            output = sorted(output, key=lambda x: x[sort_parm], reverse=rever)
        except KeyError:
            logging.error(f'Key {sort_parm} does not exist')
    return output


def order_range(output, range_value):
    end = len(output)
    if range_value:
        total_size = len(output)
        range_args = range_value.strip('][').split(',')

        try:  # if begin and end aren't ints, make them 0 and len
            begin = int(range_args[0])
        except TypeError:
            begin = 0
        try:
            end = int(range_args[1]) + 1  # end is # of items to
        except TypeError:  # return, not list range
            end = total_size
        if end > len(output):  # if range is too long, wrap to max length
            end = total_size
        output = output[begin:end]
    return output, end


# POST is unsupported because we don't allow new orders
@app.route('/orders', methods=['GET', 'OPTIONS'])
def orders():
    Session = sessionmaker(bind=db.get_db())
    session = Session()
    if request.method == 'OPTIONS':
        session.close()
        response = build_cors_response('')
        response.headers['Allow'] = 'OPTIONS, GET'
        return response

    if request.method == 'GET' or 'OPTIONS':
        # return json for one order
        _sort = request.args.get('sort')
        _range = request.args.get('range')
        _filter = request.args.get('filter')

        result = session.execute("select order_json from dashboard_orders order by id")

        # pull order out of the tuple resultProxy returns
        js = result_process(result.fetchall())
        output = js
        if output:
            begin = 0

            output = order_filter(output, _filter)
            total_size = len(output)
            output = order_sort(output, _sort)
            output, end = order_range(output, _range)

            session.close()

            response = build_cors_response(output)
            response.headers['Content-Range'] = f'orders {begin}-{end}/{total_size}'
            response.headers['Access-Control-Expose-Headers'] = 'Content-Range'
            return response
        else:
            response = build_cors_response([{'id': 0}])
            response.headers['Content-Range'] = 'orders 0-0/0'
            response.headers['Access-Control-Expose-Headers'] = 'Content-Range'
            return response
    session.close()
    return


@app.route('/orders/<int:order_id>', methods=['GET', 'PUT', 'OPTIONS', 'DELETE'])
def order(order_id):
    Session = sessionmaker(bind=db.get_db())
    session = Session()
    # print(f'Calling {request.method}')
    if request.method == 'OPTIONS':
        response = build_cors_response('')
        response.headers['Allow'] = 'OPTIONS, GET, PUT'
        session.close()
        return response
    if request.method == 'PUT':
        try:
            status = request.json['status']
            order_id = request.json['order_id'].strip('"')
            logging.info('Changing status on order %s to %s', order_id, status)
            result = session.execute("select order_json from dashboard_orders where id=:order_id",
                                     {'order_id': order_id})

            js = result_process(result.fetchone())
            if js:
                if js['status'] == 'Cancelled':
                    raise CancelledOrderException
        except (KeyError, CancelledOrderException) as e:
            logging.error(e)
            return build_cors_response(f"Invalid input: {request.json}. "
                                       f"Please input a valid status and order id")

        job = update_order_status(order_id, status)
        if job['status'] == status:
            # sqlalchemy doesn't like parameterizing the text in to_jsonb() so we have to have 4 different queries
            if status == 'Released':
                update_result = session.execute("update dashboard_orders set order_json = "
                                                "jsonb_set(order_json, '{status}',to_jsonb('Released'::TEXT)) where id"
                                                " = :order_id;",
                                                {'order_id': order_id})
            if status == 'Fulfilled':
                update_result = session.execute("update dashboard_orders set order_json = "
                                                "jsonb_set(order_json, '{status}',to_jsonb('Fulfilled'::TEXT)) where id"
                                                " = :order_id",
                                                {'order_id': order_id})
            if status == 'Cancelled':
                update_result = session.execute("update dashboard_orders set order_json = "
                                                "jsonb_set(order_json, '{status}',to_jsonb('Cancelled'::TEXT)) where id"
                                                " = :order_id",
                                                {'order_id': order_id})
            if status == 'Delayed':
                update_result = session.execute("update dashboard_orders set order_json = "
                                                "jsonb_set(order_json, '{status}',to_jsonb('Delayed'::TEXT)) where id"
                                                " = :order_id",
                                                {'order_id': order_id})
            session.commit()
            if update_result:
                session.close()
                js['status'] = status
                response = build_cors_response(js)
                return response
        response = build_cors_response("Update Failed")
        return response

    elif request.method == 'DELETE':
        # deleting orders is unsupported
        session.close()
        return
    elif request.method == 'GET':
        # return json for one order
        result = session.execute("select order_json from dashboard_orders where id=':order_id'",
                                 {'order_id': order_id})
        session.close()
        js = result_process(result.fetchone())
        if js:
            response = build_cors_response(js)
            return response
        else:
            return build_cors_response('No Data')
    else:
        session.close()
    return build_cors_response('No Data')


@app.route('/invoices', methods=['GET', 'OPTIONS'])
def invoices():
    Session = sessionmaker(bind=db.get_db())
    session = Session()
    if request.method == 'OPTIONS':
        session.close()
        response = build_cors_response('')
        response.headers['Allow'] = 'OPTIONS, GET'
        return response

    if request.method == 'GET' or 'OPTIONS':
        # return json for one order
        _sort = request.args.get('sort')
        _range = request.args.get('range')
        _filter = request.args.get('filter')

        result = session.execute("select invoice_json from dashboard_invoices order by id")

        # pull order out of the tuple resultProxy returns
        js = result_process(result.fetchall())
        output = js
        if output:
            begin = 0

            output = order_filter(output, _filter)
            total_size = len(output)
            output = order_sort(output, _sort)
            output, end = order_range(output, _range)

            session.close()

            response = build_cors_response(output)
            response.headers['Content-Range'] = f'invoices {begin}-{end}/{total_size}'
            response.headers['Access-Control-Expose-Headers'] = 'Content-Range'
            return response
        else:
            response = build_cors_response([{'id': 0}])
            response.headers['Content-Range'] = 'invoices 0-0/0'
            response.headers['Access-Control-Expose-Headers'] = 'Content-Range'
            return response
    session.close()
    return


@app.route('/invoices/<int:order_id>', methods=['GET', 'PUT', 'OPTIONS', 'DELETE'])
def invoice(order_id):
    Session = sessionmaker(bind=db.get_db())
    session = Session()
    if request.method == 'OPTIONS':
        response = build_cors_response('')
        response.headers['Allow'] = 'OPTIONS, GET, PUT'
        session.close()
        return response
    elif request.method == 'PUT':
        # deleting orders is unsupported
        session.close()
        return
    elif request.method == 'DELETE':
        # deleting orders is unsupported
        session.close()
        return
    elif request.method == 'GET':
        # return json for one order
        result = session.execute("select invoice_json from dashboard_invoices where id=':order_id'",
                                 {'order_id': order_id})
        session.close()
        js = result_process(result.fetchone())
        if js:
            response = build_cors_response(js)
            return response
        else:
            return build_cors_response('No Data')
    else:
        session.close()
    return build_cors_response('No Data')


@app.route('/scan_confirm', methods=['GET', 'PUT', 'OPTIONS'])
def scan_confirms():
    if request.method == 'OPTIONS':
        response = build_cors_response('')
        response.headers['Allow'] = 'OPTIONS, GET, PUT'
        return response

    if request.method == 'PUT':
        try:
            upc = request.form['upc_code']
            order_id = request.form['order_id']
            logging.info('Order %s scanned, upc %s', order_id, upc)
            Session = sessionmaker(bind=db.get_db())
            session = Session()
            result = session.execute("select order_json from dashboard_orders where id=:order_id",
                                     {'order_id': order_id.strip('"')})
            session.close()
            js = result_process(result.fetchone())
            # print(js)
            if js is not None:
                if js['status'] == 'Cancelled':
                    raise CancelledOrderException(order_id)
                for line in js['lines']:
                    if float(line['qty_scanned']) >= float(line['qty']) and upc == line['upc_code']:
                        raise OrderDoesNotExistException(order_id)

            else:
                raise OrderDoesNotExistException(order_id)

        except (KeyError, CancelledOrderException, OrderDoesNotExistException) as e:
            logging.error(e)
            return build_cors_response(f"Error: {e}")

        job = q.enqueue_call(
            func=update_scan_confirm, args=(upc, order_id), result_ttl=86400,
            retry=Retry(max=3, interval=60)
        )
        return build_cors_response(job.get_id())

    if request.method == 'GET':
        # TODO: Return list of all jobs
        _sort = request.args.get('sort')
        _range = request.args.get('range')
        _filter = request.args.get('filter')
        job_ids = q.finished_job_registry.get_job_ids()
        job_ids += q.started_job_registry.get_job_ids()
        job_ids += q.deferred_job_registry.get_job_ids()
        job_ids += q.failed_job_registry.get_job_ids()
        job_ids += q.scheduled_job_registry.get_job_ids()
        output = []
        job_count = 0
        for job in job_ids:
            job_data = Job.fetch(job, connection=conn)
            output.append({'id': job_count, 'job_no': job, 'order': job_data.args[1], 'upc': job_data.args[0]})
            job_count += 1

        if output:
            begin = 0
            end = len(output)
            total_size = len(output)

            if _filter:
                pass

            if _sort:

                sort_args = _sort.strip('][').split(',')
                rever = False
                sort_parm = sort_args[0].strip('"')
                if sort_args[1].strip('"') == 'DESC':
                    rever = True
                try:
                    output = sorted(output, key=lambda x: x['id'], reverse=rever)
                except KeyError:
                    logging.error(f'Key {sort_parm} does not exist')

            if _range:
                range_args = _range.strip('][').split(',')

                try:  # if begin and end aren't ints, make them 0 and len
                    begin = int(range_args[0])
                except TypeError:
                    begin = 0
                try:
                    end = int(range_args[1]) + 1  # end is # of items to
                except TypeError:  # return, not list range
                    end = total_size
                if end > len(output):  # if range is too long, wrap to max length
                    end = total_size
                output = output[begin:end]

            response = build_cors_response(output)
            response.headers['Content-Range'] = f'orders {begin}-{end}/{total_size}'
            response.headers['Access-Control-Expose-Headers'] = 'Content-Range'

            return response
        else:
            response = build_cors_response([{'id': 0}])
            response.headers['Content-Range'] = 'orders 0-0/0'
            response.headers['Access-Control-Expose-Headers'] = 'Content-Range'
            return response


@app.route('/scan_confirm/<job_key>', methods=['GET'])
def scan_confirm(job_key):
    job = Job.fetch(job_key, connection=conn)

    if job.is_finished:
        return jsonify({'result': str(job.result), 'args': job.args}), 200
    else:
        return "Error on job", 202


@app.route('/items', methods=['GET', 'OPTIONS'])
def items():
    Session = sessionmaker(bind=db.get_dyna_db())
    session = Session()
    if request.method == 'OPTIONS':
        session.close()
        response = build_cors_response('')
        response.headers['Allow'] = 'OPTIONS, GET'
        return response

    if request.method == 'GET' or 'OPTIONS':
        # return json for one order
        _sort = request.args.get('sort')
        _range = request.args.get('range')
        _filter = request.args.get('filter')

        result = session.execute("select itemid, Descr1, isnull(x04472490_Weight, 0) weight, "
                                 "isnull(x04472490_Height, 0) height, isnull(x04472490_Width, 0) width, "
                                 "isnull(x04472490_Depth, 0) depth from item order by itemid")

        # pull order out of the tuple resultProxy returns
        js = result_item_process(result.fetchall())
        output = js
        if output:
            begin = 0

            output = item_filter(output, _filter)
            total_size = len(output)
            output = order_sort(output, _sort)
            output, end = order_range(output, _range)

            session.close()

            response = build_cors_response(output)
            response.headers['Content-Range'] = f'items {begin}-{end}/{total_size}'
            response.headers['Access-Control-Expose-Headers'] = 'Content-Range'
            return response
        else:
            response = build_cors_response([{'id': 0}])
            response.headers['Content-Range'] = 'items 0-0/0'
            response.headers['Access-Control-Expose-Headers'] = 'Content-Range'
            return response
    session.close()
    return


@app.route('/items/<string:item_id>', methods=['GET', 'PUT', 'OPTIONS', 'DELETE'])
def item(item_id):
    Session = sessionmaker(bind=db.get_dyna_db())
    session = Session()
    if request.method == 'OPTIONS':
        response = build_cors_response('')
        response.headers['Allow'] = 'OPTIONS, GET, PUT'
        session.close()
        return response
    elif request.method == 'PUT':
        # deleting orders is unsupported
        session.close()
        return
    elif request.method == 'DELETE':
        # deleting orders is unsupported
        session.close()
        return
    elif request.method == 'GET':
        logging.debug(f'/items: {request.content_type}')
        # return json for one order
        # this is a sql injection risk, but parameterized queries through sqlalchemy don't seem to work with pyodbc
        result = session.execute(f"select item.itemid, Descr1, isnull(x04472490_Weight, 0) weight, "
                                 f"isnull(x04472490_Height, 0) height, isnull(x04472490_Width, 0) width, "
                                 f"isnull(x04472490_Depth, 0) depth, isnull(category.descr, '') [category],"
                                 f"isnull(zzitemextended.gfpsize, '') gfpsize "
                                 f"from item "
                                 f"left outer join zzitemextended on item.initemid = zzitemextended.initemid "
                                 f"left outer join category on item.excategoryid = category.incategoryid "
                                 f"where item.itemid = '{item_id}'")
        js = result_item_process(result.fetchone())
        print(js)
        session.close()
        if js:
            response = build_cors_response(js)
            return response
        else:
            abort(404)
    else:
        session.close()
    return build_cors_response('No Data')


@app.route('/order_status', methods=['GET'])
def order_status():
    po_num = request.args.get('po')
    shipto_zip = request.args.get('shipto_zip')
    with db.get_dyna_db().connect() as con:
        rs = con.execute('''
        SELECT
            ShipVia as ship_via,
            CASE InvoiType WHEN 51 THEN NULL ELSE ShipDate END AS ship_date,
            ShipTo as ship_to,
            PONum as po_num,
            TrackingNo as tracking_num
        FROM InvoiHdr
        WHERE
            InvoiType IN (1, 51)
            AND PONum = ? --{po}
            AND usrZipcodes = ?
            ''', po_num, shipto_zip).fetchall()
    order_list = []
    for line in rs:
        order_list.append({  # insert header record
            "poNum": line['po_num'],
            "shipTo": line['ship_to'],
            "shipVia": line['ship_via'],
            "shipDate": line['ship_date'].strftime("%Y-%m-%d") if line['ship_date'] is not None else '',
            "trackingNo": line['tracking_num'] if line['tracking_num'] is not None else ''
        })
    if order_list:
        return build_cors_response({'orders': order_list})
    else:
        return build_cors_response({'orders': ''})


def dealer_quote(api_request):
    # set up GFPZone, Number of Units, and Size for each line item
    # Determine flat charge for the entire shipment
    # For each line, determine that unit's contribution
    # Return shipment charge + each line charge
    total_units = 0
    flat_rate = 0
    item_rate = 0
    ship_to_zip = api_request['shipToZip']
    total_weight = reduce(lambda x, y: x + y, [float(x['itemWeight']) * int(x['itemQty'])
                                               for x in api_request['lines']])

    if len(api_request['lines']) > 1:
        if total_weight > 150:
            freight_type = 'ltl'
        else:
            freight_type = 'parcel'
    else:
        if total_weight > 80:
            freight_type = 'ltl'
        else:
            freight_type = 'parcel'

    try:
        ship_to_state = zip_codes[ship_to_zip]['state_code']
        zone = dealer_zone[ship_to_state]
    except KeyError:
        return 'Unknown Location'

    if ship_to_state == 'NY':
        if zip_codes[ship_to_zip]['county'] in ['Queens', 'Bronx', 'Kings', 'New York', 'Richmond']:  # NYC
            zone = 1

    for line in api_request['lines']:
        if line['unitSize'] and line['unitSize'] != '':
            if line['unitSize'] != 'Parcel':
                total_units += float(line['itemQty'])
            else:
                total_units += float(line['itemQty']) * 0.25
    total_units = int(ceil(total_units))

    total_pkg_units = '1'

    if 1 < total_units <= 3:
        total_pkg_units = '2-3'
    elif 3 < total_units <= 6:
        total_pkg_units = '4-6'
    elif 6 < total_units <= 11:
        total_pkg_units = '7-11'
    elif 11 < total_units <= 15:
        total_pkg_units = '12-15'
    elif 15 < total_units <= 19:
        total_pkg_units = '16-19'
    elif 19 < total_units <= 23:
        total_pkg_units = '20-23'
    elif 23 < total_units <= 29:
        total_pkg_units = '24-29'
    elif 29 < total_units <= 35:
        total_pkg_units = '30-35'
    elif 35 < total_units <= 47:
        total_pkg_units = '36-47'
    elif total_units > 47:
        total_pkg_units = '48+'

    try:
        flat_rate = order_matrix[zone][total_pkg_units]
    except KeyError:
        pass

    if flat_rate == 0:
        size_list = {}
        for line in api_request['lines']:
            if line['unitSize'] and line['unitSize'].lower() != '':
                line['unitSize'] = line['unitSize'].lower()
                if line['unitSize'] != 'parcel':
                    if line['unitSize'] in size_list:
                        size_list[line['unitSize']] += int(line['itemQty'])
                    else:
                        size_list[line['unitSize']] = int(line['itemQty'])
                else:
                    if line['unitSize'] in size_list:
                        size_list[line['unitSize']] += int(line['itemQty']) * 0.25
                    else:
                        size_list[line['unitSize']] = int(line['itemQty']) * 0.25

        if 'parcel' in size_list:
            size_list['parcel'] = int(math.ceil(size_list['parcel']))
            # print(size_list['Parcel'])
        for size in size_list.keys():
            item_rate += item_matrix[zone][total_pkg_units][size] * size_list[size]

    try:
        if api_request['liftGate'] == 'True':
            flat_rate += 75
    except KeyError:
        pass

    return {'total': flat_rate + item_rate, 'weight': total_weight, 'type': freight_type}


def drop_ship_quote(api_request):
    # check to see if it's over-sized
    # check to see if it's LTL
    # if one piece, determine its freight factor
    # sum total weight and dim weight (round up to nearest 100 pounds)
    # lookup zone
    # look up rate on table
    total_qty = reduce(lambda x, y: x + y, [int(x['itemQty']) for x in api_request['lines']])
    total_weight = reduce(lambda x, y: x + y, [float(x['itemWeight']) * int(x['itemQty'])
                                               for x in api_request['lines']])
    max_weight = reduce(lambda x, y: x if x > y else y, [float(x['itemHeight']) * int(x['itemQty'])
                                                         for x in api_request['lines']])
    total_volume = reduce(lambda x, y: x + y, [float(x['itemHeight']) * float(x['itemDepth']) * float(x['itemWidth']) *
                                               int(x['itemQty']) for x in api_request['lines']])
    total_height = reduce(lambda x, y: x + y, [float(x['itemHeight']) * int(x['itemQty'])
                                               for x in api_request['lines']])

    total_cubic_feet = total_volume / 1728.0

    total_dim_weight = total_volume / 139.0 * 1.3  # add 30% for inefficient packing
    # logging.debug(f'''total qty: {total_qty}, total weight: {total_weight}, max weight: {max_weight},
    #              total volume: {total_volume}, total height: {total_height}, total dim weight: {total_dim_weight},
    #              total cubic feet: {total_cubic_feet}''')

    try:
        ship_to_zip = api_request['shipToZip']
        ship_to_state = zip_codes[ship_to_zip]['state_code']
    except ValueError:
        return {'total': 'Unknown Location', 'weight': total_weight}
    except KeyError:
        return {'total': 'Unknown Location', 'weight': total_weight}

    try:
        zone, surcharge, multi_surcharge = dropship_zone[ship_to_state]
    except KeyError:
        return {'total': 'Unknown Location', 'weight': total_weight}
    if zone == -1:
        return {'total': 'Unknown Location', 'weight': total_weight}

    if total_qty == 1:
        # single-piece shipment
        if total_weight > 80.0:
            freight_type = 'ltl'
        else:
            freight_type = 'parcel'
        if api_request['lines'][0]['itemNumber'][:3] == 'C48' or \
                api_request['lines'][0]['itemNumber'][:3] == 'C60':
            freight_factor = '7'
        elif api_request['lines'][0]['category'] == 'Range' or api_request['lines'][0]['category'] == 'Wall Oven':
            freight_factor = '5A'
        else:
            if total_weight > 400.0:
                freight_factor = '9'
            elif total_weight > 300.0:
                freight_factor = '8'
            elif total_weight > 200.0:
                freight_factor = '7'
            elif total_weight > 150.0:
                freight_factor = '6'
            elif total_weight > 70.0 and total_height > 30.0:
                freight_factor = '5'
            elif total_dim_weight > 75.0:
                freight_factor = '4A'
            elif total_dim_weight > 60.0:
                freight_factor = '4'
            elif total_dim_weight > 30.0 or total_weight > 30.0:
                freight_factor = '3'
            elif total_dim_weight > 20.0 or total_weight > 20.0:
                freight_factor = '2'
            else:
                freight_factor = '1'
        item_rate = single_dropship[freight_factor][zone]
        surcharge_amt = item_rate * surcharge * .01
    else:
        # multi-piece shipment
        if total_cubic_feet > 700.0:
            item_rate = 0
            return {'total': 'Shipment Too Large', 'weight': total_weight}
        else:
            # check LTL or Parcel
            if max_weight > 70.0 or total_volume > 18000.0 or total_weight > 80.0 or total_dim_weight > 250.0:
                freight_type = 'ltl'  # LTL
                whole_pallet = 0
                half_pallet = 0
                small_pallet = 0
                for x in api_request['lines']:
                    if int(x['itemWeight']) > 70 and int(x['itemHeight']) > 42:
                        whole_pallet += 1 * int(x['itemQty'])
                    if int(x['itemWeight']) > 70.0 and int(x['itemHeight']) <= 42:
                        half_pallet += 0.5 * int(x['itemQty'])
                    elif int(x['itemWeight']) < 70:
                        small_pallet += float(x['itemHeight']) * float(x['itemWidth']) * float(x['itemDepth']) \
                                        * int(x['itemQty'])

                half_pallet = math.ceil(half_pallet)
                small_pallet = math.ceil(small_pallet / 51840.0)
                total_pallet = whole_pallet + half_pallet + small_pallet
                extra_units = 0

                total_weight += total_pallet * 25.0

                print(f'total pallets: {total_pallet} -- whole pallets: {whole_pallet}, half pallets: {half_pallet}, '
                      f'small pallets: {small_pallet}  Updated total weight: {total_weight}')

                if total_pallet <= 9:
                    if total_weight < 100:
                        freight_factor = 'up to 100'
                    elif total_weight < 150:
                        freight_factor = '100 to 149'
                    elif total_weight < 200:
                        freight_factor = '150 to 199'
                    elif total_weight < 300:
                        freight_factor = '200 to 299'
                    elif total_weight < 400:
                        freight_factor = '300 to 399'
                    elif total_weight < 500:
                        freight_factor = '400 to 499'
                    elif total_weight < 600:
                        freight_factor = '500 to 599'
                    elif total_weight < 700:
                        freight_factor = '600 to 699'
                    elif total_weight < 800:
                        freight_factor = '700 to 799'
                    elif total_weight < 900:
                        freight_factor = '800 to 899'
                    elif total_weight < 1000:
                        freight_factor = '900 to 999'
                    elif total_weight < 1100:
                        freight_factor = '1000 to 1099'
                    else:
                        freight_factor = '1100+'
                        extra_units = (total_weight - 1000) // 100
                        logging.info(extra_units)

                    item_rate = multi_ltl_dropship[freight_factor][zone]

                    if extra_units > 0:
                        if zone == 1:
                            item_rate += extra_units * 20
                        elif zone == 2:
                            item_rate += extra_units * 30
                        elif zone == 3:
                            item_rate += extra_units * 40
                else:
                    return {'total': 'Shipment Too Large for LTL', 'weight': total_weight}
            else:  # parcel
                freight_type = 'parcel'
                if max(total_weight, total_dim_weight) < 50.0:
                    freight_factor = 'up to 50'
                elif max(total_weight, total_dim_weight) < 80.0:
                    freight_factor = '50 to 79'
                elif max(total_weight, total_dim_weight) < 120.0:
                    freight_factor = '80 to 119'
                else:
                    freight_factor = '120 to 150'
                item_rate = multi_parcel_dropship[freight_factor][zone]
            surcharge_amt = item_rate * multi_surcharge * .01
    return {'total': item_rate + surcharge_amt, 'weight': total_weight, 'type': freight_type}


@app.route('/freight_quote', methods=['PUT', 'OPTIONS'])
def freight_quote():
    if request.method == 'OPTIONS':
        response = build_cors_response('')
        response.headers['Allow'] = 'OPTIONS', 'PUT'
        return response
    if request.method == 'PUT':
        logging.info(f'Content-Type: {request.content_type}')
        logging.debug(f'Content-Length: {request.content_length}')
        logging.debug(f'Content-Encoding: {request.content_encoding}')
        logging.debug(request.data)
        logging.debug(request.form)
        if request.content_type.startswith('application/json'):
            req = request.json
        elif request.content_type.startswith('application/x-www-form-urlencoded'):   #Netsuite sends data as a form
            req = request.form[0]
        if req['custFreightType'] == "Dealer":
            rate_total = dealer_quote(req)
        elif req['custFreightType'] == "Drop Ship":
            rate_total = drop_ship_quote(req)
        else:
            return build_cors_response(f"Error: Not a valid freight type")
        logging.info(rate_total)
        return build_cors_response(rate_total)


@app.errorhandler(401)
@app.route('/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        response = build_cors_response('')
        response.headers['Allow'] = 'OPTIONS, POST'
        return response
    if request.method == 'POST':
        username = request.json['username']
        password = request.json['password']
        if username == 'shipping' and password == 'shipping':
            return build_cors_response({'id': 'shipping', 'fullName': 'Shipping Manager'})
        elif username == 'shipping':
            return build_cors_response({'error': 'incorrect password'}, '401')
        else:
            return build_cors_response({'id': 'guest', 'fullName': 'Guest'})


def fulltext_search(text, order_list):
    lower_text = text.lower()
    output_list = []
    for o in order_list:
        if lower_text in o['id'].lower() or \
                lower_text in o['ship_via'].lower() or \
                lower_text in o['status'].lower() or \
                lower_text in o['ship_from'].lower() or \
                lower_text in o['po_number'].lower() or \
                lower_text in o['order_type'].lower() or \
                lower_text in o['cust_name'].lower() or \
                lower_text in o['ship_date']:
            output_list.append(o)

        for line in o['lines']:
            if lower_text in line['item_id'].lower() or \
                    lower_text in line['upc_code'].lower():
                output_list.append(o)
                break
    return output_list


def fulltext_item_search(text, item_list):
    lower_text = text.lower()
    output_list = []
    for o in item_list:
        if lower_text in o['item_id'].lower() or \
                lower_text in o['descr1'].lower():
            output_list.append(o)
    return output_list


def result_process(result):
    if result:
        if len(result) > 1:
            return list(map(lambda x: x[0], result))
        else:
            return result[0]


def result_item_process(result):
    if result:
        if isinstance(result, list):
            return [{'item_id': x[0], 'descr1': x[1], 'weight': x[2], 'height': x[3], 'width': x[4], 'depth': x[5],
                     'category': x[6], 'gfpsize': x[7]} for x in result]
        else:
            return [{'item_id': result[0], 'descr1': result[1], 'weight': result[2], 'height': result[3],
                     'width': result[4], 'depth': result[5], 'category': result[6], 'gfpsize': result[7]}]


def build_cors_response(output, status='', **kwargs):
    response = jsonify(output, **kwargs)
    if status != '':
        response.status_code = status
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = '*'
    response.headers['Access-Control-Allow-Methods'] = '*'
    return response

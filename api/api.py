# TODO: better CORS support
# TODO: support filtering in /orders
import math

from flask import Flask, request, jsonify
import json
import db
from sqlalchemy import exc
from sqlalchemy.orm import sessionmaker
from rq import Retry, Queue
from rq.job import Job
from worker import conn
from tasks import update_scan_confirm, update_order_status
from exceptions import CancelledOrderException, OrderDoesNotExistException
from logging.config import dictConfig
import logging
import config
from gfp import item_matrix, order_matrix, nyc_zip
from math import ceil

app = Flask(__name__)

dictConfig(config.log_config)
app.config.from_pyfile('config.py', silent=True)

q = Queue(connection=conn)


# call to update dashboard database
@app.cli.command()
def order_poll():
    try:
        if config.mode == 'development':
            date = '\'2021-05-25\''
        else:
            date = 'cast(getdate() as date)'
    except KeyError:
        date = 'cast(getdate() as date)'

    with db.get_dyna_db().connect() as con:
        rs = con.execute(
            f"""select h.invoiid as id, 
                h.shipvia as ship_via, 
                h.OrderId as order_id,
                h.x04472474_ShippedDate as ship_date,
                isnull(h.PONum, '') as po_number,
                case when h.invoitype = 1 then 'Invoiced'
                    when h.invoitype = 50 then 'Estimate'
                    when h.invoitype = 51 then 'Open'
                    else 'Unknown' end as order_type,
                w.WarehouseId as ship_from,
                case when (x04472474_PendingCancellation = 1  or usrCancelled = 1) then 'Cancelled'
                        when (x04472474_BLStatus = 'Closed' or x04472474_BLStatus = 'Ready to Ship' or 
                            x04472474_BLStatus = 'Fulfilled') then 'Fulfilled'
                        when x04472474_Delayed = 1 then 'Delayed'
                        when (x04472474_BLStatus is NULL or 
                            (x04472474_BLStatus <> 'Ready to Ship' and x04472474_BLStatus <> 'Closed')) then 'Released'
                    end as 'status',
                d.Qty as qty,
                d.usrBarcodeScanCount as qty_scanned,
                isnull(i.UPCCode,'') as upc_code,
                i.ItemId as item_id,
                d.InInvoiDetId as line_id
            from InvoiHdr as h inner join InvoiDet as d on h.InInvoiId = d.ExInvoiId
            inner join Item as i on d.ExItemId = i.InItemId
            inner join Warehouse as w on d.usrShipFromWarehouse = w.InWarehouseId
            inner join Cust as c on h.ExCustID = c.InCustId
            where /*h.[x04472474_ShippedDate] = '2021-05-18' AND*/ h.[InvoiType] = 51 AND 
                d.[usrShipFromWarehouse] in (1, 4, 8) AND h.[x04472474_Shipped] = 1 AND 
                /*h.[ShipVia] != '' and*/ i.itemid not in ('j4g','j5u','x1','j4', 'j8') AND
                c.custid not in ('zemp')
        """).fetchall()

    new_orders = []
    idx = 0
    order_list = {}  # store pos so we can insert if lines aren't in order
    for line in rs:
        # look for unique header record
        if line.id not in order_list:
            new_orders.append({  # insert header record
                "id": line['id'],
                "ship_via": line['ship_via'] if line['ship_via'] is not None else '',
                "order_id": line['order_id'],
                "ship_date": line['ship_date'].strftime("%Y-%m-%d"),
                "order_type": line['order_type'],
                "status": line['status'],
                "ship_from": line['ship_from'],
                "po_number": line['po_number'].replace("'", "''"),
                "lines": []
            })
            order_list[line['id']] = idx
            idx += 1

        new_orders[order_list[line['id']]]["lines"].append({
            "qty": str(line['qty']),
            "qty_scanned": str(line['qty_scanned']),
            "upc_code": line['upc_code'],
            "item_id": line['item_id'],
            "line_id": line['line_id']
        })
    # update data store with new_orders
    Session = sessionmaker(bind=db.get_db())
    session = Session()

    try:
        session.execute('delete from dashboard_orders')
        for item in new_orders:
            session.execute(f"insert into dashboard_orders values({item['id']}, '{json.dumps(item)}')")
        session.commit()
    except exc.SQLAlchemyError as e:
        logging.error(e)
        session.rollback()
    finally:
        session.close()


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
            end = len(output)
            total_size = len(output)

            if _filter and _filter.strip('}{') != '':
                filter_dict = json.loads(_filter)
                print(filter_dict)
                try:
                    if 'q' in filter_dict:
                        output = fulltext_search(filter_dict['q'], output)
                    else:
                        for name in filter_dict.keys():
                            output = list(filter(lambda x: x[name] == filter_dict[name], output))
                    end = len(output)
                    total_size = len(output)
                except (KeyError, IndexError):
                    pass

            if _sort:
                sort_args = _sort.strip('][').strip('"').split(',')
                rever = False
                sort_parm = sort_args[0].strip('"')
                if sort_args[1].strip('"') == 'DESC':
                    rever = True
                try:
                    output = sorted(output, key=lambda x: x[sort_parm], reverse=rever)
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
            print(js)
            if js is not None:
                if js['status'] == 'Cancelled':
                    raise CancelledOrderException(order_id)
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


@app.route('/freight_quote', methods=['PUT'])
def freight_quote():
    if request.method == 'PUT':
        # set up GFPZone, Number of Units, and Size for each line item
        # Determine flat charge for the entire shipment
        # For each line, determine that unit's contribution
        # Return shipment charge + each line charge
        gfp_zone = -1
        total_units = 0
        flat_rate = 0
        item_rate = 0
        if request.json['shipToState'] == 'NY':
            if request.json['shipToZip'] in nyc_zip:  # NYC
                gfp_zone = 1
        elif request.json['GFPZone'] == "2":
            gfp_zone = 2
        elif request.json['GFPZone'] == "3":
            gfp_zone = 3
        elif request.json['GFPZone'] == "4":
            gfp_zone = 4

        if gfp_zone == -1:
            return build_cors_response({'total': 0})

        for line in request.json['lines']:
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
            flat_rate = order_matrix[gfp_zone][total_pkg_units]
        except KeyError:
            pass

        size_list = {}
        if flat_rate == 0:
            for line in request.json['lines']:
                if line['unitSize'] and line['unitSize'] != '':
                    if line['unitSize'] != 'Parcel':
                        if line['unitSize'] in size_list:
                            size_list[line['unitSize']] += int(line['itemQty'])
                        else:
                            size_list[line['unitSize']] = int(line['itemQty'])
                    else:
                        if line['unitSize'] in size_list:
                            size_list[line['unitSize']] += int(line['itemQty']) * 0.25
                        else:
                            size_list[line['unitSize']] = int(line['itemQty']) * 0.25

            if 'Parcel' in size_list:
                size_list['Parcel'] = int(math.ceil(size_list['Parcel']))
                print(size_list['Parcel'])

            for size in size_list.keys():
                item_rate += item_matrix[gfp_zone][total_pkg_units][size] * size_list[size]

        return build_cors_response({'total': flat_rate + item_rate})


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
                lower_text in o['order_type'].lower():
            output_list.append(o)

        for line in o['lines']:
            if lower_text in line['item_id'].lower() or \
                    lower_text in line['upc_code'].lower():
                output_list.append(o)
                break
    return output_list


def result_process(result):
    if result:
        if len(result) > 1:
            return list(map(lambda x: x[0], result))
        else:
            return result[0]


def build_cors_response(output, status='', **kwargs):
    response = jsonify(output, **kwargs)
    if status != '':
        response.status_code = status
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = '*'
    response.headers['Access-Control-Allow-Methods'] = '*'
    return response

# TODO: better CORS support
# TODO: support filtering in /orders
from flask import Flask, request, jsonify
import json
import db
from sqlalchemy import exc
from sqlalchemy.orm import sessionmaker
from rq import Retry, Queue
from rq.job import Job
from worker import conn
from tasks import update_scan_confirm
from exceptions import CancelledOrderException
from logging.config import dictConfig
import logging
import config

app = Flask(__name__)

dictConfig(config.log_config)
app.config.from_pyfile('config.py', silent=True)

q = Queue(connection=conn)


# call to update dashboard database
@app.cli.command()
def order_poll():
    date = '\'2021-03-04\''  # 'getdate()'

    with db.get_dyna_db().connect() as con:
        rs = con.execute(
            f"""select h.invoiid as id, 
                h.shipvia as ship_via, 
                h.OrderId as order_id,
                h.x04472474_ShippedDate as ship_date,
                case when h.invoitype = 1 then 'Invoiced'
                    when h.invoitype = 50 then 'Estimate'
                    when h.invoitype = 51 then 'Open'
                    else 'Unknown' end as order_type,
                w.WarehouseId as ship_from,
                case when x04472474_BLStatus is NULL then 'Open'
                    when x04472474_BLStatus = 'Ready to Ship' then 'Closed'
                    when x04472474_PendingCancellation = 1  then 'Cancelled'
                    end as 'status',
                d.Qty as qty,
                d.usrBarcodeScanCount as qty_scanned,
                isnull(i.UPCCode,'') as upc_code,
                i.ItemId as item_id,
                d.InInvoiDetId as line_id
            from InvoiHdr as h inner join InvoiDet as d on h.InInvoiId = d.ExInvoiId
            inner join Item as i on d.ExItemId = i.InItemId
            inner join Warehouse as w on d.usrShipFromWarehouse = w.InWarehouseId
            where h.[x04472474_ShippedDate] = {date} AND h.[InvoiType] = 51 AND 
                d.[usrShipFromWarehouse] = 4 AND h.[x04472474_Shipped] = 1 AND 
                h.[ShipVia] != '' and i.itemid not in ('j4g','j5u','x1','j4', 'j8')
        """).fetchall()

    new_orders = []
    idx = 0
    order_list = {}  # store pos so we can insert if lines aren't in order
    for line in rs:
        # look for unique header record
        if line.id not in order_list:
            new_orders.append({  # insert header record
                "id": line['id'],
                "ship_via": line['ship_via'],
                "order_id": line['order_id'],
                "ship_date": line['ship_date'].strftime("%Y-%m-%d"),
                "order_type": line['order_type'],
                "status": line['status'],
                "lines": []
            })
            order_list[line['id']] = idx
            idx += 1

        new_orders[order_list[line['id']]]["lines"].append({
            "qty": str(line['qty']),
            "qty_scanned": str(line['qty_scanned']),
            "ship_from": line['ship_from'],
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

            if _filter:
                str_filter = list(map(lambda x: x.strip('"'), _filter.strip('}{').split(':')))
                try:
                    name = str_filter[0]
                    values = str_filter[1]
                # filter_dict = {}
                    output = list(filter(lambda x: x[name] == values, output))
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


@app.route('/orders/<int:order_id>', methods=['GET', 'PUT', 'DELETE'])
def order(order_id):
    Session = sessionmaker(bind=db.get_db())
    session = Session()

    if request.method == 'OPTIONS':
        response = build_cors_response('')
        response.headers['Allow'] = 'OPTIONS, GET'
        session.close()
        return response
    if request.method == 'PUT':
        # updating orders are unsupported for now
        session.close()
        return
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
            Session = sessionmaker(bind=db.get_db())
            session = Session()
            result = session.execute("select order_json from dashboard_orders where id=:order_id",
                                     {'order_id': order_id.strip('"')})
            session.close()
            js = result_process(result.fetchone())
            if js:
                if js['status'] == 'Cancelled':
                    raise CancelledOrderException
        except (KeyError, CancelledOrderException):
            return build_cors_response(f"Invalid input: {request.json}. "
                                       f"Please input a UPC code and order id")

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
            output.append({'id': job_count, 'job_no': job})
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
        return str(job.result), 200
    else:
        return "Error on job", 202


def result_process(result):
    if result:
        if len(result) > 1:
            return list(map(lambda x: x[0], result))
        else:
            return result[0]


def build_cors_response(output):
    response = jsonify(output)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = '*'
    response.headers['Access-Control-Allow-Methods'] = '*'
    return response

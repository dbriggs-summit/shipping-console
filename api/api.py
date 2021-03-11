import time
from sqlalchemy import create_engine, exc
from sqlalchemy.orm import sessionmaker

from flask import Flask, request
import config
import json
import db

dyna_server = config.dynaServer
dyna_db = config.dynaDBName
dyna_user = config.dynaUserName
dyna_password = config.dynaPassword
postgres_server = config.postgresServer
postgres_db = config.postgresDBName
postgres_user = config.postgresUserName
postgres_password = config.postgresPassword

dynacom_eng = \
    create_engine(f'mssql+pyodbc://{dyna_user}:{dyna_password}@{dyna_server}/'
                  f'{dyna_db}?driver=SQL Server')
postgres_eng = \
    create_engine(f'postgresql://{postgres_user}:{postgres_password}@'
                  f'{postgres_server}:5432/{postgres_db}')

app = Flask(__name__)
db.init_app(app)

app.config.from_pyfile('config.py', silent=True)


@app.route('/time')
def get_current_time():
    return {'time': time.time()}


# call to update dashboard database
@app.cli.command()
def order_poll():
    date = '\'2021-03-04\''  # 'getdate()'

    with dynacom_eng.connect() as con:
        rs = con.execute(
            f"""select h.invoiid as id, 
                h.shipvia as ship_via, 
                h.OrderId as order_id,
                h.x04472474_ShippedDate as ship_date,
                h.InvoiType as order_type,
                w.WarehouseId as ship_from,
                case when x04472474_BLStatus is NULL then 'Open'
                    when x04472474_BLStatus = 'Ready to Ship' then 'Closed'
                    --when  then 'Cancelled'
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
                h.[ShipVia] != '' and i.itemid not in ('j4g','j5u','x1','j4')
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
    Session = sessionmaker(bind=postgres_eng)
    session = Session()

    try:
        session.execute('delete from dashboard_orders')
        for order in new_orders:
            session.execute(f"insert into dashboard_orders values({order['id']}, '{json.dumps(order)}')")
        session.commit()
    except exc.SQLAlchemyError as e:
        print(e)
        session.rollback()
    finally:
        session.close()


@app.route('/orders', methods=('GET', 'POST'))
def orders():
    Session = sessionmaker(bind=postgres_eng)
    session = Session()
    if request.method == 'GET':
        #return json for one order
        result = session.execute("select id, order_json from dashboard_orders")
        session.close()
        js = result.fetchall()
        if js:
            return js
    return


@app.route('/orders/<int:id>', methods=('GET', 'PUT', 'DELETE'))
def order(id):
    Session = sessionmaker(bind=postgres_eng)
    session = Session()
    if request.method == 'PUT':
        #process update code
        return
    elif request.method == 'DELETE':
        #deleting orders is unsupported
        return
    elif request.method == 'GET':
        #return json for one order
        result = session.execute("select id, order_json from dashboard_orders where id=':order_id'",
                                 {'order_id': id})
        session.close()
        js = result.fetchone()
        if js:
            return js[1]
    return

# @app.route('/update_line')
# def update_line():

# @app.route('/update_shipment')
# def update_shipment():

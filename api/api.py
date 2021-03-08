import time
from sqlalchemy import create_engine
import sqlite3

from flask import Flask
import config

server = config.server
database = config.databaseName
userName = config.userName
password = config.password
engine = create_engine(f'mssql+pyodbc://{userName}:{password}@{server}/{database}?driver=SQL Server')


app = Flask(__name__)

#set up persistent data store for orders that lives outside of query lifetime

@app.route('/time')
def get_current_time():
    return {'time': time.time()}

@app.cli.command()
def order_poll():
    date = '\'2021-03-04\''  # 'getdate()'

    with engine.connect() as con:
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
            from InvoiHdr h inner join InvoiDet d on h.InInvoiId = d.ExInvoiId
            inner join Item i on d.ExItemId = i.InItemId
            inner join Warehouse w on d.usrShipFromWarehouse = w.InWarehouseId
            where h.[x04472474_ShippedDate] = {date} AND h.[InvoiType] = 51 AND 
                d.[usrShipFromWarehouse] = 4 AND h.[x04472474_Shipped] = 1 AND h.[ShipVia] != '' 
                and i.itemid not in ('j4g','j5u','x1','j4')
        """)

    new_orders = []
    idx = 0
    order_list = {}  # store pos so we can insert if lines aren't in order
    for line in rs:
        #look for unique header record
        if line.id not in order_list:
            new_orders.append({ #insert header record
                "id":line['id'],
                "ship_via":line['ship_via'],
                "order_id":line['order_id'],
                "ship_date":line['ship_date'],
                "order_type":line['order_type'],
                "status":line['status'],
                "lines":[]
            })
            order_list[line['id']] = idx
            idx += 1
        new_orders[order_list[line['id']]]["lines"].append({
            "qty" : line['qty'],
            "qty_scanned" : line['qty_scanned'],
            "ship_from" : line['ship_from'],
            "upc_code" : line['upc_code'],
            "item_id" : line['item_id'],
            "line_id" : line['line_id']
        })

    #update data store with new_orders

#@app.route('/update_line')
#def update_line():

#@app.route('/update_shipment')
#def update_shipment():

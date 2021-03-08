import time

from flask import Flask

app = Flask(__name__)

#set up persistent data store for orders that lives outside of query lifetime

@app.route('/time')
def get_current_time():
    return {'time': time.time()}

@app.route('/order_poll')
def order_poll():
    new_orders = []
    #sql query here
    data = query.results()
    row = {}

    for each line in data:
        idx = -1
        order_list = {} #store pos so we can insert if lines aren't in order
        #look for unique header record
        if line.id not in order_list:
            new_orders.append({ #insert header record
                "id":line.id,
                "ship_via":line.shipvia,
                "order_id":line.order_id,
                "ship_date":line.ship_date,
                "order_type":line.order_type,
                "status":line.status,
                "lines":[]
            })
            idx += 1
        order_list[line.id] = idx
        row["qty"] = line.qty
        row["qty_scanned"] = line.qty_scanned
        row["ship_from"] = line.ship_from
        row["upc_code"] = line.upc_code
        row["item_id"] = line.item_id
        row["line_id"] = line.line_id
        new_orders[order_list[line.id]]["lines"].append(row)
        row = {}

    #update data store with new_orders

@app.route('/update_line')
def update_line():

@app.route('/update_shipment')
def update_shipment():
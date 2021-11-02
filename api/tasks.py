import db
from sqlalchemy.orm import sessionmaker
from sqlalchemy import exc
from exceptions import CancelledOrderException, OrderDoesNotExistException, InvalidStatusException
import logging
from logging.config import dictConfig
import json


def orders_poll():
    with db.get_dyna_db().connect() as con:
        rs = con.execute(
            f"""select h.invoiid as id, 
                h.shipvia as ship_via, 
                h.OrderId as order_id,
                c.Name as cust_name,
                h.x04472474_ShippedDate as ship_date,
                isnull(h.PONum, '') as po_number,
                case when h.invoitype = 1 then 'Invoiced'
                    when h.invoitype = 50 then 'Estimate'
                    when h.invoitype = 51 then 'Open'
                    else 'Unknown' end as order_type,
                w.WarehouseId as ship_from,
                case when (x04472474_PendingCancellation = 1  or usrCancelled = 1) then 'Cancelled'
                        when (x04472474_BLStatus = 'Closed' or 
                            x04472474_BLStatus = 'Fulfilled') then 'Fulfilled'
                        when (x04472474_Delayed = 1 and h.x04472474_ShippedDate <= h.x04472474_DelayedDate) 
                            then 'Delayed'
                        when (x04472474_BLStatus is NULL or 
                            x04472474_BLStatus <> 'Closed') then 'Released'
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
            where h.[InvoiType] = 51 AND 
                d.[usrShipFromWarehouse] in (1, 4, 8) AND h.[x04472474_Shipped] = 1 AND 
                i.itemid not in ('j4g','j5u','x1','j4', 'j8') AND
                c.custid not in ('zemp')
        """).fetchall()
    new_orders = order_prep(rs)
    db_insert(new_orders, 'dashboard_orders')


def invoices_poll(config):
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
                c.Name as cust_name,
                h.x04472474_ShippedDate as ship_date,
                isnull(h.PONum, '') as po_number,
                case when h.invoitype = 1 then 'Invoiced'
                    when h.invoitype = 50 then 'Estimate'
                    when h.invoitype = 51 then 'Open'
                    else 'Unknown' end as order_type,
                w.WarehouseId as ship_from,
                case when (x04472474_PendingCancellation = 1  or usrCancelled = 1) then 'Cancelled'
					when h.InvoiType = 1 then 'Invoiced'
                        when (x04472474_BLStatus = 'Closed' or 
                            x04472474_BLStatus = 'Fulfilled') then 'Fulfilled'
                        when (x04472474_Delayed = 1 and h.x04472474_ShippedDate <= h.x04472474_DelayedDate) 
                            then 'Delayed'
                        when (x04472474_BLStatus is NULL or 
                            x04472474_BLStatus <> 'Closed') then 'Released'
                    end as 'status',
                d.Qty as qty,
                d.usrBarcodeScanCount as qty_scanned,
                isnull(i.UPCCode,'') as upc_code,
                i.ItemId as item_id,
                d.InInvoiDetId as line_id,
                h.x04472474_DeliveredDate as delivered_date,
                h.x04472474_DelayedDate as delayed_date
            from InvoiHdr as h inner join InvoiDet as d on h.InInvoiId = d.ExInvoiId
            inner join Item as i on d.ExItemId = i.InItemId
            inner join Warehouse as w on d.usrShipFromWarehouse = w.InWarehouseId
            inner join Cust as c on h.ExCustID = c.InCustId
            where ((h.[InvoiType] = 51 AND h.x04472474_ShippedDate < {date}) or (h.InvoiType = 1 and InvoiDate = {date})) and
				(h.x04472474_ShippedDate > h.x04472474_DelayedDate OR x04472474_Delayed <> 1) and
                d.[usrShipFromWarehouse] in (1, 4, 8) AND h.[x04472474_Shipped] = 1 AND 
                i.itemid not in ('j4g','j5u','x1','j4', 'j8', 'RETURN', 'k89') AND
                c.custid not in ('zemp')
        """).fetchall()
    new_orders = order_prep(rs)
    db_insert(new_orders, 'dashboard_invoices')


def order_prep(rs):
    new_orders = []
    idx = 0
    order_list = {}  # store pos so we can insert if lines aren't in order
    for line in rs:
        # look for unique header record
        record = {  # insert header record
                "id": line['id'],
                "cust_name": line['cust_name'].replace("'", "''") if line['cust_name'] is not None else '',
                "ship_via": line['ship_via'].replace("'", "''") if line['ship_via'] is not None else '',
                "order_id": line['order_id'],
                "ship_date": line['ship_date'].strftime("%Y-%m-%d"),
                "order_type": line['order_type'],
                "status": line['status'],
                "ship_from": line['ship_from'],
                "po_number": line['po_number'].replace("'", "''"),
                "lines": []
            }
        try:
            record["delivered_date"] = line['delivered_date'].strftime("%Y-%m-%d") if line['delivered_date'] is not None else ''
            record["delayed_date"] = line['delayed_date'].strftime("%Y-%m-%d") if line['delayed_date'] is not None else ''
        except exc.NoSuchColumnError:
            pass
        if line.id not in order_list:
            new_orders.append(record)
            order_list[line['id']] = idx
            idx += 1

        new_orders[order_list[line['id']]]["lines"].append({
            "qty": str(line['qty']),
            "qty_scanned": str(line['qty_scanned']),
            "upc_code": line['upc_code'],
            "item_id": line['item_id'],
            "line_id": line['line_id']
        })
    return new_orders


def db_insert(new_orders, table):
    Session = sessionmaker(bind=db.get_db())
    session = Session()
    valid_tables = {'dashboard_orders': 1, 'dashboard_invoices': 1}

    try:
        if valid_tables[table] != 1:
            logging.error('table is not valid')
    except LookupError:
        logging.error('table does not exist')
        return

    try:
        session.execute(f"delete from {table}")
        for item in new_orders:
            session.execute(f"insert into {table} values({item['id']}, '{json.dumps(item)}')")
        session.commit()
    except exc.SQLAlchemyError as e:
        logging.error(e)
        session.rollback()
    finally:
        session.close()


def activate_logging():
    dictConfig({
        'version': 1,
        'formatters': {'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        }},
        'handlers': {
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'default',
                'filename': 'tasklogs.log',
                'maxBytes': 512000,
                'backupCount': 3
            }
        },
        'root': {
            'level': 'INFO',
            'handlers': ['file']
        }
    })


def update_scan_confirm(upc, order_id):
    """

    :param upc: string. upc code of item to scan
    :param order_id: string. order of item scanned
    :return:
    """
    errors = []

    activate_logging()

    Session = sessionmaker(bind=db.get_dyna_db())
    session = Session()

    try:
        result = session.execute('''
            select i.itemid, 
                isnull(i.upccode, '') as upc_code, 
                d.qty, 
                d.InInvoiDetId as line_id, 
                d.usrBarcodeScanCount as qty_scanned, 
                isnull(h.x04472474_PendingCancellation, '') as cancelled,
                h.invoiid order_id
            from invoihdr h 
            inner join invoidet d on h.InInvoiId = d.ExInvoiId 
            inner join Item as i on d.ExItemId = i.InItemId
            where invoiid = :order_id and i.upccode = :upc_code 
            ''', {'order_id': order_id, 'upc_code': upc})
        # session.commit() causes errors on SQL Server calls
        total_lines = 0
        complete_lines = 0

        for line in result.fetchall():
            # order_id = line['order_id']
            total_lines += 1

            if line['cancelled'] == 1:
                raise CancelledOrderException(order_id)

            if line['qty'] > line['qty_scanned']:
                session.execute(
                    '''
                    update invoidet 
                    set usrBarcodeScanCount = usrBarcodeScanCount + 1
                    from
                    invoihdr h 
                    inner join invoidet d on h.InInvoiId = d.ExInvoiId 
                    where h.invoiid = :order_id and d.InInvoiDetId = :line_id
                    ''',
                    {'order_id': line['order_id'],
                     'line_id': line['line_id']})
                # session.commit()
                if line['qty'] - line['qty_scanned'] == 1:
                    # if this was the last item on line, close it out
                    complete_lines += 1
                break
            else:
                # line is complete
                complete_lines += 1
        else:
            raise OrderDoesNotExistException(order_id)

        if total_lines == complete_lines and total_lines > 0:
            # if all lines are complete, mark it ready to ship
            logging.info('Order %s is ready to ship', order_id)
            session.execute(
                '''
                update invoihdr 
                set x04472474_BLStatus = 'Fulfilled'
                from
                invoihdr
                where invoiid = :order_id
                ''',
                {'order_id': order_id})

        session.commit()  # Commit together so we don't have state where all
        # lines are complete but order isn't Ready to Ship

    except (exc.SQLAlchemyError, ValueError, CancelledOrderException,
            OrderDoesNotExistException) as e:
        logging.error(e)
        errors.append(e)
        session.rollback()
    finally:
        session.close()
    if len(errors) > 0:
        return {"error": errors}
    else:
        return {"result": 'Scan successful'}


def update_order_status(order_id, order_status):
    """

    :param order_id: string. order to change
    :param order_status: string. can be 'Released', 'Fulfilled', 'Delayed' or 'Cancelled'
    :return:
    """
    errors = []

    # activate_logging()

    Session = sessionmaker(bind=db.get_dyna_db())
    session = Session()
    try:
        result = session.execute('''
            select
                isnull(h.x04472474_BLStatus, '') as status,
                isnull(h.x04472474_PendingCancellation, '') as cancelled,
                h.invoiid order_id
            from invoihdr h 
            where invoiid = :order_id
            ''', {'order_id': order_id})
        # session.commit() causes errors on SQL Server calls

        try:
            for line in result.fetchall():
                if order_status == 'Cancelled':
                    pass    # Don't support cancelling at the moment
                elif order_status == 'Released' or order_status == 'Fulfilled' or order_status == 'Delayed':
                    if line['status'] != order_status:
                        session.execute(
                            '''
                            update invoihdr 
                            set x04472474_BLStatus = :order_status
                            from
                            invoihdr
                            where invoiid = :order_id
                            ''',
                            {'order_id': order_id, 'order_status': order_status})
                        session.commit()
                else:
                    raise InvalidStatusException(order_status)
        except KeyError:
            raise OrderDoesNotExistException(order_id)

    except (exc.SQLAlchemyError, ValueError, CancelledOrderException,
            OrderDoesNotExistException) as e:
        logging.error(e)
        errors.append(e)
        session.rollback()
    finally:
        session.close()
    if len(errors) > 0:
        return {"error": errors}
    else:
        return {"id": order_id, "status": order_status}

import db
from sqlalchemy.orm import sessionmaker
from sqlalchemy import exc
from exceptions import CancelledOrderException, OrderDoesNotExistException
import logging
from logging.config import dictConfig


def update_scan_confirm(upc, order_id):
    """

    :param upc: string. upc code of item to scan
    :param order_id: string. order of item scanned
    :return:
    """
    errors = []

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
                set x04472474_BLStatus = 'Ready to Ship'
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

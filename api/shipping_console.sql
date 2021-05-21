select h.invoiid as id, 
                h.shipvia as ship_via,
                h.OrderId as order_id,
                h.x04472474_ShippedDate as ship_date,
                case when h.invoitype = 1 then 'Invoiced'
                    when h.invoitype = 50 then 'Estimate'
                    when h.invoitype = 51 then 'Open'
                    else 'Unknown' end as order_type,
                w.WarehouseId as ship_from,
                case when x04472474_PendingCancellation = 1  then 'Cancelled'
                    when (x04472474_BLStatus is NULL or
                    (x04472474_BLStatus <> 'Ready to Ship' and x04472474_BLStatus <> 'Closed')) then 'Open'
                    when (x04472474_BLStatus = 'Closed' or x04472474_BLStatus = 'Ready to Ship') then 'Closed'
                    end as 'status',
                d.Qty as qty,
                d.usrBarcodeScanCount as qty_scanned,
                isnull(i.UPCCode,'') as upc_code,
                i.ItemId as item_id,
                d.InInvoiDetId as line_id
            from InvoiHdr as h inner join InvoiDet as d on h.InInvoiId = d.ExInvoiId
            inner join Item as i on d.ExItemId = i.InItemId
            inner join Warehouse as w on d.usrShipFromWarehouse = w.InWarehouseId
            where /*h.[x04472474_ShippedDate] = '2021-05-18' AND*/ h.[InvoiType] = 51 AND
                d.[usrShipFromWarehouse] = 4 AND h.[x04472474_Shipped] = 1 AND
                h.[ShipVia] != '' and i.itemid not in ('j4g','j5u','x1','j4', 'j8') AND
                c.custid not in ('zemp')

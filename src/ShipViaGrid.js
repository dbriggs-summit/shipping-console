import * as React from "react";
import { DataGrid } from '@material-ui/data-grid';
import { useHistory } from 'react-router-dom';
import today_date from "./utilities";

const order_columns = [
    {field: 'ship_via', headerName: 'Ship Via', width: 210},
    {field: 'total_orders', headerName: 'Total Orders', type: 'number', width: 145},
    {field: 'open_orders', headerName: 'Open Orders', type: 'number', width: 145},
    {field: 'closed_orders', headerName: 'Closed Orders', type: 'number', width: 145},
];

const inv_columns = [
    {field: 'ship_via', headerName: 'Ship Via', width: 210},
    {field: 'total_orders', headerName: 'Total Orders', type: 'number', width: 145},
    {field: 'open_orders', headerName: 'Open Orders', type: 'number', width: 145},
    {field: 'closed_orders', headerName: 'Closed Orders', type: 'number', width: 145},
    {field: 'invoiced_orders', headerName: 'Invoiced Orders', type: 'number', width: 145},
];



const ShipViaGrid = props => {
    const {location: location, type: type, ...ship_vias} = props;
    const history = useHistory();
    function handleClick(rowData) {
        const destination = location === '' ? {
                        pathname: "/" + type,
                        search: `filter=${JSON.stringify({ 
                            ship_via: encodeURIComponent(rowData.row.ship_via),
                        })}`
        } : {
                            pathname: "/" + type,
                            search: `filter=${JSON.stringify({ 
                                ship_via: encodeURIComponent(rowData.row.ship_via), 
                                ship_from: location, 
                                ship_date: today_date()
                            })}`
        };
        history.push(destination);
    };
    const order_grid = (ship_vias.value === undefined ?
        [{'id': 0,
        'ship_via': '',
        'total_orders': 0,
        'open_orders': 0,
        'closed_orders': 0
        }] : Object.values(ship_vias.value).reduce(
        (grid, ship_via) => {
            grid.push({
                'id': grid.length,
                'ship_via': ship_via[0],
                'total_orders': ship_via[4],
                'open_orders': ship_via[1],
                'closed_orders': ship_via[2]
                });
            return grid;

        },  []
    ));
    const invoice_grid = (ship_vias.value === undefined ?
        [{
            'id': 0,
            'ship_via': '',
            'total_orders': 0,
            'open_orders': 0,
            'closed_orders': 0,
            'invoiced_orders': 0
        }] : Object.values(ship_vias.value).reduce(
        (grid, ship_via) => {
            grid.push({
                'id': grid.length,
                'ship_via': ship_via[0],
                'total_orders': ship_via[4],
                'open_orders': ship_via[1],
                'closed_orders': ship_via[2],
                'invoiced_orders': ship_via[3]
                });
            return grid;

        },  []
    ));

    return (
        <DataGrid rows={type === 'orders' ? order_grid : invoice_grid}
                  columns={type === "orders" ? order_columns : inv_columns}
                  autoHeight="true"
                  hideFooter="true"
                  onRowClick={handleClick}
                  sortModel={[{ field:'ship_via', sort: 'asc'},]} />
    );
};

export default ShipViaGrid;
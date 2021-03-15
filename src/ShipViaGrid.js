import * as React from "react";
import { DataGrid } from '@material-ui/data-grid';

const columns = [
    {field: 'ship_via', headerName: 'Ship Via'},
    {field: 'total_orders', headerName: 'Total Orders', type: 'number'},
    {field: 'open_orders', headerName: 'Open Orders', type: 'number'},
    {field: 'closed_orders', headerName: 'Ready to Ship', type: 'number'},
];

const ShipViaGrid = props => {
    console.log(props);
    const ship_vias = props;
    const ship_via_grid = (ship_vias === undefined ?
        [{'id': 0,
        'ship_via': '',
        'total_orders': 0,
        'open_orders': 0,
        'closed_orders': 0
        }] : Object.values(ship_vias).reduce(
        (grid, ship_via) => {
            grid.push({
                'id': grid.length,
                'ship_via': ship_via[0],
                'total_orders': ship_via[3],
                'open_orders': ship_via[1],
                'closed_orders': ship_via[2]
                });
            return grid;

        }, {'id': 0,
            'ship_via': '',
            'total_orders': 0,
            'open_orders': 0,
            'closed_orders': 0
        }
    ));

    return <DataGrid rows={ship_via_grid} columns={columns}  />;
};

export default ShipViaGrid;
import * as React from "react";
import { DataGrid } from '@material-ui/data-grid';
import { Link, Redirect } from 'react-router-dom';

const columns = [
    {field: 'ship_via', headerName: 'Ship Via', width: 210,
    renderCell: (params) =>  (<Link to={{
                        pathname: "/orders",
                        search: `filter=${JSON.stringify({ ship_via: params.getValue("ship_via")})}`
    }} style={{ textDecoration: 'none', color: 'inherit', }}>{params.getValue("ship_via")}</Link>)
    },
    {field: 'total_orders', headerName: 'Total Orders', type: 'number', width: 145},
    {field: 'open_orders', headerName: 'Open Orders', type: 'number', width: 145},
    {field: 'closed_orders', headerName: 'Ready to Ship', type: 'number', width: 145},
];

const ShipViaGrid = props => {
    const {...ship_vias} = props;
    const ship_via_grid = (ship_vias.value === undefined ?
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
                'total_orders': ship_via[3],
                'open_orders': ship_via[1],
                'closed_orders': ship_via[2]
                });
            return grid;

        },  []
    ));

    return (
        <DataGrid rows={ship_via_grid} columns={columns} autoHeight="true" hideFooter="true" onRowClick={() => {return (<Redirect to="/orders" />)}} />
    );
};

export default ShipViaGrid;
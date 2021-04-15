import * as React from "react";
import {Admin, Resource} from 'react-admin';
import simpleRestProvider from 'ra-data-simple-rest';
import Dashboard from "./Dashboard";
import MyLayout from "./MyLayout";
import customRoutes from "./customRoutes";
import { OrderEdit, OrderList } from "./orders";

const dataProvider = simpleRestProvider('http://10.30.30.13:8000/');
//const dataProvider = simpleRestProvider('http://127.0.0.1:5000/');
const App = () => (
    <Admin customRoutes={customRoutes} layout={MyLayout} dataProvider={dataProvider} dashboard={Dashboard}
           disableTelemetry>
        <Resource name="orders" list={OrderList} edit={OrderEdit} options={{ label: "Orders" }} />
    </Admin>
);

export default App;

/*
        <Resource name="scan_confirm" list={ListGuesser} edit={EditGuesser} options={{ label: "Scan Confirm" }} />
 */
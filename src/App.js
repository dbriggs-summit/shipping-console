import * as React from "react";
import {Admin, Resource, ListGuesser, EditGuesser} from 'react-admin';
import simpleRestProvider from 'ra-data-simple-rest';
import Dashboard from "./Dashboard";
import MyLayout from "./MyLayout";
import customRoutes from "./customRoutes";

const dataProvider = simpleRestProvider('http://127.0.0.1:5000/');
const App = () => (
    <Admin customRoutes={customRoutes} layout={MyLayout} dataProvider={dataProvider} dashboard={Dashboard}
           disableTelemetry>
        <Resource name="orders" list={ListGuesser} edit={EditGuesser} options={{ label: "Orders" }} />
        <Resource name="scan_confirm" list={ListGuesser} edit={EditGuesser} options={{ label: "Scan Confirm" }} />
    </Admin>
);

export default App;

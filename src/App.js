import * as React from "react";
import {Admin, Resource, ListGuesser, EditGuesser} from 'react-admin';
import simpleRestProvider from 'ra-data-simple-rest';
import Dashboard from "./Dashboard";

const dataProvider = simpleRestProvider('http://127.0.0.1:5000/');
const App = () => (
    <Admin dataProvider={dataProvider} dashboard={Dashboard} disableTelemetry>
        <Resource name="orders" list={ListGuesser} edit={EditGuesser} />
        <Resource name="scan_confirm" list={ListGuesser} edit={EditGuesser} />
    </Admin>
);

export default App;

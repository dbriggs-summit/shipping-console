import * as React from "react";
import {Admin, Resource, ListGuesser, EditGuesser} from 'react-admin';
import jsonServerProvider from 'ra-data-simple-rest';

const dataProvider = jsonServerProvider('http://127.0.0.1:5000/');
const App = () => (
    <Admin dataProvider={dataProvider} disableTelemetry>
        <Resource name="orders" list={ListGuesser} edit={EditGuesser} />
    </Admin>
);

export default App;

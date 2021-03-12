import * as React from "react";
import {Admin, Resource, ListGuesser} from 'react-admin';
import jsonServerProvider from 'ra-data-simple-rest';

const dataProvider = jsonServerProvider('http://127.0.0.1:5000/');
const App = () => (
    <Admin dataProvider={dataProvider}>
        <Resource name="orders" list={ListGuesser} />
    </Admin>
);

export default App;

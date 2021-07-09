import * as React from "react";
import { Route } from 'react-router-dom';
import ScanLabels from "./ScanLabels";
import Dashboard from "./Dashboard";

export default [
    <Route exact path="/confirm-scan" component={ScanLabels} />,
    <Route exact path="/dashboard-bronx">
        <Dashboard dash_loc="Bronx" />
    </Route>,
    <Route exact path="/dashboard-ed50d">
        <Dashboard dash_loc="ED50D" />
    </Route>
];
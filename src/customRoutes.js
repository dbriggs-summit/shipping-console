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
    </Route>,
    <Route exact path="/dashboard-invoice">
        <Dashboard dash_loc="" />
    </Route>,
    <Route exact path="/dashboard-edison">
        <Dashboard dash_loc="Edison" />
    </Route>,
    <Route exact path="/">
        <Dashboard dash_loc="Edison" />
    </Route>
];
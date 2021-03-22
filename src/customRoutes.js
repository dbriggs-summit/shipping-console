import * as React from "react";
import { Route } from 'react-router-dom';
import ScanLabels from "./ScanLabels";

export default [
    <Route exact path="/confirm-scan" component={ScanLabels} />,
];
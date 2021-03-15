import React, {useState, useEffect, useCallback, CSSProperties} from "react";
import { Card, CardContent, CardHeader } from '@material-ui/core';
import { useVersion, useDataProvider } from 'react-admin';
import OrderCard from "./OrderCard";
import EventIcon from '@material-ui/icons/Event';
import CheckCircleIcon from '@material-ui/icons/CheckCircle';
import ArrowDropDownCircleIcon from '@material-ui/icons/ArrowDropDownCircle';
import { Title } from 'react-admin';


const styles = {
    flex: { display: 'flex' },
    flexColumn: { display: 'flex', flexDirection: 'column' },
    leftCol: { flex: 1, marginRight: '0.5em' },
    rightCol: { flex: 1, marginLeft: '0.5em' },
    singleCol: { marginTop: '1em', marginBottom: '1em' },
};

const Spacer = () => <span style={{ width: '1em' }} />;
const VerticalSpacer = () => <span style={{ height: '1em' }} />;


const Dashboard = () => {
    const dataProvider = useDataProvider();
    const [state, setState] = useState({});
    const version = useVersion();
    const fetchOrders = useCallback(async () =>{
        const {data}  = await dataProvider.getList(
          'orders',
            {
                pagination: { page: 1, perPage: 999},
                sort: { field: 'id', order: 'DESC'},
                filter: {},
            }
        );
        const aggregations = data
            .reduce(
                (stats, order) => {

                    if (order.status === 'Open') {
                        stats.open_orders++;
                        stats.all_orders++;
                    }
                    if (order.status === 'Closed') {
                        stats.closed_orders++;
                        stats.all_orders++;
                    }
                    return stats;
                },{
                    open_orders: 0,
                    all_orders: 0,
                    closed_orders: 0
                }
            );

        setState(state => ({
            ...state,
            data,
            all_orders: aggregations.all_orders,
            open_orders: aggregations.open_orders,
            closed_orders: aggregations.closed_orders,
        }));

    }, [dataProvider]);

    useEffect(() => {
        fetchOrders();
    }, [version]);

    const {
        all_orders,
        open_orders,
        closed_orders,
    } = state;

    return (
        <div style={styles.flex}>
            <div style={styles.leftCol}>
                <div style={styles.flex}>
                    <Title title="Shipping Console" />
                    <OrderCard value={all_orders} title="Total Orders" icon={EventIcon} />
                    <Spacer />
                    <OrderCard value={open_orders} title="Open Orders" icon={ArrowDropDownCircleIcon} />
                    <Spacer />
                    <OrderCard value={closed_orders} title="Closed Orders" icon={CheckCircleIcon} />

                </div>
            </div>
        </div>
    );
};

export default Dashboard;

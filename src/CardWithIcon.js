import * as React from "react";
import {createElement} from 'react';
import {Card, Box, Typography, Divider} from "@material-ui/core";
import {makeStyles} from "@material-ui/core";
import { Link } from 'react-router-dom';

const useStyles = makeStyles(theme => ({
    card: {
        minHeight: 52,
        display: 'flex',
        flexDirection: 'column',
        flex: '1',
        /*'& a': {
            textDecoration: 'none',
            color: 'inherit',
        },*/
    },
    main: (props) => ({
        overflow: 'inherit',
        padding: 16,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
    }),
    title: {},
}));

const CardWithIcon = props => {
  const { icon, title, subtitle } = props;
  const classes = useStyles(props);
  return (
    <Card className={classes.card}>
        <div ClassName={classes.main}>
            <Box width="3em" className="icon">
                {createElement(icon, {fontSize: 'large'})}
            </Box>
            <Box textAlign="right">
                <Typography
                    className={classes.title}
                    color="textSecondary">
                    {title}
                </Typography>
                <Typography variant="h5" component="h2">
                    {subtitle || ' '}
                </Typography>
            </Box>
        </div>
    </Card>
  );
};

export default CardWithIcon;
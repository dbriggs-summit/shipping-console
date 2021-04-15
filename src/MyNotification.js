import { Notification } from 'react-admin';
import {makeStyles} from "@material-ui/core";

const useStyles = makeStyles(theme => ({
    card: {
        minHeight: 52,
        display: 'flex',
        flexDirection: 'column',
        flex: '1',
        '& a': {
            textDecoration: 'none',
            color: 'inherit',
        },
    },
    main: (props) => ({
        overflow: 'inherit',
        padding: 16,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        '& .icon': {
            color: theme.palette.type === 'dark' ? 'inherit' : '#dc2440',
        },
        fontSize: '300%',
    }),
    title: {},
    icon: {}
}));


const MyNotification = props => {
    const classes = useStyles(props);
    return(
        <Notification className={classes.main} {...props} />
    );
}

export default MyNotification;
// in src/MyLayout.js
import { Layout } from 'react-admin';
import Menu from './Menu';
import MyNotification from './MyNotification';

const MyLayout = (props) => <Layout {...props} notification={MyNotification} menu={Menu} />;

export default MyLayout;
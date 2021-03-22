// in src/MyLayout.js
import { Layout } from 'react-admin';
import Menu from './Menu';

const MyLayout = (props) => <Layout {...props} menu={Menu} />;

export default MyLayout;
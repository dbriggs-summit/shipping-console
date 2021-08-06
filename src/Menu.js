// in src/Menu.js
import * as React from 'react';
import { useSelector } from 'react-redux';
import { useMediaQuery } from '@material-ui/core';
import { DashboardMenuItem, MenuItemLink, getResources } from 'react-admin';
import DefaultIcon from '@material-ui/icons/ViewList';
import CropFreeIcon from '@material-ui/icons/CropFree';
import DashboardIcon from '@material-ui/icons/Dashboard';

const Menu = ({ onMenuClick, logout }) => {
    const isXSmall = useMediaQuery(theme => theme.breakpoints.down('xs'));
    const open = useSelector(state => state.admin.ui.sidebarOpen);
    const resources = useSelector(getResources);
    return (
        <div>
            <MenuItemLink
                to="/dashboard-edison"
                primaryText="Edison"
                leftIcon={<DashboardIcon />}
                onClick={onMenuClick}
                sidebarIsOpen={open}
            />
            <MenuItemLink
                to="/dashboard-bronx"
                primaryText="Bronx"
                leftIcon={<DashboardIcon />}
                onClick={onMenuClick}
                sidebarIsOpen={open}
            />
            <MenuItemLink
                to="/dashboard-ED50D"
                primaryText="ED50D"
                leftIcon={<DashboardIcon />}
                onClick={onMenuClick}
                sidebarIsOpen={open}
            />
            <MenuItemLink
                to="/dashboard-invoice"
                primaryText="Invoice Progress"
                leftIcon={<DashboardIcon />}
                onClick={onMenuClick}
                sidebarIsOpen={open}
            />
            {resources.map(resource => (
                <MenuItemLink
                    key={resource.name}
                    to={`/${resource.name}`}
                    primaryText={
                        (resource.options && resource.options.label) ||
                        resource.name
                    }
                    leftIcon={
                        resource.icon ? <resource.icon /> : <DefaultIcon />
                    }
                    onClick={onMenuClick}
                    sidebarIsOpen={open}
                />
            ))}
            <MenuItemLink
                to="/confirm-scan"
                primaryText="Scan Labels"
                leftIcon={<CropFreeIcon />}
                onClick={onMenuClick}
                sidebarIsOpen={open}
            />
            {isXSmall && logout}
        </div>
    );
};

export default Menu;
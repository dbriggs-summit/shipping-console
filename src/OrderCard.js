import * as React from "react";
import CardWithIcon from './CardWithIcon';

const OrderCard = ({icon, value, title, to}) => {
    return (
        <CardWithIcon
            icon={icon}
            title={title}
            subtitle={value}
            to={to}
        />
    );
};

export default OrderCard;
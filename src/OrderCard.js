import * as React from "react";
import CardWithIcon from './CardWithIcon';

const OrderCard = ({icon, value, title}) => {
    return (
        <CardWithIcon
            icon={icon}
            title={title}
            subtitle={value}
        />
    );
};

export default OrderCard;
create table dashboard_orders (
    id varchar(25) NOT NULL PRIMARY KEY,
    "order_json" json NOT NULL
);
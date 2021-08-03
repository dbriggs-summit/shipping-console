create table dashboard_orders (
    id varchar(25) NOT NULL PRIMARY KEY,
    "order_json" jsonb NOT NULL
);
create table dashboard_invoices (
    id   varchar(25) not null primary key,
    invoice_json jsonb not null
);
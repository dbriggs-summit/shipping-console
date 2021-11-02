import * as React from "react";
import { Filter, List, Edit, Datagrid, TextField, ArrayField, ReferenceField,
    SaveButton, Toolbar, SingleFieldList, ChipField, SimpleForm, SelectInput,
    TextInput, ArrayInput, DateInput, SimpleFormIterator } from 'react-admin';

const PostEditToolbar = props => (
    <Toolbar {...props} >
        <SaveButton disabled={props.pristine} />
    </Toolbar>
);

export const InvoiceFilter = (props) => (
  <Filter {...props}>
      <TextInput label="Search" source="q" alwaysOn />
      <SelectInput label="Status" source="status" choices={[
                { id: 'Released', name: 'Released'},
                { id: 'Fulfilled', name: 'Fulfilled'},
                { id: 'Cancelled', name: 'Cancelled'},
                { id: 'Delayed', name: 'Delayed'},
                { id: 'Invoiced', name: 'Invoiced'}
            ]} />
      <SelectInput label="Ship From" source="ship_from" choices={[
          { id: 'Bronx', name: 'Bronx'},
          { id: 'Edison', name: 'Edison'},
          { id: 'ED50D', name: 'ED50D'}
      ]} />
      <DateInput label="Ship Date" source="ship_date" />
  </Filter>
);

export const InvoiceList = props => (
    <List filters={<InvoiceFilter />} {...props}>
        <Datagrid optimized rowClick="edit">
            <ReferenceField source="id" reference="invoices"><TextField source="id" /></ReferenceField>
            <TextField source="cust_name" label="Customer Name" />
            <TextField source="po_number" />
            <TextField source="status" />
            <TextField source="ship_from" />
            <TextField source="ship_date" options={{ timeZone: 'UTC' }} />
            <TextField source="delivered_date" />
            <TextField source="ship_via" />
            <ArrayField source="lines"><SingleFieldList><ChipField source="item_id" /></SingleFieldList></ArrayField>
        </Datagrid>
    </List>
);

export const InvoiceEdit = ({permissions, ...props}) => (
    <Edit {...props}>
        <SimpleForm toolbar={<PostEditToolbar />}>
            <TextInput disabled source="id" />
            <TextInput disabled source="order_id" />
            <SelectInput disabled source="status" choices={[
                { id: 'Released', name: 'Released'},
                { id: 'Fulfilled', name: 'Fulfilled'},
                { id: 'Cancelled', name: 'Cancelled'},
                { id: 'Delayed', name: 'Delayed'},
                { id: 'Invoiced', name: 'Invoiced'}
            ]} />
            <TextInput disabled source="cust_name" />
            <TextInput disabled source="po_number" />
            <TextInput disabled source="ship_via" />
            <SelectInput disabled source="order_type" choices={[
                { id: 'Invoiced', name: 'Invoiced'},
                { id: 'Estimate', name: 'Estimate'},
                { id: 'Open', name: 'Open'},
            ]} />
            <DateInput disabled source="ship_date" />
            <DateInput disabled source="delivered_date" />
            <DateInput disabled source="delayed_date" />
            <ArrayInput disabled source="lines"><SimpleFormIterator><TextInput source="item_id" title="Item" />
            <TextInput disabled source="upc_code" title="UPC Code" />
            <TextInput disabled source="qty" title="Qty Ordered" />
            <TextInput disabled source="qty_scanned" title="Qty Scanned" />
            <TextInput disabled source="ship_from" title="Ship From" />
            </SimpleFormIterator></ArrayInput>
        </SimpleForm>
    </Edit>
);
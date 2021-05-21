import * as React from "react";
import { Filter, List, Edit, Datagrid, TextField, ArrayField, ReferenceField,
    SaveButton, Toolbar, SingleFieldList, ChipField, SimpleForm, SelectInput,
    TextInput, ArrayInput, DateInput, SimpleFormIterator } from 'react-admin';

const PostEditToolbar = props => (
    <Toolbar {...props} >
        <SaveButton disabled={props.pristine} />
    </Toolbar>
);

export const OrderFilter = (props) => (
  <Filter {...props}>
      <TextInput label="Search" source="q" alwaysOn />
      <SelectInput label="Status" source="status" choices={[
                { id: 'Released', name: 'Released'},
                { id: 'Fulfilled', name: 'Fulfilled'},
                { id: 'Cancelled', name: 'Cancelled'},
                { id: 'Delayed', name: 'Delayed'},
            ]} />
      <SelectInput label="Ship From" source="ship_from" choices={[
          { id: 'Bronx', name: 'Bronx'},
          { id: 'Edison', name: 'Edison'},
      ]} />
  </Filter>
);

export const OrderList = props => (
    <List filters={<OrderFilter />} {...props}>
        <Datagrid optimized rowClick="edit">
            <ReferenceField source="order_id" reference="orders"><TextField source="id" /></ReferenceField>
            <TextField source="po_number" />
            <TextField source="status" />
            <TextField source="ship_from" />
            <TextField source="ship_date" options={{ timeZone: 'UTC' }} />
            <TextField source="ship_via" />
            <ArrayField source="lines"><SingleFieldList><ChipField source="item_id" /></SingleFieldList></ArrayField>
        </Datagrid>
    </List>
);

export const OrderEdit = ({permissions, ...props}) => (
    <Edit {...props}>
        <SimpleForm toolbar={<PostEditToolbar />}>
            <TextInput disabled source="order_id" />
            {permissions === 'shipping' && <SelectInput source="status" choices={[
                { id: 'Released', name: 'Released'},
                { id: 'Fulfilled', name: 'Fulfilled'},
                { id: 'Cancelled', name: 'Cancelled'},
                { id: 'Delayed', name: 'Delayed'}
            ]} /> }
            <TextInput disabled source="po_number" />
            <TextInput disabled source="ship_via" />
            <SelectInput disabled source="order_type" choices={[
                { id: 'Invoiced', name: 'Invoiced'},
                { id: 'Estimate', name: 'Estimate'},
                { id: 'Open', name: 'Open'},
            ]} />
            <DateInput disabled source="ship_date" />
            <ArrayInput disabled source="lines"><SimpleFormIterator><TextInput source="item_id" title="Item" />
            <TextInput disabled source="upc_code" title="UPC Code" />
            <TextInput disabled source="qty" title="Qty Ordered" />
            <TextInput disabled source="qty_scanned" title="Qty Scanned" />
            <TextInput disabled source="ship_from" title="Ship From" />
            </SimpleFormIterator></ArrayInput>
        </SimpleForm>
    </Edit>
);
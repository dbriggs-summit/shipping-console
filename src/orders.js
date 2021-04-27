import * as React from "react";
import { List, Edit, Datagrid, TextField, ArrayField, ReferenceField,
    SaveButton, Toolbar, SingleFieldList, ChipField, SimpleForm, SelectInput,
    TextInput, ArrayInput, DateInput, SimpleFormIterator } from 'react-admin';

const PostEditToolbar = props => (
    <Toolbar {...props} >
        <SaveButton disabled={!props.pristine} />
    </Toolbar>
);

export const OrderList = props => (
    <List {...props}>
        <Datagrid optimized rowClick="edit">
            <TextField source="id" />
            <ArrayField source="lines"><SingleFieldList><ChipField source="item_id" /></SingleFieldList></ArrayField>
            <ReferenceField source="order_id" reference="orders"><TextField source="id" /></ReferenceField>
            <TextField source="status" />
            <TextField source="ship_via" />
        </Datagrid>
    </List>
);

export const OrderEdit = ({permissions, ...props}) => (
    <Edit {...props}>
        <SimpleForm toolbar={<PostEditToolbar />}>
            <TextInput disabled source="order_id" />
            {permissions === 'shipping' && <SelectInput source="status" choices={[
                { id: 'Open', name: 'Open'},
                { id: 'Closed', name: 'Closed'},
                { id: 'Cancelled', name: 'Cancelled'},
            ]} /> }
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
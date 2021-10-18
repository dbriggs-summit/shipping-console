import React, { useState } from "react";
import { useNotify, fetchStart, fetchEnd } from 'react-admin';
import { useDispatch } from "react-redux";
import configData from "./config.json";
import {Fragment} from "react";
import {
    InputAdornment,
    IconButton,
    TextField as MuiTextField,
    TextFieldProps,
    Theme,
    InputLabel,
    MenuItem,
    FormControl,
    Select,
    Button,
    Divider,
    Container,
    Card,
    CardHeader,
    Box, makeStyles
} from '@material-ui/core';
import LocalShippingIcon from "@material-ui/icons/LocalShipping";
import CardWithIcon from "./CardWithIcon";

const Spacer = () => <span style={{ width: '1em' }} />;
const VerticalSpacer = () => <span style={{ height: '1em' }} />;

function handleErrors(response) {
    if (!response.ok) {
        throw Error(response.statusText);
    }
    return response;
}

const useStyles = makeStyles(
    theme => ({
        output: {
            width: theme.spacing(32),
            paddingTop: 50,
            display: "block"
        },
        form: {
            width: theme.spacing(32),
            paddingTop: 10,
            paddingBottom: 10,
            display: "block"
        },
        line: {
            width: theme.spacing(32),
            paddingTop: 10,
            paddingBottom: 10,
            display: "block"
        }
    }),
    { name: 'FreightQuote' }
);

const FreightQuote = (props) => {

    const dispatch = useDispatch();
    const notify = useNotify();
    const classes = useStyles(props);
    const [loading, setLoading] = useState(false);
    const [freightAmount, setFreightAmount] = useState(0);
    const [shipToZip, setShipToZip] = useState({
        "text":'',
        "errorText": ""
    });
    const [custFreightType, setCustFreightType] = useState('Drop Ship');
    const [lines, setLines] = useState(
    [
            {
                "itemNumber": "",
                "itemQty": "",
                "itemWeight": "",
                "itemHeight": "",
                "itemWidth": "",
                "itemDepth": "",
                "unitSize": "Full Size",
                "errorText": ""
            }
        ]
    );
                  console.log(lines.length);
    const handleLinesChange = (index, event) => {
        const values = [...lines];
        if (event.target.name === "itemNumber") {
              lines[index].itemNumber = event.target.value;
              setLoading(true);
              dispatch(fetchStart());
              fetch(configData.mode === "production" ? configData.apiUrl + `/items/` + lines[index].itemNumber :
                      `/items/` + lines[index].itemNumber,
                  {method: 'GET' })
                  .then(response => {
                      if(!response.ok){
                          throw Error("Please enter a valid item");
                      }
                      return response;
                  })
                  .then(response => response.json())
                  .then(json => {
                      if (json[0].weight === 0 || json[0].width === 0) {
                          lines[index].errorText = "Item has no weights and/or dims. Please contact inventory";
                      } else {
                          lines[index].errorText = "";
                      }
                      lines[index].itemWidth = json[0].width;
                      lines[index].itemDepth = json[0].depth;
                      lines[index].itemHeight = json[0].height;
                      lines[index].itemWeight = json[0].weight;
                  })
                  .catch((e) => {
                      lines[index].itemWidth = "";
                      lines[index].itemDepth = "";
                      lines[index].itemHeight = "";
                      lines[index].itemWeight = "";
                      lines[index].errorText = "Please enter a valid item";
                      /*notify('Problem getting quote: ' + e,'warning',
                        {},false, 5000)*/
                  })
                  .finally(() => {
                      setLoading(false);
                      dispatch(fetchEnd());
                  })
            setLines(values);
        } else {
            lines[index].itemQty = event.target.value;
            setLines(values);
        }
    };
    const handleInputChange = (event) => {
        //const [zipValue, freightValue] = [...shipToZip, custFreightType];
        if (event.target.name === "shipToZip") {
            if (/(^\d{5}$)|(^\d{5}-\d{4}$)/.test(event.target.value) === false) {
                setShipToZip({ text: event.target.value, errorText: "Please enter a valid zip code"});
                return;
            }
            setShipToZip({ text: event.target.value, errorText: ""});
        } else if (event.target.name === "custFreightType") {
            setCustFreightType(event.target.value);
        }
    };
    const handleAddFields = () => {
        const values = [...lines];
        values.push({
            itemNumber: '',
            itemQty: '',
            itemWeight: '0',
            itemHeight: '0',
            itemDepth: '0',
            itemWidth: '0',
            unitSize: 'Full Size',
            errorText: ""
        });
        setLines(values);
    };

    const handleRemoveFields = index => {
        const values = [...lines];
        values.splice(index, 1);
        setLines(values);
    };
    const handleSubmit = (data) => {
        data.preventDefault();
        if (shipToZip.errorText !== "") {
            return;
        }
        const lineErrors = lines.reduce((sum, curVal) => {
            if (curVal.errorText !== "") {
                sum += 1;
            }
            return sum;
        }, 0);
        if (lineErrors > 0) {
            return;
        }
        const formBody = {
            shipToZip: shipToZip.text,
            custFreightType: custFreightType,
            lines : lines
        };
        dispatch(fetchStart());
        fetch(configData.mode === "production" ? configData.apiUrl + `freight_quote` : `/freight_quote`,
                  {
                      method: 'PUT',
                      headers: {'Accept': 'application/json','Content-Type': 'application/json'},
                      body: JSON.stringify(formBody)
                  })
                  .then(handleErrors)
                  .then(response => response.json())
                  .then(json => {
                      setFreightAmount(json.total);
                  })
                  .catch((e) => {
                    notify('Problem getting quote: ' + e,'warning',
                        {},false, 5000)
                  })
                  .finally(() => {
                      dispatch(fetchEnd());
                  })
    };


  return (
      <Container>
          <Card>
            <CardHeader title="Freight Quote" />
          </Card>
          <Spacer />
          <FormControl onSubmit={handleSubmit}>
              <Box className={classes.form}>
                  <Box className={classes.form}>
                      <MuiTextField label="Zip Code" onChange={event => handleInputChange(event)}
                                    error = { shipToZip.errorText === "" ? false : true }
                                    helperText={shipToZip.errorText}
                          name="shipToZip" type="text" required value={shipToZip.text} />
                  </Box>
                  <Spacer />
                  <Box className={classes.form}>
                      <Select label="Freight Type" onChange={event => handleInputChange(event)} name="custFreightType"
                              value={custFreightType}>
                          <MenuItem value="Dealer">Dealer</MenuItem>
                          <MenuItem value="Drop Ship">Drop Ship</MenuItem>
                          <MenuItem value="White Glove">White Glove</MenuItem>
                      </Select>
                  </Box>
              </Box>
              <Box className={classes.form}>
                  <div className="form-row">
                      {lines.map((lines, index) => (

                          <Fragment key={`${lines}~${index}`}>
                              <Box className={classes.line}>
                                  <MuiTextField label="Item Number" onChange={event => handleLinesChange(index, event)}
                                         type="text" required
                                         className="form-control"
                                         error = { lines.errorText === "" ? false : true }
                                         id="itemNumber"
                                         name="itemNumber"
                                         helperText={lines.errorText}
                                         value={lines.itemNumber}
                                  />
                                  <MuiTextField label="Qty" onChange={event => handleLinesChange(index, event)}
                                         type="text" required
                                         className="form-control"
                                         id="itemQty"
                                         name="itemQty"
                                         value={lines.itemQty}
                                  />
                              <div className="form-group col-sm-2">
                                  <Button onClick={() => handleRemoveFields(index)}
                                          className="btn btn-link"
                                          type="button">
                                      -
                                  </Button>
                                  <Button onClick={() => handleAddFields(index)}
                                          className="btn btn-link"
                                          type="button">
                                      +
                                  </Button>
                              </div>
                            <Divider />
                          </Box>
                              </Fragment>


                      ))}
                  </div>
              </Box>
              <Box className={classes.form}>
                  <Button
                      variant="contained"
                      className="btn btn-primary mr-2"
                      type="submit"
                      onClick={handleSubmit}>
                      Get Quote
                  </Button>
              </Box>
          </FormControl>
          <Box className={classes.output}>
              <CardWithIcon title="Your Quote:" subtitle={freightAmount} icon={LocalShippingIcon} />
          </Box>
          <VerticalSpacer />
              { configData.mode === "production" ? "" : <pre>
                  {"shipToZip:"} { JSON.stringify(shipToZip.text, null, 2)},
                  {"custFreightType:"} {JSON.stringify(custFreightType, null, 2)},
                  {"lines:"} {JSON.stringify(lines, null, 2)}
              </pre>}


      </Container>
  );

};

export default FreightQuote;
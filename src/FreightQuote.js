import React, { useState } from "react";
import { useNotify, fetchStart, fetchEnd } from 'react-admin';
import { useDispatch } from "react-redux";
import configData from "./config.json";
import {Fragment} from "react";

function handleErrors(response) {
    if (!response.ok) {
        throw Error(response.statusText);
    }
    return response;
}

const FreightQuote = () => {
    const dispatch = useDispatch();
    const notify = useNotify();
    const [freightAmount, setFreightAmount] = useState(0);
    const [shipToZip, setShipToZip] = useState('');
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
                "unitSize": "Full Size"
            }
        ]
    );
    const handleLinesChange = (index, event) => {
        const values = [...lines];
        if (event.target.name === "itemNumber") {
              lines[index].itemNumber = event.target.value;
              dispatch(fetchStart());
              fetch(configData.mode === "production" ? configData.apiUrl + `/items/` + lines[index].itemNumber :
                      `/items/` + lines[index].itemNumber,
                  {method: 'GET' })
                  .then(handleErrors)
                  .then(response => response.json())
                  .then(json => {
                      lines[index].itemWidth = json[0].width;
                      lines[index].itemDepth = json[0].depth;
                      lines[index].itemHeight = json[0].height;
                      lines[index].itemWeight = json[0].weight;
                  })
                  .catch((e) => {
                    notify('Problem getting item data: ' + e,'warning',
                        {},false, 5000)
                  })
                  .finally(() => {
                      dispatch(fetchEnd());
                  })
        } else {
            lines[index].itemQty = event.target.value;
        }

        setLines(values);
    };
    const handleInputChange = (event) => {
        const [zipValue, freightValue] = [...shipToZip, custFreightType];
        if (event.target.name === "shipToZip") {
            setShipToZip(event.target.value);
        } else if (event.target.name === "custFreightType") {
            setCustFreightType(event.target.value);
        }
    };
    const handleAddFields = () => {
        const values = [...lines];
        lines.push({
            itemNumber: '',
            itemQty: '',
            itemWeight: '0',
            itemHeight: '0',
            itemDepth: '0',
            itemWidth: '0',
            unitSize: 'Full Size'
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
        dispatch(fetchStart());
        const formBody = {
            shipToZip: shipToZip,
            custFreightType: custFreightType,
            lines : lines
        };
        fetch(configData.mode === "production" ? configData.apiUrl + `/freight_quote` : `/freight_quote`,
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
                    notify('Problem getting item data: ' + e,'warning',
                        {},false, 5000)
                  })
                  .finally(() => {
                      dispatch(fetchEnd());
                  })
    };


  return (
      <>
          <h1>Freight Quote</h1>
          <form onSubmit={handleSubmit}>
              <label>
                  Zip Code:
                  <input onChange={event => handleInputChange(event)}
                      name="shipToZip" type="text" value={shipToZip} />
              </label>
              <br />
              <label>
                  Freight Type:
                  <select onChange={event => handleInputChange(event)} name="custFreightType" value={custFreightType}>
                      <option value="Dealer">Dealer</option>
                      <option value="Drop Ship">Drop Ship</option>
                      <option value="White Glove">White Glove</option>
                  </select>
              </label>
              <div className="form-row">
                  {lines.map((lines, index) => (
                      <Fragment key={`${lines}~${index}`}>
                          <div className="form-group col-sm-6">
                              <label htmlFor="itemNumber">Item Number</label>
                              <input onChange={event => handleLinesChange(index, event)}onin
                                     type="text"
                                     className="form-control"
                                     id="itemNumber"
                                     name="itemNumber"
                                     value={lines.itemNumber}
                              />
                          </div>
                          <div className="form-group col-sm-4">
                              <label htmlFor="itemQty">Qty</label>
                              <input onChange={event => handleLinesChange(index, event)}
                                     type="text"
                                     className="form-control"
                                     id="itemQty"
                                     name="itemQty"
                                     value={lines.itemQty}
                              />
                          </div>
                          <div className="form-group col-sm-2">
                              <button onClick={() => handleRemoveFields(index)}
                                      className="btn btn-link"
                                      type="button">
                                  -
                              </button>
                              <button onClick={() => handleAddFields(index)}
                                      className="btn btn-link"
                                      type="button">
                                  +
                              </button>
                          </div>
                      </Fragment>
                  ))}
              </div>
              <div className="submit-button">
                  <button
                      className="btn btn-primary mr-2"
                      type="submit"
                      onSubmit={handleSubmit}>
                      Get Quote
                  </button>
              </div>
              <br />
              { configData.mode === "production" ? "" : <pre>
                  {"shipToZip:"} { JSON.stringify(shipToZip, null, 2)},
                  {"custFreightType:"} {JSON.stringify(custFreightType, null, 2)},
                  {"lines:"} {JSON.stringify(lines, null, 2)}
              </pre>}
              <pre>
                  Your quote is: ${JSON.stringify(freightAmount, null, 2)}
              </pre>
          </form>
      </>
  );

};

export default FreightQuote;
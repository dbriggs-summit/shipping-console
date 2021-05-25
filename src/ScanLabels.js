import React, { useState } from "react";
import BarcodeScanner from "react-barcode-reader";
import { useNotify, fetchStart, fetchEnd } from 'react-admin';
import { useDispatch } from "react-redux";
import configData from "./config.json";

function handleErrors(response) {
    if (!response.ok) {
        throw Error(response.statusText);
    }
    return response;
}



const ScanLabels = () => {
  //const result = 'No result';
  //const update = useScan;
    const dispatch = useDispatch();
    //const redirect = useRedirect();
    const notify = useNotify();
    const [loading, setLoading] = useState(false);
    const handleScan = (data) => {
        if(!data.startsWith("w") || data.split(" ").length !== 3) {
            notify('Please enter a valid matrix label', 'warning',
                {},false, 5000)
        }
        else {
            const words = data.split(" ");
            const upc_code = words[0].slice(1);
            const order_id = words[1];
            setLoading(true);
            dispatch(fetchStart());
            const newScan = new FormData();
            newScan.append('upc_code', upc_code);
            newScan.append('order_id', order_id);
            //fetch(`http://10.30.30.13:8000/scan_confirm`, { method: 'PUT', body: newScan })
            fetch(configData.mode === "production" ? configData.apiUrl + `/scan_confirm` : `/scan_confirm`, { method: 'PUT', body: newScan })
                .then(handleErrors)
                .then(response => response.text())
                .then(text => {
                        if(text.substring(0,6) === "\"Error") {
                            throw Error(text);
                        }
                })
                .then(() => {
                    notify('Scan Successful: ' + upc_code + ' for order # ' + order_id,
                        'info',{},false, 5000);
                })
                .catch((e) => {
                    notify('Problem with scan: ' + e,'warning',
                        {},false, 5000)
                })
                .finally(() => {
                    setLoading(false);
                    dispatch(fetchEnd());
                });
        }
    };

  const handleError = (err) => {
    console.error(err);
  };
  return (
    <div>
      <BarcodeScanner
        onError={handleError}
        onScan={handleScan}
      />
    </div>);

};

export default ScanLabels;
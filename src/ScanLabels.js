import React, { useState } from "react";
import BarcodeScanner from "react-barcode-reader";
import { useNotify, useRedirect, fetchStart, fetchEnd } from 'react-admin';
import { useDispatch } from "react-redux";

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
    const redirect = useRedirect();
    const notify = useNotify();
    const [loading, setLoading] = useState(false);
    const handleScan = (data) => {
        if(!data.startsWith("w") || data.split(" ").length !== 3) {
            notify('Please enter a valid matrix label', 'warning')
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
            fetch(`/scan_confirm`, { method: 'PUT', body: newScan })
                .then(handleErrors)
                .then(() => {
                    notify('Scan Successful: ' + upc_code + ' for order # ' + order_id);
                })
                .catch((e) => {
                    notify('Error: Problem with scan: ' + e,'warning')
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
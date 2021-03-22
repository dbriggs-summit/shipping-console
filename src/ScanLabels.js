import React, {Component} from "react";
import BarcodeScanner from "react-barcode-reader";

class Scanner extends Component {
  constructor(props){
    super(props)
    this.state = {
      result: 'No result',
    }

    this.handleScan = this.handleScan.bind(this)
  }
  handleScan(data){
    this.setState({
      result: data,
    })
  }
  handleError(err){
    console.error(err)
  }
  render(){

    return(
      <div>
        <BarcodeScanner
          onError={this.handleError}
          onScan={this.handleScan}
          />
        <p>{this.state.result}</p>
      </div>
    )
  }
}

const ScanLabels = () => (
    <Scanner />

);

export default ScanLabels;
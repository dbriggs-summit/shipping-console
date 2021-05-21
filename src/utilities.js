import configData from "./config.json";

function today_date() {
    const today = configData.mode === 'development' ? new Date(2021, 2, 4) : new Date(); //January is 0

    const dd = String(today.getDate()).padStart(2, '0');
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const yyyy = today.getFullYear();

    return yyyy + '-' + mm + '-' + dd;
}

export default today_date;
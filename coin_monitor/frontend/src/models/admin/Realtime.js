
import axios from "axios";


class Realtime {
    

    getListSymbol() {
		
		return axios.request({
			url: '/api/realtime/getListSymbol',
			method: 'POST',
		})
			.then(response => {
				// App.loading(false, 'Loading...');
				response = response['data'];
                
				if(response['result']){
                    response = response['data']
                    return response.map((x) => {return {code: x['testnet_symbol'], name: x['testnet_symbol']}})
                }
			})

			.catch((error) => {
				console.log(error);
				// App.loading(false, 'Loading...');
				// error_handle(error)
				return false;
			})
	}


    getListAccount() {
		
		return axios.request({
			url: '/api/realtime/getListAccount',
			method: 'POST',
		})
			.then(response => {
				// App.loading(false, 'Loading...');
				response = response['data'];
				if(response['result']){
                    response = response['data']
                    return response.map((x) => {return {code: x['testnet_account_id'], name: x['testnet_account_name']}})
                }
			})

			.catch((error) => {
				console.log(error);
				// App.loading(false, 'Loading...');
				// error_handle(error)
				return false;
			})
	}


    updateChart(account, symbol, date){
        global.App.loading.loading(true, 'Updating...')
        return axios.request({
			url: '/api/realtime/updateChart',
			method: 'POST',
            data: {
                account, symbol, date
            }
		})
			.then(response => {
				global.App.loading.loading(false)
				response = response['data'];
				if(response['result']){
                    response = response['data']
                    return response.map((x) => {return {code: x['testnet_account_id'], name: x['testnet_account_name']}})
                }
			})

			.catch((error) => {
                global.App.loading.loading(false)
				console.log(error);
				// App.loading(false, 'Loading...');
				// error_handle(error)
				return false;
			})
    }



}

export default Realtime;
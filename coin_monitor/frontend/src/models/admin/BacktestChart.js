
import axios from "axios";


class BacktestChart {
    

    getListSymbol() {
		
		return axios.request({
			url: '/backtest/chart/getListSymbol',
			method: 'POST',
		})
			.then(response => {
				// App.loading(false, 'Loading...');
				response = response['data'];
                
				if(response['result']){
                    response = response['data']
                    return response.map((x) => {return {code: x['lab_campaign_symbol'], name: x['lab_campaign_symbol']}})
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
			url: '/backtest/chart/getListAccount',
			method: 'POST',
		})
			.then(response => {
				// App.loading(false, 'Loading...');
				response = response['data'];
				if(response['result']){
                    response = response['data']
                    return response.map((x) => {return {code: x['lab_account_id'], name: x['lab_account_name']}})
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
			url: '/backtest/chart/updateChart',
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
                    return response.map((x) => {return {code: x['lab_account_id'], name: x['lab_account_name']}})
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

	getStatistic(account, symbol){
        global.App.loading.loading(true, 'Statistic...')
        return axios.request({
			url: '/backtest/chart/getStatistic',
			method: 'POST',
            data: {
                account, symbol
            }
		})
			.then(response => {
				global.App.loading.loading(false)
				response = response['data'];
				if(response['result']){
                    response = response['data']
                    return response
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

export default BacktestChart;
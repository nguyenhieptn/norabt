// import Lab_account from "./Lab_account";
import Watchlist from "./Watchlist";
import Testnet_account from "./Testnet_account"
import Exchange_account from "./Accounts"

class ChartFelxModel{
    constructor(){
        this.getChartFieldResult = {}
    }

    getDatabase(){
        if(this.getDatabaseResult) return this.getDatabaseResult
        App.loading(true, 'Loading...');
		this.getDatabaseResult = axios.request({
			url: '/admin/chartflex/getDatabase',
			method: 'POST',
		}) 

			.then(response => {
				App.loading(false, 'Loading...');
				response = response['data'];
                if(response['result']){
                    response = response['data']
                    var options = [{'value':'', 'label': '-- Select Database --'}]
                    for(let db in response){
                        options.push({
                            'value': db,
                            'label': response[db]
                        })
                    }
                    return options
                }else{
                    error_handle(response)
                }
				
			})

			.catch((error) => {
				console.log(error);
				App.loading(false, 'Loading...');
				error_handle(error)
				return false;
			})

        return this.getDatabaseResult
    }

    getSourceOptions(database){
        if(this.getSourceOptionsResult) return this.getSourceOptionsResult
        App.loading(true, 'Loading...');
		this.getSourceOptionsResult = axios.request({
			url: '/admin/chartflex/getChartSource',
			method: 'POST',
            data: {
                database
            }
		}) 

			.then(response => {
				App.loading(false, 'Loading...');
				response = response['data'];
                if(response['result']){
                    response = response['data']
                    var options = [{'value':'', 'label': '-- Select Source --'}]
                    for(let db of response){
                        options.push({
                            'value': db,
                            'label': db
                        })
                    }
                    return options
                }else{
                    error_handle(response)
                }
				
			})

			.catch((error) => {
				console.log(error);
				App.loading(false, 'Loading...');
				error_handle(error)
				return false;
			})

        return   this.getSourceOptionsResult

    }


    getChartField(database, source){
        if(!source) return Promise.resolve([])
        if(this.getChartFieldResult[source]) return this.getChartFieldResult[source]
        App.loading(true, 'Loading...');
		this.getChartFieldResult[source] = axios.request({
			url: '/admin/chartflex/getChartField',
			method: 'POST',
            data:{
                database: database,
                source: source
            }
		}) 

			.then(response => {
				App.loading(false, 'Loading...');
				response = response['data'];
                if(response['result']){
                    response = response['data']
                    var options = [{'value':'', 'label': '-- Select Field --'}]
                    for(let db of response){
                        options.push({
                            'value': db,
                            'label': db
                        })
                    }
                    return options
                }else{
                    error_handle(response)
                }
				
			})

			.catch((error) => {
				console.log(error);
				App.loading(false, 'Loading...');
				error_handle(error)
				return false;
			})

        return this.getChartFieldResult[source]

    }

    getWatchlist(){
        if(this.getWatchlistResult) return this.getWatchlistResult;
        App.loading(true);
        this.wlModel = new Watchlist()
       
        this.getWatchlistResult = this.wlModel.read().then(res => {
            if(res){
                if(res['result']){
                    var data = res['data'].sort((a,b)=>a[WL_SYMBOL]>b[WL_SYMBOL]?1:-1);
                    var options = [{'value':'', 'label': '-- Select Symbol --'}]
                    data.map(item => {
                        options.push({
                            'value': item[WL_SYMBOL],
                            'label': item[WL_SYMBOL]
                        })
                    })

                    return options;
                }
            }
        })
        
        return this.getWatchlistResult
    }


    getAccounts(mode){
        App.loading(true);

        this.model = mode == "test_net" ?  new Testnet_account() :  new Exchange_account()
        let colName = mode == "test_net" ? TESTNET_ACCOUNT_NAME :  ACCOUNT_NAME
        let colID =  mode == "test_net" ? TESTNET_ACCOUNT_ID :  ACCOUNT_ID
      
        return this.model.read().then(res => {
            if(res){
                if(res['result']){
                    
                    var data = res['data'].sort((a,b)=>a[colName]>b[colName]?1:-1);
                   
                    var options = [{'value':'', 'label': '-- Select Account --'}]
                    data.map(item => {
                        options.push({
                            'value': item[colID],
                            'label': item[colName]
                        })
                    })
                    return options;
                }
            }
        })
    }


    getData(config, startTime, stopTime){
        
		return axios.request({
			url: '/admin/chartflex/getData',
			method: 'POST',
            data:{
                configuration: config,
                start_time: startTime,
                stop_time: stopTime
            }
		}) 

			.then(response => {
				response = response['data'];
                if(response['result']){
                    response = response['data']
                    return response
                }else{
                    error_handle(response)
                }
				
			})

			.catch((error) => {
				console.log(error);
				error_handle(error)
				return false;
			})
    }


    getPosition(account , symbol, startTime, stopTime , mode){
        
		return axios.request({
			url: '/admin/chartflex/getPosition',
			method: 'POST',
            data:{
                account,
                symbol,
                startTime,
                stopTime,
                mode,
            }
		}) 

			.then(response => {
				response = response['data'];
                if(response['result']){
                    response = response['data']
                    return response
                }else{
                    error_handle(response)
                }
				
			})

			.catch((error) => {
				console.log(error);
				error_handle(error)
				return false;
			})
    }



    
}

export default ChartFelxModel;
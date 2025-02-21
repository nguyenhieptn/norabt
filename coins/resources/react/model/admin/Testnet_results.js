import { result } from "lodash";
import model from "../model";

class Testnet_results extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/testnet_results/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/testnet_results/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/testnet_results/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/testnet_results/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/testnet_results/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/testnet_results/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/testnet_results/read',
                method: 'POST'
            },
            map: {
                link: '/admin/testnet_results/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/testnet_results/filter',
                method: 'POST'
            },
            get: {
                link: '/admin/testnet_results/get',
                method: 'POST'
            },
        }

        if(!App.getTestnetResultByStrategy) App.getTestnetResultByStrategy = {};
        if(!App.getTestnetResultByAccount) App.getTestnetResultByAccount = {};

        this.lastUpdate = 0;
    }

    
    getByStrategy(strategy){

        var time = Number(moment().format('x'));
        if(App.getTestnetResultByStrategy[strategy] && time - this.lastUpdate < 5000) return App.getTestnetResultByStrategy[strategy]
        this.lastUpdate = time;

        App.getTestnetResultByStrategy[strategy] = this.getAll().then(res => {
            var returnData = [];
            if(res['result']){
                for(let i in res['data']){
                    if(res['data'][i][TESTNET_RESULT_STRATEGY] == strategy){
                        returnData.push(res['data'][i]);
                    }
                }
            }
            return {result:true, data:returnData};
        })

        return App.getTestnetResultByStrategy[strategy];
    }

    getAll(){
        var time = Number(moment().format('x'));
        if(App.getAllTestnetResult && time - this.lastUpdate < 5000) return App.getAllTestnetResult
        this.lastUpdate = time;
        App.getAllTestnetResult = this.get([[["testnet_result_strategy", "=", App.strategySelector.selected()]]], {'orderBy' : TESTNET_RESULT_SELL_TIME, 'asc': false});

        return App.getAllTestnetResult;
    }

    getByAccountTestnet(account){

        var time = Number(moment().format('x'));
        if(App.getTestnetResultByAccount[account] && time - this.lastUpdate < 5000) return App.getTestnetResultByAccount[account]
        this.lastUpdate = time;
       
        App.getTestnetResultByAccount[account] = this.getAllAccount().then(res => {
            var returnData = [];
            if(res['result']){
                for(let i in res['data']){
                    if(res['data'][i][TESTNET_RESULT_ACCOUNT] == account){
                        returnData.push(res['data'][i]);
                    }
                }
            }
            return {result:true, data:returnData};
        })

        return App.getTestnetResultByAccount[account];
    }
    getAllAccount(){
        var time = Number(moment().format('x'));
        if(App.getAllTestnetResultAccount && time - this.lastUpdate < 5000) return App.getAllTestnetResultAccount
        this.lastUpdate = time;
        App.getAllTestnetResultAccount = this.get([], {'orderBy' : TESTNET_RESULT_SELL_TIME, 'asc': false});

        return App.getAllTestnetResultAccount;
    }

   

    readAll(){
      var result =  this.get([], {'orderBy' : TESTNET_RESULT_SELL_TIME, 'asc': false});
      return result;
    }

    

    getUpdateData(){
        return axios.request({
			url: '/admin/testnet_results/updateData',
			method: 'POST',
		})
			.then(response => {
				response = response['data'];
                var indexData = {};
                if(response['result']){
                    for(let data of response['data']){
                        indexData[data[TESTNET_RESULT_ID]] = data;
                    }
                }
				return indexData;
			})

			.catch((error) => {
				console.log(error);
				error_handle(error)
				return false;
			})
    }
}

export default Testnet_results;
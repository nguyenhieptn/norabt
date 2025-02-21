import model from "../model";

class Lab_results extends model {
    constructor() {
        super();
        this.links = {
            add: {
                link: '/admin/lab_results/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/lab_results/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/lab_results/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/lab_results/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/lab_results/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/lab_results/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/lab_results/read',
                method: 'POST'
            },
            map: {
                link: '/admin/lab_results/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/lab_results/filter',
                method: 'POST'
            },
            get: {
                link: '/admin/lab_results/get',
                method: 'POST'
            },
        }
    }

    getByStrategy(){
        if(App.getLabResultStrategy ) return App.getLabResultStrategy
        App.getLabResultStrategy = this.get([[[LAB_RESULT_STRATEGY, '=', App.strategySelector.selected()]]], { 'orderBy': LAB_RESULT_SELL_TIME, 'asc': false });

        return App.getLabResultStrategy;
    }

    getByAccount(accountID = null){
        if(accountID == null) accountID = App.accountSelectorLab.selected()
        if(!isset(App.getLabResultAccount)) App.getLabResultAccount = {}
        if(App.getLabResultAccount[accountID] ) return App.getLabResultAccount[accountID]
        App.getLabResultAccount[accountID] = this.get([[[LAB_RESULT_ACCOUNT, '=', accountID]]], { 'orderBy': LAB_RESULT_CHART, 'asc': false });
        setTimeout(()=>{App.getLabResultAccount[accountID] = null}, 60000)
        return App.getLabResultAccount[accountID];
    }

    updateIndicator(data){
        App.loading(true, 'Loading...');
		return axios.request({
			url: '/admin/lab_results/updateIndicator',
			method: 'POST',
			data: {...data}
		}) 

			.then(response => {
				App.loading(false, 'Loading...');
				response = response['data'];
				return response;
			})

			.catch((error) => {
				console.log(error);
				App.loading(false, 'Loading...');
				error_handle(error)
				return false;
			})

    }

    updateWalletBalance(data){
        App.loading(true, 'Loading...');
		return axios.request({
			url: '/admin/lab_results/updateWalletBalance',
			method: 'POST',
			data: {...data}
		}) 

			.then(response => {
				App.loading(false, 'Loading...');
				response = response['data'];
				return response;
			})

			.catch((error) => {
				console.log(error);
				App.loading(false, 'Loading...');
				error_handle(error)
				return false;
			})

    }

    updateProfitInvest(data){
        App.loading(true, 'Loading...');
		return axios.request({
			url: '/admin/lab_results/updateProfitInvest',
			method: 'POST',
			data: {...data}
		}) 

			.then(response => {
				App.loading(false, 'Loading...');
				response = response['data'];
				return response;
			})

			.catch((error) => {
				console.log(error);
				App.loading(false, 'Loading...');
				error_handle(error)
				return false;
			})

    }
}

export default Lab_results;
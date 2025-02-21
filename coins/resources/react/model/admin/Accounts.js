import model from "../model";

class Accounts extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/accounts/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/accounts/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/accounts/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/accounts/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/accounts/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/accounts/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/accounts/read',
                method: 'POST'
            },
            map: {
                link: '/admin/accounts/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/accounts/filter',
                method: 'POST'
            },
        }
    }

    getAvailableBallance(id){
        App.loading(true);
        return axios.request({
			url: '/admin/accounts/getAccount',
			method: 'POST',
			data: {
                id
            }
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

    getPositions(id){
        App.loading(true);
        return axios.request({
			url: '/admin/accounts/getPositions',
			method: 'POST',
			data: {
                id
            }
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

    getTrade(id,symbol,startTime,endTime){
        App.loading(true);
        return axios.request({
			url: '/admin/accounts/getTrade',
			method: 'POST',
			data: {
                id,
                symbol,
                startTime,
                endTime
            }
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

    count(){
        App.loading(true);
        return axios.request({
			url: '/admin/accounts/count',
			method: 'POST',
			
		})
			.then(response => {
				App.loading(false, 'Loading...');
				response = response['data'];
                if(response['result']) return response['data'];
				return 0;
			})

			.catch((error) => {
				console.log(error);
				App.loading(false, 'Loading...');
				error_handle(error)
				return false;
			})
    }


    restartTrading(id){
        App.loading(true);
        return axios.request({
			url: '/admin/accounts/restartTrading',
			method: 'POST',
            data: {
                id
            }
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

    stopTrading(id){
        App.loading(true);
        return axios.request({
			url: '/admin/accounts/stopTrading',
			method: 'POST',
            data: {
                id
            }
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

	getIncom(id , type){
        App.loading(true);
        return axios.request({
			url: '/admin/accounts/getIncom',
			method: 'POST',
            data: {
                id,
				incomeType : type
            }
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

export default Accounts;
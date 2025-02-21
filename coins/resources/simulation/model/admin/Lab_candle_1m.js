import model from "../model";

class Lab_candle_1m extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/lab_candle_1m/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/lab_candle_1m/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/lab_candle_1m/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/lab_candle_1m/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/lab_candle_1m/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/lab_candle_1m/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/lab_candle_1m/read',
                method: 'POST'
            },
            map: {
                link: '/admin/lab_candle_1m/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/lab_candle_1m/filter',
                method: 'POST'
            },
            get: {
                link: '/admin/lab_candle_1m/get',
                method: 'POST'
            },
        }
    }

    showdb(db){
        App.loading(true);
		return axios.request({
			url: '/admin/lab_candle_3m/showdb',
			method: 'POST',
            data :{
                ...db
            }
		}) 

			.then(response => {
				App.loading(false, 'Adding...');
				response = response['data'];
				return response;
			})

			.catch((error) => {
				console.log(error);
				App.loading(false, 'Adding...');
				error_handle(error)
				return false;
			})
    }


    getMissData(dbName, symbols){
        App.loading(true);
		return axios.request({
			url: '/admin/lab_candle_1m/getMissData',
			method: 'POST',
            data :{
                symbols: symbols,
                dbName: dbName
            }
		}) 

			.then(response => {
				App.loading(false, 'Adding...');
				response = response['data'];
				return response;
			})

			.catch((error) => {
				console.log(error);
				App.loading(false, 'Adding...');
				error_handle(error)
				return false;
			})
    }
}

export default Lab_candle_1m;
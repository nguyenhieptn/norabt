import model from "../model";

class Lab_candle_1d extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/lab_candle_1d/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/lab_candle_1d/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/lab_candle_1d/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/lab_candle_1d/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/lab_candle_1d/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/lab_candle_1d/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/lab_candle_1d/read',
                method: 'POST'
            },
            get: {
                link: '/admin/lab_candle_1d/get',
                method: 'POST'
            },
            map: {
                link: '/admin/lab_candle_1d/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/lab_candle_1d/filter',
                method: 'POST'
            },
        }
    }


    getFluctuation(data){
        App.loading(true, 'Loading...');
		return axios.request({
			url: '/admin/lab_candle_1d/getFluctuation',
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

export default Lab_candle_1d;
import model from "../model";

class Candle_4h extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/candle_4h/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/candle_4h/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/candle_4h/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/candle_4h/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/candle_4h/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/candle_4h/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/candle_4h/read',
                method: 'POST'
            },
            map: {
                link: '/admin/candle_4h/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/candle_4h/filter',
                method: 'POST'
            },
            get: {
                link: '/admin/candle_4h/get',
                method: 'POST'
            },
        }
    }

    getTrend3() {
		
		App.loading(true, 'getData...');
		return axios.request({
			url: '/admin/candle_4h/getTrend3',
			method: 'POST',
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

    getAll(){
        if (App.getCandle4hAll) return App.getCandle4hAll;
        App.loading(true);
        App.getCandle4hAll = this.read({ [CANDLE_4H_SYMBOL]: 'BTCUSDT' }, { 'orderBy': CANDLE_4H_CLOSE_TIME, 'asc': true });
        return App.getCandle4hAll
    }
}

export default Candle_4h;
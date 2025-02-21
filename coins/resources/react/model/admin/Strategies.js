import model from "../model";

class Strategies extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/strategies/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/strategies/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/strategies/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/strategies/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/strategies/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/strategies/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/strategies/read',
                method: 'POST'
            },
            map: {
                link: '/admin/strategies/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/strategies/filter',
                method: 'POST'
            },
        }
    }

    count(){
        App.loading(true);
        return axios.request({
			url: '/admin/strategies/count',
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

    
}

export default Strategies;
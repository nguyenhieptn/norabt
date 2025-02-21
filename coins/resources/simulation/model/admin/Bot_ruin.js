import model from "../model";

class Bot_ruin extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/bot_ruin/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/bot_ruin/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/bot_ruin/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/bot_ruin/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/bot_ruin/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/bot_ruin/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/bot_ruin/read',
                method: 'POST'
            },
            map: {
                link: '/admin/bot_ruin/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/bot_ruin/filter',
                method: 'POST'
            },
        }
    }

    run_ruin(data) {

		App.loading(true)
		return axios.request({
			url: `/admin/bot_ruin/run_ruin`,
			method: 'POST',
			data: {
				...data
			}
		})

			.then(response => {
				App.loading(false);
				response = response['data'];
				if (response['result']) {
					return true
				}
				else {
					error_handle(response);
				}
			})

			.catch((error) => {
				App.loading(false);
				error_handle(error)
				return false;
			})
	}

    stop_ruin(data) {

		App.loading(true)
		return axios.request({
			url: `/admin/bot_ruin/stop_ruin`,
			method: 'POST',
			data: {
				...data
			}
		})

			.then(response => {
				App.loading(false);
				response = response['data'];
				if (response['result']) {
					return true
				}
				else {
					error_handle(response);
				}
			})

			.catch((error) => {
				App.loading(false);
				error_handle(error)
				return false;
			})
	}

    get_excel(data) {

		App.loading(true)
		return axios.request({
			url: `/admin/bot_ruin/get_excel`,
			method: 'POST',
			data: {
				...data
			}
		})

			.then(response => {
				App.loading(false);
				response = response['data'];
				return response
			
			})

			.catch((error) => {
				App.loading(false);
				error_handle(error)
				return false;
			})
	}
}

export default Bot_ruin;
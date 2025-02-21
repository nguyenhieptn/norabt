import model from "../model";

class Account_summary extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/account_summary/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/account_summary/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/account_summary/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/account_summary/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/account_summary/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/account_summary/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/account_summary/read',
                method: 'POST'
            },
            map: {
                link: '/admin/account_summary/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/account_summary/filter',
                method: 'POST'
            },
        }
    }

    calculate() {
		
		App.loading(true, 'Calculate...');
		return axios.request({
			url: '/admin/account_summary/calculate',
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

}

export default Account_summary;
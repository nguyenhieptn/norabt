import model from "../model";

class Lab_account extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/lab_account/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/lab_account/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/lab_account/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/lab_account/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/lab_account/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/lab_account/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/lab_account/read',
                method: 'POST'
            },
            map: {
                link: '/admin/lab_account/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/lab_account/filter',
                method: 'POST'
            },
        }
    }

    getGroup(){
        App.loading(true, 'Loading...');
		return axios.request({
			url: '/admin/lab_account/getGroup',
			method: 'POST',
			data: {}
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


    changeGroupName(newGroup,oldGroup){
        App.loading(true, 'Loading...');
		return axios.request({
			url: '/admin/lab_account/editGroup',
			method: 'POST',
			data: {
                'new_group' : newGroup,
                'old_group' : oldGroup,

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

    getLog(id){
        App.loading(true, 'Loading...');
		return axios.request({
			url: '/admin/lab_account/getLog',
			method: 'POST',
			data: {'id': id}
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

export default Lab_account;
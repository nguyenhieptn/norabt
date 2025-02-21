import model from "../../../react/model/model";

class Lab_strategies extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/lab_strategies/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/lab_strategies/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/lab_strategies/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/lab_strategies/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/lab_strategies/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/lab_strategies/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/lab_strategies/read',
                method: 'POST'
            },
            map: {
                link: '/admin/lab_strategies/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/lab_strategies/filter',
                method: 'POST'
            },
        }
    }

    getGroup(){
        App.loading(true, 'Loading...');
		return axios.request({
			url: '/admin/lab_strategies/getGroup',
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
			url: '/admin/lab_strategies/editGroup',
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
}

export default Lab_strategies;
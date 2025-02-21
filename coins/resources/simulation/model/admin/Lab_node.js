import model from "../model";

class Lab_node extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/lab_node/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/lab_node/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/lab_node/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/lab_node/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/lab_node/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/lab_node/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/lab_node/read',
                method: 'POST'
            },
            map: {
                link: '/admin/lab_node/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/lab_node/filter',
                method: 'POST'
            },
        }
    }


    getSystemInfo(server){
        App.loading(true, 'Loading...');
		return axios.request({
			url: '/admin/lab_node/getSystemInfo',
			method: 'POST',
			data: {'server': server}
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

export default Lab_node;
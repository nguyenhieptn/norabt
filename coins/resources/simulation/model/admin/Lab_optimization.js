import model from "../../../react/model/model";

class Lab_optimization  extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/lab_optimization/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/lab_optimization/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/lab_optimization/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/lab_optimization/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/lab_optimization/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/lab_optimization/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/lab_optimization/read',
                method: 'POST'
            },
            map: {
                link: '/admin/lab_optimization/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/lab_optimization/filter',
                method: 'POST'
            },
        }
    }


    

    getLog(id){
        App.loading(true, 'Loading...');
		return axios.request({
			url: '/admin/lab_optimization/getLog',
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

export default Lab_optimization ;
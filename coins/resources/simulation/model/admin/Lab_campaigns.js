import model from "../model";

class Lab_campaigns extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/lab_campaigns/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/lab_campaigns/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/lab_campaigns/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/lab_campaigns/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/lab_campaigns/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/lab_campaigns/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/lab_campaigns/read',
                method: 'POST'
            },
            map: {
                link: '/admin/lab_campaigns/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/lab_campaigns/filter',
                method: 'POST'
            },
           
        }
    }

    updateRank(data){
        App.loading(true, 'Loading...');
		return axios.request({
			url: '/admin/lab_campaigns/updateRank',
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

export default Lab_campaigns;
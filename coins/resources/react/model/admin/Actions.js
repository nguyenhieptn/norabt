import model from "../model";

class Actions extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/actions/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/actions/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/actions/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/actions/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/actions/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/actions/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/actions/read',
                method: 'POST'
            },
            map: {
                link: '/admin/actions/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/actions/filter',
                method: 'POST'
            },
            get: {
                link: '/admin/actions/get',
                method: 'POST'
            },
        }
   
        if(!App.getAllActions) App.getAllActions = {};
    }

    
    getAll(account){

        if(App.getAllActions[account]) return App.getAllActions[account]

        App.getAllActions[account] = this.get([[[ACTION_ACCOUNT, '=', account]]], {'orderBy' : ACTION_SELL_TIME, 'asc': false});

        setTimeout(()=>App.getAllActions = {} , 5000);

        return App.getAllActions[account];
    }

    getUpdateData(){
        return axios.request({
			url: '/admin/actions/updateData',
			method: 'POST',
		})
			.then(response => {
				response = response['data'];
                var indexData = {};
                if(response['result']){
                    for(let data of response['data']){
                        indexData[data[ACTION_ID]] = data;
                    }
                }
				return indexData;
			})

			.catch((error) => {
				console.log(error);
				error_handle(error)
				return false;
			})
    }

}

export default Actions;
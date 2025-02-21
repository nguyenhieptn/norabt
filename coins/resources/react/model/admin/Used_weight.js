import model from "../model";

class Used_weight extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/used_weight/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/used_weight/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/used_weight/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/used_weight/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/used_weight/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/used_weight/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/used_weight/read',
                method: 'POST'
            },
            map: {
                link: '/admin/used_weight/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/used_weight/filter',
                method: 'POST'
            },
        }
    }
}

export default Used_weight;
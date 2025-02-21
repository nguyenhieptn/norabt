import model from "../model";

class Change_24h extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/change_24h/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/change_24h/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/change_24h/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/change_24h/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/change_24h/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/change_24h/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/change_24h/read',
                method: 'POST'
            },
            map: {
                link: '/admin/change_24h/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/change_24h/filter',
                method: 'POST'
            },
            get: {
                link: '/admin/change_24h/get',
                method: 'POST'
            },
        }
    }
}

export default Change_24h;
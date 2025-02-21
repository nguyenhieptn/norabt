import model from "../model";

class Params extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/params/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/params/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/params/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/params/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/params/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/params/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/params/read',
                method: 'POST'
            },
            map: {
                link: '/admin/params/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/params/filter',
                method: 'POST'
            },
        }
    }
}

export default Params;
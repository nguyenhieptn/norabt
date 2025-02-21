import model from "../model";

class System_info extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/system_info/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/system_info/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/system_info/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/system_info/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/system_info/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/system_info/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/system_info/read',
                method: 'POST'
            },
            map: {
                link: '/admin/system_info/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/system_info/filter',
                method: 'POST'
            },
        }
    }
}

export default System_info;
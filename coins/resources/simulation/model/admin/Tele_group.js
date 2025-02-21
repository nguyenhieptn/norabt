import model from "../model";

class Tele_group extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/tele_group/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/tele_group/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/tele_group/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/tele_group/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/tele_group/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/tele_group/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/tele_group/read',
                method: 'POST'
            },
            map: {
                link: '/admin/tele_group/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/tele_group/filter',
                method: 'POST'
            },
        }
    }
}

export default Tele_group;
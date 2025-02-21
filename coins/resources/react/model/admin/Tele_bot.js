import model from "../model";

class Tele_bot extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/tele_bot/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/tele_bot/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/tele_bot/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/tele_bot/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/tele_bot/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/tele_bot/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/tele_bot/read',
                method: 'POST'
            },
            map: {
                link: '/admin/tele_bot/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/tele_bot/filter',
                method: 'POST'
            },
        }
    }
}

export default Tele_bot;
import model from "../model";

class Events extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/events/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/events/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/events/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/events/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/events/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/events/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/events/read',
                method: 'POST'
            },
            map: {
                link: '/admin/events/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/events/filter',
                method: 'POST'
            },
        }
    }
}

export default Events;
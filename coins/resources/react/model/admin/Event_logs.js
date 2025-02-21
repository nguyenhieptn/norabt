import model from "../model";

class Event_logs extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/event_logs/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/event_logs/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/event_logs/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/event_logs/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/event_logs/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/event_logs/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/event_logs/read',
                method: 'POST'
            },
            map: {
                link: '/admin/event_logs/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/event_logs/filter',
                method: 'POST'
            },
        }
    }
}

export default Event_logs;
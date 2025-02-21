import model from "../model";

class Lab_event_logs extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/lab_event_logs/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/lab_event_logs/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/lab_event_logs/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/lab_event_logs/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/lab_event_logs/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/lab_event_logs/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/lab_event_logs/read',
                method: 'POST'
            },
            map: {
                link: '/admin/lab_event_logs/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/lab_event_logs/filter',
                method: 'POST'
            },
        }
    }
}

export default Lab_event_logs;
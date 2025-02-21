import model from "../model";

class Schedule_alert extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/schedule_alert/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/schedule_alert/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/schedule_alert/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/schedule_alert/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/schedule_alert/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/schedule_alert/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/schedule_alert/read',
                method: 'POST'
            },
            map: {
                link: '/admin/schedule_alert/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/schedule_alert/filter',
                method: 'POST'
            },
        }
    }
}

export default Schedule_alert;
import model from "../model";

class Lab_schedule extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/lab_schedule/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/lab_schedule/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/lab_schedule/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/lab_schedule/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/lab_schedule/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/lab_schedule/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/lab_schedule/read',
                method: 'POST'
            },
            map: {
                link: '/admin/lab_schedule/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/lab_schedule/filter',
                method: 'POST'
            },
        }
    }
}

export default Lab_schedule;
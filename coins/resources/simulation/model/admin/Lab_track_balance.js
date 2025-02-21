import model from "../model";

class Lab_track_balance extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/lab_track_balance/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/lab_track_balance/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/lab_track_balance/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/lab_track_balance/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/lab_track_balance/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/lab_track_balance/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/lab_track_balance/read',
                method: 'POST'
            },
            map: {
                link: '/admin/lab_track_balance/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/lab_track_balance/filter',
                method: 'POST'
            },
        }
    }
}

export default Lab_track_balance;
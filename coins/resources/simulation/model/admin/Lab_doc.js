import model from "../model";

class Lab_doc extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/lab_doc/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/lab_doc/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/lab_doc/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/lab_doc/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/lab_doc/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/lab_doc/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/lab_doc/read',
                method: 'POST'
            },
            map: {
                link: '/admin/lab_doc/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/lab_doc/filter',
                method: 'POST'
            },
        }
    }
}

export default Lab_doc;
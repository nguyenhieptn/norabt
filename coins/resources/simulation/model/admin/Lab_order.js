import model from "../../../react/model/model";

class Lab_order extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/lab_order/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/lab_order/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/lab_order/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/lab_order/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/lab_order/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/lab_order/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/lab_order/read',
                method: 'POST'
            },
            map: {
                link: '/admin/lab_order/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/lab_order/filter',
                method: 'POST'
            },
        }
    }
}

export default Lab_order;
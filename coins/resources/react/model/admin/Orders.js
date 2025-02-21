import model from "../model";

class Orders extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/orders/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/orders/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/orders/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/orders/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/orders/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/orders/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/orders/read',
                method: 'POST'
            },
            map: {
                link: '/admin/orders/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/orders/filter',
                method: 'POST'
            },
        }
    }
}

export default Orders;
import model from "../model";

class Order_track extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/order_track/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/order_track/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/order_track/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/order_track/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/order_track/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/order_track/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/order_track/read',
                method: 'POST'
            },
            map: {
                link: '/admin/order_track/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/order_track/filter',
                method: 'POST'
            },
        }
    }
}

export default Order_track;
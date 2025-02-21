import model from "../model";

class Testnet_order extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/testnet_order/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/testnet_order/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/testnet_order/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/testnet_order/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/testnet_order/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/testnet_order/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/testnet_order/read',
                method: 'POST'
            },
            map: {
                link: '/admin/testnet_order/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/testnet_order/filter',
                method: 'POST'
            },
        }
    }
}

export default Testnet_order;
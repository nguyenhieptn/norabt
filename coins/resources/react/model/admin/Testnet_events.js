import model from "../model";

class Testnet_events extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/testnet_events/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/testnet_events/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/testnet_events/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/testnet_events/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/testnet_events/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/testnet_events/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/testnet_events/read',
                method: 'POST'
            },
            map: {
                link: '/admin/testnet_events/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/testnet_events/filter',
                method: 'POST'
            },
        }
    }
}

export default Testnet_events;
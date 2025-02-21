import model from "../model";

class Testnet_event_logs extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/testnet_event_logs/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/testnet_event_logs/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/testnet_event_logs/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/testnet_event_logs/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/testnet_event_logs/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/testnet_event_logs/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/testnet_event_logs/read',
                method: 'POST'
            },
            map: {
                link: '/admin/testnet_event_logs/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/testnet_event_logs/filter',
                method: 'POST'
            },
        }
    }
}

export default Testnet_event_logs;
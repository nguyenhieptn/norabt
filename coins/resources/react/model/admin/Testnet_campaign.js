import model from "../model";

class Testnet_campaign extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/testnet_campaign/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/testnet_campaign/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/testnet_campaign/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/testnet_campaign/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/testnet_campaign/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/testnet_campaign/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/testnet_campaign/read',
                method: 'POST'
            },
            map: {
                link: '/admin/testnet_campaign/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/testnet_campaign/filter',
                method: 'POST'
            },
        }
    }

  
}

export default Testnet_campaign;
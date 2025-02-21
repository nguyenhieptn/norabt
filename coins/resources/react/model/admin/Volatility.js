import model from "../model";

class Volatility extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/volatility/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/volatility/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/volatility/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/volatility/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/volatility/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/volatility/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/volatility/read',
                method: 'POST'
            },
            map: {
                link: '/admin/volatility/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/volatility/filter',
                method: 'POST'
            },
        }
    }
}

export default Volatility;
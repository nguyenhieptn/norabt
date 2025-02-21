import model from "../model";

class Volatility_history extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/volatility_history/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/volatility_history/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/volatility_history/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/volatility_history/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/volatility_history/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/volatility_history/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/volatility_history/read',
                method: 'POST'
            },
            map: {
                link: '/admin/volatility_history/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/volatility_history/filter',
                method: 'POST'
            },
        }
    }
}

export default Volatility_history;
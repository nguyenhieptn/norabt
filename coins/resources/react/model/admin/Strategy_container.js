import model from "../model";

class Strategy_container extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/strategy_container/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/strategy_container/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/strategy_container/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/strategy_container/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/strategy_container/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/strategy_container/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/strategy_container/read',
                method: 'POST'
            },
            map: {
                link: '/admin/strategy_container/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/strategy_container/filter',
                method: 'POST'
            },
        }
    }
}

export default Strategy_container;
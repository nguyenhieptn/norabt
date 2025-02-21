import model from "../model";

class Lab_strategy_container extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/lab_strategy_container/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/lab_strategy_container/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/lab_strategy_container/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/lab_strategy_container/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/lab_strategy_container/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/lab_strategy_container/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/lab_strategy_container/read',
                method: 'POST'
            },
            map: {
                link: '/admin/lab_strategy_container/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/lab_strategy_container/filter',
                method: 'POST'
            },
        }
    }
}

export default Lab_strategy_container;
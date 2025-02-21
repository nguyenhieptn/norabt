import model from "../model";

class Rank_history extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/rank_history/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/rank_history/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/rank_history/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/rank_history/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/rank_history/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/rank_history/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/rank_history/read',
                method: 'POST'
            },
            map: {
                link: '/admin/rank_history/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/rank_history/filter',
                method: 'POST'
            },
        }
    }
}

export default Rank_history;
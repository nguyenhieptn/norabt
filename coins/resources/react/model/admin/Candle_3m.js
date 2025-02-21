import model from "../model";

class Candle_3m extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/candle_3m/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/candle_3m/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/candle_3m/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/candle_3m/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/candle_3m/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/candle_3m/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/candle_3m/read',
                method: 'POST'
            },
            map: {
                link: '/admin/candle_3m/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/candle_3m/filter',
                method: 'POST'
            },
        }
    }
}

export default Candle_3m;
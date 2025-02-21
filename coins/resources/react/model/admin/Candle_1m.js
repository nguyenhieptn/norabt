import model from "../model";

class Candle_1m extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/candle_1m/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/candle_1m/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/candle_1m/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/candle_1m/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/candle_1m/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/candle_1m/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/candle_1m/read',
                method: 'POST'
            },
            map: {
                link: '/admin/candle_1m/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/candle_1m/filter',
                method: 'POST'
            },
        }
    }
}

export default Candle_1m;
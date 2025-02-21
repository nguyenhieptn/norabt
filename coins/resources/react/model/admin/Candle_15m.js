import model from "../model";

class Candle_15m extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/candle_15m/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/candle_15m/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/candle_15m/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/candle_15m/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/candle_15m/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/candle_15m/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/candle_15m/read',
                method: 'POST'
            },
            map: {
                link: '/admin/candle_15m/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/candle_15m/filter',
                method: 'POST'
            },
        }
    }
}

export default Candle_15m;
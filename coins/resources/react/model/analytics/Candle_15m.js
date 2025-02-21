import model from "../model";

class Candle_15m extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/analytics/candle_15m/add',
                method: 'POST'
            },
            edit: {
                link: '/analytics/candle_15m/edit',
                method: 'POST'
            },
            delete: {
                link: '/analytics/candle_15m/drop',
                method: 'POST'
            },
            adds: {
                link: '/analytics/candle_15m/adds',
                method: 'POST'
            },
            edits: {
                link: '/analytics/candle_15m/edits',
                method: 'POST'
            },
            deletes: {
                link: '/analytics/candle_15m/drops',
                method: 'POST'
            },
            read: {
                link: '/analytics/candle_15m/read',
                method: 'POST'
            },
            map: {
                link: '/analytics/candle_15m/mapping',
                method: 'POST'
            },
            filter: {
                link: '/analytics/candle_15m/filter',
                method: 'POST'
            },
        }
    }
}

export default Candle_15m;
import model from "../model";

class Candle_1m extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/analytics/candle_1m/add',
                method: 'POST'
            },
            edit: {
                link: '/analytics/candle_1m/edit',
                method: 'POST'
            },
            delete: {
                link: '/analytics/candle_1m/drop',
                method: 'POST'
            },
            adds: {
                link: '/analytics/candle_1m/adds',
                method: 'POST'
            },
            edits: {
                link: '/analytics/candle_1m/edits',
                method: 'POST'
            },
            deletes: {
                link: '/analytics/candle_1m/drops',
                method: 'POST'
            },
            read: {
                link: '/analytics/candle_1m/read',
                method: 'POST'
            },
            map: {
                link: '/analytics/candle_1m/mapping',
                method: 'POST'
            },
            filter: {
                link: '/analytics/candle_1m/filter',
                method: 'POST'
            },
        }
    }
}

export default Candle_1m;
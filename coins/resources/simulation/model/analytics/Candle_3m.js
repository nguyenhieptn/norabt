import model from "../model";

class Candle_3m extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/analytics/candle_3m/add',
                method: 'POST'
            },
            edit: {
                link: '/analytics/candle_3m/edit',
                method: 'POST'
            },
            delete: {
                link: '/analytics/candle_3m/drop',
                method: 'POST'
            },
            adds: {
                link: '/analytics/candle_3m/adds',
                method: 'POST'
            },
            edits: {
                link: '/analytics/candle_3m/edits',
                method: 'POST'
            },
            deletes: {
                link: '/analytics/candle_3m/drops',
                method: 'POST'
            },
            read: {
                link: '/analytics/candle_3m/read',
                method: 'POST'
            },
            map: {
                link: '/analytics/candle_3m/mapping',
                method: 'POST'
            },
            filter: {
                link: '/analytics/candle_3m/filter',
                method: 'POST'
            },
        }
    }
}

export default Candle_3m;
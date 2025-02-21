import model from "../model";

class Candle_1d extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/analytics/candle_1d/add',
                method: 'POST'
            },
            edit: {
                link: '/analytics/candle_1d/edit',
                method: 'POST'
            },
            delete: {
                link: '/analytics/candle_1d/drop',
                method: 'POST'
            },
            adds: {
                link: '/analytics/candle_1d/adds',
                method: 'POST'
            },
            edits: {
                link: '/analytics/candle_1d/edits',
                method: 'POST'
            },
            deletes: {
                link: '/analytics/candle_1d/drops',
                method: 'POST'
            },
            read: {
                link: '/analytics/candle_1d/read',
                method: 'POST'
            },
            get: {
                link: '/analytics/candle_1d/get',
                method: 'POST'
            },
            map: {
                link: '/analytics/candle_1d/mapping',
                method: 'POST'
            },
            filter: {
                link: '/analytics/candle_1d/filter',
                method: 'POST'
            },
        }
    }
}

export default Candle_1d;
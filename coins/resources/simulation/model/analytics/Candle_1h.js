import model from "../model";

class Candle_1h extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/analytics/candle_1h/add',
                method: 'POST'
            },
            edit: {
                link: '/analytics/candle_1h/edit',
                method: 'POST'
            },
            delete: {
                link: '/analytics/candle_1h/drop',
                method: 'POST'
            },
            adds: {
                link: '/analytics/candle_1h/adds',
                method: 'POST'
            },
            edits: {
                link: '/analytics/candle_1h/edits',
                method: 'POST'
            },
            deletes: {
                link: '/analytics/candle_1h/drops',
                method: 'POST'
            },
            read: {
                link: '/analytics/candle_1h/read',
                method: 'POST'
            },
            get: {
                link: '/analytics/candle_1h/get',
                method: 'POST'
            },
            map: {
                link: '/analytics/candle_1h/mapping',
                method: 'POST'
            },
            filter: {
                link: '/analytics/candle_1h/filter',
                method: 'POST'
            },
        }
    }
}

export default Candle_1h;
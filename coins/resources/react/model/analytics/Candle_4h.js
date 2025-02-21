import model from "../model";

class Candle_4h extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/analytics/candle_4h/add',
                method: 'POST'
            },
            edit: {
                link: '/analytics/candle_4h/edit',
                method: 'POST'
            },
            delete: {
                link: '/analytics/candle_4h/drop',
                method: 'POST'
            },
            adds: {
                link: '/analytics/candle_4h/adds',
                method: 'POST'
            },
            edits: {
                link: '/analytics/candle_4h/edits',
                method: 'POST'
            },
            deletes: {
                link: '/analytics/candle_4h/drops',
                method: 'POST'
            },
            read: {
                link: '/analytics/candle_4h/read',
                method: 'POST'
            },
            get: {
                link: '/analytics/candle_4h/get',
                method: 'POST'
            },
            map: {
                link: '/analytics/candle_4h/mapping',
                method: 'POST'
            },
            filter: {
                link: '/analytics/candle_4h/filter',
                method: 'POST'
            },
        }
    }
}

export default Candle_4h;
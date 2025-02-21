import model from "../model";

class Candle_1h extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/candle_1h/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/candle_1h/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/candle_1h/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/candle_1h/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/candle_1h/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/candle_1h/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/candle_1h/read',
                method: 'POST'
            },
            map: {
                link: '/admin/candle_1h/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/candle_1h/filter',
                method: 'POST'
            },
        }
    }
}

export default Candle_1h;
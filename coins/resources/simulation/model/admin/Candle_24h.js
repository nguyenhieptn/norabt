import model from "../model";

class Candle_24h extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/candle_24h/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/candle_24h/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/candle_24h/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/candle_24h/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/candle_24h/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/candle_24h/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/candle_24h/read',
                method: 'POST'
            },
            map: {
                link: '/admin/candle_24h/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/candle_24h/filter',
                method: 'POST'
            },
        }
    }
}

export default Candle_24h;
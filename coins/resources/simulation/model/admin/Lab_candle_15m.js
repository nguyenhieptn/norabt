import model from "../model";

class Lab_candle_15m extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/lab_candle_15m/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/lab_candle_15m/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/lab_candle_15m/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/lab_candle_15m/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/lab_candle_15m/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/lab_candle_15m/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/lab_candle_15m/read',
                method: 'POST'
            },
            map: {
                link: '/admin/lab_candle_15m/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/lab_candle_15m/filter',
                method: 'POST'
            },
        }
    }
}

export default Lab_candle_15m;
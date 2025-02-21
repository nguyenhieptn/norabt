import model from "../model";

class Lab_candle_3m extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/lab_candle_3m/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/lab_candle_3m/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/lab_candle_3m/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/lab_candle_3m/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/lab_candle_3m/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/lab_candle_3m/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/lab_candle_3m/read',
                method: 'POST'
            },
            map: {
                link: '/admin/lab_candle_3m/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/lab_candle_3m/filter',
                method: 'POST'
            },
        }
    }
}

export default Lab_candle_3m;
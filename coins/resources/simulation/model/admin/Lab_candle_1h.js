import model from "../model";

class Lab_candle_1h extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/lab_candle_1h/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/lab_candle_1h/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/lab_candle_1h/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/lab_candle_1h/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/lab_candle_1h/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/lab_candle_1h/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/lab_candle_1h/read',
                method: 'POST'
            },
            get: {
                link: '/admin/lab_candle_1h/get',
                method: 'POST'
            },
            map: {
                link: '/admin/lab_candle_1h/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/lab_candle_1h/filter',
                method: 'POST'
            },
        }
    }
}

export default Lab_candle_1h;
import model from "../model";

class Lab_candle_1w extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/lab_candle_1w/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/lab_candle_1w/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/lab_candle_1w/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/lab_candle_1w/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/lab_candle_1w/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/lab_candle_1w/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/lab_candle_1w/read',
                method: 'POST'
            },
            get: {
                link: '/admin/lab_candle_1w/get',
                method: 'POST'
            },
            map: {
                link: '/admin/lab_candle_1w/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/lab_candle_1w/filter',
                method: 'POST'
            },
        }
    }
}

export default Lab_candle_1w;
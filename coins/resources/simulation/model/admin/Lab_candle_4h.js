import model from "../../../react/model/model";

class Lab_candle_4h extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/lab_candle_4h/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/lab_candle_4h/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/lab_candle_4h/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/lab_candle_4h/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/lab_candle_4h/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/lab_candle_4h/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/lab_candle_4h/read',
                method: 'POST'
            },
            get: {
                link: '/admin/lab_candle_4h/get',
                method: 'POST'
            },
            map: {
                link: '/admin/lab_candle_4h/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/lab_candle_4h/filter',
                method: 'POST'
            },
        }
    }

    getAll(){
        if (App.getLabCandle4hAll) return App.getLabCandle4hAll;
        App.loading(true);
        App.getLabCandle4hAll = this.read({ 'lab_candle_4h_symbol': 'BTCUSDT' , 'lab_candle_4h_startpoint' : 1 }, { 'orderBy': 'lab_candle_4h_close_time', 'asc': true });
        return App.getLabCandle4hAll
    }
}

export default Lab_candle_4h;
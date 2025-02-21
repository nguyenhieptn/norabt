import model from "../model";

class Candle_1d extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/candle_1d/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/candle_1d/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/candle_1d/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/candle_1d/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/candle_1d/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/candle_1d/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/candle_1d/read',
                method: 'POST'
            },
            map: {
                link: '/admin/candle_1d/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/candle_1d/filter',
                method: 'POST'
            },
        }
    }

    getAll(){
        if (App.getCandle1dAll) return App.getCandle1dAll;
        App.loading(true);
        App.getCandle1dAll = this.read({ [CANDLE_1D_SYMBOL]: 'BTCUSDT' }, { 'orderBy': CANDLE_1D_CLOSE_TIME, 'asc': true });
        return App.getCandle1dAll
    }
}

export default Candle_1d;
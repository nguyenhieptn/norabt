import model from "../model";

class Candle_1w extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/candle_1w/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/candle_1w/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/candle_1w/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/candle_1w/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/candle_1w/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/candle_1w/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/candle_1w/read',
                method: 'POST'
            },
            map: {
                link: '/admin/candle_1w/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/candle_1w/filter',
                method: 'POST'
            },
        }

        
    }

    getAll(){
        if (App.getCandle1wAll) return App.getCandle1wAll;
        App.loading(true);
        App.getCandle1wAll = this.read({ [CANDLE_1W_SYMBOL]: 'BTCUSDT' }, { 'orderBy': CANDLE_1W_CLOSE_TIME, 'asc': true });
        return App.getCandle1wAll
    }
}

export default Candle_1w;
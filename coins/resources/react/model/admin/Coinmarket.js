import model from "../model";

class Coinmarket extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/coinmarket/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/coinmarket/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/coinmarket/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/coinmarket/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/coinmarket/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/coinmarket/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/coinmarket/read',
                method: 'POST'
            },
            map: {
                link: '/admin/coinmarket/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/coinmarket/filter',
                method: 'POST'
            },
        }


        
    }


    getRank(){
        if(!this.getRankResult){
            this.getRankResult = this.read([], false).then(dateData => {
                var indexData = {};
                if (dateData['result']) {
                    var volData = dateData['data'];
                    // volData = volData.sort((a, b) => Number(b[CANDLE_24H_VOLUME_USDT]) - Number(a[CANDLE_24H_VOLUME_USDT]));
                    for (let i in volData) {
                        // indexData[volData[i][COINMARKET_SYMBOL]] = volData[i][COINMARKET_RANK]
                        indexData[volData[i]['coinmarket_symbol']] = volData[i]['coinmarket_rank']
                    }
                }
                return indexData;
            })
        }   
        return this.getRankResult
    }
}

export default Coinmarket;
import model from "../model";

class Trades extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/trades/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/trades/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/trades/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/trades/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/trades/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/trades/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/trades/read',
                method: 'POST'
            },
            map: {
                link: '/admin/trades/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/trades/filter',
                method: 'POST'
            },
        }
    }


    getUserTrade(id){
        if(!this.getUserTradeResult){
            this.getUserTradeResult = this.read({[TRADE_ACCOUNT]: id}).then(userTrade => {
                if(userTrade['result']){
                    var userTradeIndex = {};
                    for(let i in userTrade['data']){
                        userTradeIndex[userTrade['data'][i][TRADE_SYMBOL]] = true;
                    }
                }
                return userTradeIndex;
            })
            
        }
        return this.getUserTradeResult;
		
    }
}

export default Trades;
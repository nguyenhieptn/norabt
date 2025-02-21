import model from "../model";

class Watchlist extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/watchlist/add',
                method: 'POST',
                onSuccess : ()=>{App.selectSymbol && App.selectSymbol.getSymbol()}
            },
            edit: {
                link: '/admin/watchlist/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/watchlist/drop',
                method: 'POST',
                onSuccess : ()=>{App.selectSymbol && App.selectSymbol.getSymbol()}
            },
            adds: {
                link: '/admin/watchlist/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/watchlist/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/watchlist/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/watchlist/read',
                method: 'POST'
            },
            map: {
                link: '/admin/watchlist/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/watchlist/filter',
                method: 'POST'
            },
        }

    }


    getWatchlist(){
        if(App.getWatchlistResult) return App.getWatchlistResult;
        App.loading(true);
        App.getWatchlistResult = this.read().then(res => {
            if(res){
                if(res['result']){
                    var suggest = {};
                    res['data'].map(item => suggest[item[WL_SYMBOL]] = item[WL_SYMBOL]);
                    return suggest;
                }
            }
        })
        setTimeout(()=>App.getWatchlistResult = null , 5000);
        return App.getWatchlistResult
    }



}

export default Watchlist;
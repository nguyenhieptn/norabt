import model from "../model";

class Watchlist extends model {
    constructor() {
        super();
        this.links = {
            add: {
                link: '/admin/watchlist/add',
                method: 'POST',
                onSuccess: () => { App.selectSymbol && App.selectSymbol.getSymbol() }
            },
            edit: {
                link: '/admin/watchlist/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/watchlist/drop',
                method: 'POST',
                onSuccess: () => { App.selectSymbol && App.selectSymbol.getSymbol() }
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


    getWatchlist() {
        if (App.getWatchlistResult) return App.getWatchlistResult;
        App.loading(true);
        App.getWatchlistResult = this.read().then(res => {
            if (res) {
                if (res['result']) {
                    var data = res['data'].sort((a,b)=>a[WL_SYMBOL]>b[WL_SYMBOL]?1:-1);
                    var suggest = {};
                    data.map(item => suggest[item[WL_SYMBOL]] = item[WL_SYMBOL]);
                    return suggest;
                }
            }
        })
        setTimeout(() => App.getWatchlistResult = null, 5000);
        return App.getWatchlistResult
    }
    
    file_public(path) {
        if (!path) return '';
        return path.replace(/(https?:\/\/[^\/]+)/, ' $1/api/uploader/uploader/public?file=$1');
    }

    getIcon() {
        if (App.getWatchlistIcon) return App.getWatchlistIcon;
        App.loading(true);
        App.getWatchlistIcon = this.read().then(res => {
     
            if (res) {
                if (res['result']) {
                    var suggest = {};
                    res['data'].map(item => suggest[item[WL_SYMBOL]] = this.file_public(item[WL_ICON]));
                    return suggest;
                }
            }
        })
        return App.getWatchlistIcon
    }

    readCalAvg(dataKeys, loading = true, special = {}) {

        if (loading) App.loading(true, 'Loading...');

        var variable = {
            data: { ...dataKeys, ...special }
        }

        return axios.request({
            url: '/admin/watchlist/readCalAvg',
            method: 'POST',
            ...variable
        })
            .then(response => {
                App.loading(false, 'Loading...');
                response = response['data'];
                return response;
            })

            .catch((error) => {
                console.log(error);
                App.loading(false, 'Loading...');
                error_handle(error)
                return false;
            })

    }



}

export default Watchlist;
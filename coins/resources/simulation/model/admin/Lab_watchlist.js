import model from "../model";

class Lab_watchlist extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/lab_watchlist/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/lab_watchlist/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/lab_watchlist/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/lab_watchlist/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/lab_watchlist/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/lab_watchlist/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/lab_watchlist/read',
                method: 'POST'
            },
            map: {
                link: '/admin/lab_watchlist/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/lab_watchlist/filter',
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
                    var data = res['data'].sort((a,b)=>a[LAB_WL_SYMBOL]>b[LAB_WL_SYMBOL]?1:-1);
                    var suggest = {};
                    data.map(item => suggest[item[LAB_WL_SYMBOL]] = item[LAB_WL_SYMBOL]);
                    return suggest;
                }
            }
        })
        setTimeout(()=>App.getWatchlistResult = null , 5000);
        return App.getWatchlistResult
    }

    updateRank(){
        App.loading(true, 'Loading...');
		return axios.request({
			url: '/admin/lab_watchlist/updateRank',
			method: 'POST',
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

    // file_public(path) {
    //     if (!path) return '';
    //     return path.replace(/(https?:\/\/[^\/]+)/, ' $1/api/uploader/uploader/public?file=$1');
    // }

    // getIcon() {
    //     if (App.getWatchlistIcon) return App.getWatchlistIcon;
    //     App.loading(true);
    //     App.getWatchlistIcon = this.read().then(res => {
    //         if (res) {
    //             if (res['result']) {
    //                 console.log(res);
    //                 var suggest = {};
    //                 res['data'].map(item => suggest[item[WL_SYMBOL]] = this.file_public(item[WL_ICON]));
    //                 return suggest;
    //             }
    //         }
    //     })
    //     return App.getWatchlistIcon
    // }
}

export default Lab_watchlist;
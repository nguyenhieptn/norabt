import model from "../../../react/model/model";

class Top_BTC extends model{
    constructor(){
        super();
        this.links = {
         
            read: {
                link: '/admin/top_btc/read',
                method: 'POST'
            },
            map: {
                link: '/admin/top_btc/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/top_btc/filter',
                method: 'POST'
            },
        }
    }
}

export default Top_BTC;
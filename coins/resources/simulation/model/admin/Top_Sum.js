import model from "../../../react/model/model";

class Top_Sum extends model{
    constructor(){
        super();
        this.links = {
         
            read: {
                link: '/admin/top_sum/read',
                method: 'POST'
            },
            map: {
                link: '/admin/top_sum/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/top_sum/filter',
                method: 'POST'
            },
            get: {
                link: '/admin/top_sum/get',
                method: 'POST'
            },
        }
    }
}

export default Top_Sum;
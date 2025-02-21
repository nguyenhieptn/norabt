import model from "../model";

class Price_1s extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/price_1s/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/price_1s/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/price_1s/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/price_1s/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/price_1s/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/price_1s/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/price_1s/read',
                method: 'POST'
            },
            get: {
                link: '/admin/price_1s/get',
                method: 'POST'
            },
            map: {
                link: '/admin/price_1s/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/price_1s/filter',
                method: 'POST'
            },
        }
    }
}

export default Price_1s;
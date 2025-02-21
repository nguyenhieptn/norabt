import model from "../model";

class Funding_fee extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/funding_fee/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/funding_fee/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/funding_fee/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/funding_fee/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/funding_fee/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/funding_fee/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/funding_fee/read',
                method: 'POST'
            },
            map: {
                link: '/admin/funding_fee/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/funding_fee/filter',
                method: 'POST'
            },
        }
    }
}

export default Funding_fee;
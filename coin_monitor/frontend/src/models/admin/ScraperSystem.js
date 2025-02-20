import model from "../model";

class ScraperSystem extends model{
    constructor(){
        super();
        this.links = {
            // add: {
            //     link: '/admin/account_summary/add',
            //     method: 'POST'
            // },
            // edit: {
            //     link: '/admin/account_summary/edit',
            //     method: 'POST'
            // },
            // delete: {
            //     link: '/admin/account_summary/drop',
            //     method: 'POST'
            // },
            // adds: {
            //     link: '/admin/account_summary/adds',
            //     method: 'POST'
            // },
            // edits: {
            //     link: '/admin/account_summary/edits',
            //     method: 'POST'
            // },
            // deletes: {
            //     link: '/admin/account_summary/drops',
            //     method: 'POST'
            // },
            read: {
                link: '/api/scraperSystem/read',
                method: 'POST'
            },
            // map: {
            //     link: '/admin/account_summary/mapping',
            //     method: 'POST'
            // },
            filter: {
                link: '/api/scraperSystem/filter',
                method: 'POST'
            },
        }
    }


}

export default ScraperSystem;
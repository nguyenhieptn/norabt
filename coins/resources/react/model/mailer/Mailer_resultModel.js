import model from "../model";

class Mailer_resultModel extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/mailer/mailer_result/add',
                method: 'POST'
            },
            edit: {
                link: '/mailer/mailer_result/edit',
                method: 'POST'
            },
            delete: {
                link: '/mailer/mailer_result/drop',
                method: 'POST'
            },
            adds: {
                link: '/mailer/mailer_result/adds',
                method: 'POST'
            },
            edits: {
                link: '/mailer/mailer_result/edits',
                method: 'POST'
            },
            deletes: {
                link: '/mailer/mailer_result/drops',
                method: 'POST'
            },
            read: {
                link: '/mailer/mailer_result/read',
                method: 'GET'
            },
            map: {
                link: '/mailer/mailer_result/mapping',
                method: 'POST'
            },
            filter: {
                link: '/mailer/mailer_result/filter',
                method: 'POST'
            },
        }
    }
}

export default Mailer_resultModel;
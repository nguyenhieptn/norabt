import model from "../model";

class Mailer_configModel extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/mailer/mailer_config/add',
                method: 'POST'
            },
            edit: {
                link: '/mailer/mailer_config/edit',
                method: 'POST'
            },
            delete: {
                link: '/mailer/mailer_config/drop',
                method: 'POST'
            },
            adds: {
                link: '/mailer/mailer_config/adds',
                method: 'POST'
            },
            edits: {
                link: '/mailer/mailer_config/edits',
                method: 'POST'
            },
            deletes: {
                link: '/mailer/mailer_config/drops',
                method: 'POST'
            },
            read: {
                link: '/mailer/mailer_config/read',
                method: 'GET'
            },
            map: {
                link: '/mailer/mailer_config/mapping',
                method: 'POST'
            },
            filter: {
                link: '/mailer/mailer_config/filter',
                method: 'POST'
            },
        }
    }
}

export default Mailer_configModel;
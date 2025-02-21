import model from "../model";

class AuthenModel extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/auth/authentication/add',
                method: 'POST'
            },
            edit: {
                link: '/auth/authentication/edit',
                method: 'POST'
            },
            delete: {
                link: '/auth/authentication/drop',
                method: 'POST'
            },
            adds: {
                link: '/auth/authentication/adds',
                method: 'POST'
            },
            edits: {
                link: '/auth/authentication/edits',
                method: 'POST'
            },
            deletes: {
                link: '/auth/authentication/drops',
                method: 'POST'
            },
            read: {
                link: '/auth/authentication/read',
                method: 'POST'
            },
            map: {
                link: '/auth/authentication/mapping',
                method: 'POST'
            },
            filter: {
                link: '/auth/authentication/filter',
                method: 'POST'
            },
        }
    }
}

export default AuthenModel;
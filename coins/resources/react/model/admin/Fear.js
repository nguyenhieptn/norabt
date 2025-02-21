import model from "../model";

class Fear extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/fear/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/fear/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/fear/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/fear/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/fear/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/fear/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/fear/read',
                method: 'POST'
            },
            get: {
                link: '/admin/fear/get',
                method: 'POST'
            },
            map: {
                link: '/admin/fear/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/fear/filter',
                method: 'POST'
            },
        }
    }
}

export default Fear;
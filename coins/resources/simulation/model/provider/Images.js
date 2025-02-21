import model from "../model";

class Images extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/provider/images/add',
                method: 'POST'
            },
            edit: {
                link: '/provider/images/edit',
                method: 'POST'
            },
            delete: {
                link: '/provider/images/drop',
                method: 'POST'
            },
            adds: {
                link: '/provider/images/adds',
                method: 'POST'
            },
            edits: {
                link: '/provider/images/edits',
                method: 'POST'
            },
            deletes: {
                link: '/provider/images/drops',
                method: 'POST'
            },
            read: {
                link: '/provider/images/read',
                method: 'POST'
            },
            map: {
                link: '/provider/images/mapping',
                method: 'POST'
            },
            filter: {
                link: '/provider/images/filter',
                method: 'POST'
            },
        }
    }
}

export default Images;
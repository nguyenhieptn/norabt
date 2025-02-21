import model from "../../../react/model/model";

class Lab_opt_result  extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/admin/lab_opt_result/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/lab_opt_result/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/lab_opt_result/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/lab_opt_result/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/lab_opt_result/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/lab_opt_result/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/lab_opt_result/read',
                method: 'POST'
            },
            map: {
                link: '/admin/lab_opt_result/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/lab_opt_result/filter',
                method: 'POST'
            },
        }
    }
}

export default Lab_opt_result ;
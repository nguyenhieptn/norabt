import model from "../model";

class DiskModel extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/uploader/uploader_disks/add',
                method: 'POST'
            },
            edit: {
                link: '/uploader/uploader_disks/edit',
                method: 'POST'
            },
            delete: {
                link: '/uploader/uploader_disks/drop',
                method: 'POST'
            },
            adds: {
                link: '/uploader/uploader_disks/adds',
                method: 'POST'
            },
            edits: {
                link: '/uploader/uploader_disks/edits',
                method: 'POST'
            },
            deletes: {
                link: '/uploader/uploader_disks/drops',
                method: 'POST'
            },
            read: {
                link: '/uploader/uploader_disks/read',
                method: 'POST'
            },
            map: {
                link: '/uploader/uploader_disks/mapping',
                method: 'POST'
            },
            filter: {
                link: '/uploader/uploader_disks/filter',
                method: 'POST'
            },
        }
    }
}

export default DiskModel;
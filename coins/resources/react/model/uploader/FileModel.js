import model from "../model";

class FileModel extends model{
    constructor(){
        super();
        this.links = {
            add: {
                link: '/uploader/uploader_files/add',
                method: 'POST'
            },
            edit: {
                link: '/uploader/uploader_files/edit',
                method: 'POST'
            },
            delete: {
                link: '/uploader/uploader_files/drop',
                method: 'POST'
            },
            adds: {
                link: '/uploader/uploader_files/adds',
                method: 'POST'
            },
            edits: {
                link: '/uploader/uploader_files/edits',
                method: 'POST'
            },
            deletes: {
                link: '/uploader/uploader_files/drops',
                method: 'POST'
            },
            read: {
                link: '/uploader/uploader_files/read',
                method: 'POST'
            },
            filter: {
                link: '/uploader/uploader_files/filter',
                method: 'POST'
            },
        }
    }
}

export default FileModel;
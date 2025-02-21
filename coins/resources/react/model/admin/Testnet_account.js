import model from "../model";

class Testnet_account extends model {
    constructor() {
        super();
        this.links = {
            add: {
                link: '/admin/testnet_account/add',
                method: 'POST'
            },
            edit: {
                link: '/admin/testnet_account/edit',
                method: 'POST'
            },
            delete: {
                link: '/admin/testnet_account/drop',
                method: 'POST'
            },
            adds: {
                link: '/admin/testnet_account/adds',
                method: 'POST'
            },
            edits: {
                link: '/admin/testnet_account/edits',
                method: 'POST'
            },
            deletes: {
                link: '/admin/testnet_account/drops',
                method: 'POST'
            },
            read: {
                link: '/admin/testnet_account/read',
                method: 'POST'
            },
            map: {
                link: '/admin/testnet_account/mapping',
                method: 'POST'
            },
            filter: {
                link: '/admin/testnet_account/filter',
                method: 'POST'
            },
        }
    }

    restartTrading(id) {
        App.loading(true);
        return axios.request({
            url: '/admin/testnet_account/restartTrading',
            method: 'POST',
            data: {
                id
            }
        })
            .then(response => {
                App.loading(false, 'Loading...');
                response = response['data'];
                return response;
            })

            .catch((error) => {
                console.log(error);
                App.loading(false, 'Loading...');
                error_handle(error)
                return false;
            })
    }

    stopTrading(id) {
        App.loading(true);
        return axios.request({
            url: '/admin/testnet_account/stopTrading',
            method: 'POST',
            data: {
                id
            }
        })
            .then(response => {
                App.loading(false, 'Loading...');
                response = response['data'];
                return response;
            })

            .catch((error) => {
                console.log(error);
                App.loading(false, 'Loading...');
                error_handle(error)
                return false;
            })
    }

    cleanData(id) {
        makeQuestion("Do you want to delete all RESULT and TRACKING BALANCE Data?").then(res => {
            if (res) {
                App.loading(true);
                return axios.request({
                    url: '/admin/testnet_account/cleanData',
                    method: 'POST',
                    data: {
                        id
                    }
                })
                    .then(response => {
                        App.loading(false, 'Loading...');
                        response = response['data'];
                        return response;
                    })

                    .catch((error) => {
                        console.log(error);
                        App.loading(false, 'Loading...');
                        error_handle(error)
                        return false;
                    })
            }
        })

    }



    cloneData(id) {
        return makeQuestion("Do you want to clone this account?").then(res => {
            if (res) {
                App.loading(true);
                return axios.request({
                    url: '/admin/testnet_account/clone',
                    method: 'POST',
                    data: {
                        id
                    }
                })
                    .then(response => {
                        App.loading(false, 'Loading...');
                        response = response['data'];
                        return response;
                    })

                    .catch((error) => {
                        console.log(error);
                        App.loading(false, 'Loading...');
                        error_handle(error)
                        return false;
                    })
            }
        })

    }

}

export default Testnet_account;
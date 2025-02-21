global.login = () => {
    window.location = `${APP_AUTHEN}/login?link=${encodeURIComponent(window.location.href)}`;
}

global.logout = () => {
    axios.request({
        url: '/auth/profile/logout',
        method: 'post',
    })
        .then(response => {
            window.location.href = "/login";
        })

        .catch((error) => {
            Swal('Error', error, 'error');
        })
}


global.isAdmin = () => {
    if (App.server.user[AUTHEN_GROUP] == AUTHEN_GROUP_ROOT) return true;
    if (App.server.user[AUTHEN_GROUP] == AUTHEN_GROUP_ADMIN) return true;

    return false
}


global.getUser = (cache = true) => {
    if (!global.getUserResult || !cache) {
        global.getUserResult = axios.request({
            url: '/auth/profile/read',
            method: 'post',
        })
            .then(response => {
                response = response['data'];
                if(response['result']){
                    if(App) App.user = response['data']
                    return response['data'];

                }else{
                    error_handle(response);
                }
                
            })

            .catch((error) => {
                error_handle(error);
            })
    }
    return global.getUserResult;

}
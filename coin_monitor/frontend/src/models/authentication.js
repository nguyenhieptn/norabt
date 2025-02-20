import Axios from "axios";

class Authentication {
    

    async getUser(){
        global.USER = null
        var user = await Axios.get("/api/authentication/getUser")
        user = user['data']
        if(user['result']){
            global.USER = user['data']
        }
        return global.USER
    }
}

export default Authentication
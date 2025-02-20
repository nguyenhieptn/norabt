import Axios from "axios";

class Future_spot_diff {
    constructor(){

    }

    read(data){
        return Axios.request({
			url: '/api/future_spot_diff/read',
			method: 'post',
			data: data
		}).then(
            res => {
                res = res['data'];
                if(res['result']){
                    return res['data']
                }
            }
        )
       
    }
}

export default Future_spot_diff
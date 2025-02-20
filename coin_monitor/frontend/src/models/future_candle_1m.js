import Axios from "axios";

class Future_candle_1m {
    constructor(){

    }

    read(data){
        return Axios.request({
			url: '/api/future_candle_1m/read',
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

export default Future_candle_1m
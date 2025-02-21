import model from "../model";

class Ctrl extends model{
    constructor(){
        super();
    }

    get(key, df = null){
        App.loading(true);
        return axios.request({
			url: '/control/control/read',
			method: 'POST',
			data: {
                keys: [key]
            }
		})
			.then(response => {
				App.loading(false, 'Loading...');
				response = response['data'];
				if(response['result']){
                    if(response['data'][key] === null) return df;
                    return response['data'][key];
                }else{
                    error_handle(response);
                    return df;
                }
			})

			.catch((error) => {
				console.log(error);
				App.loading(false, 'Loading...');
				error_handle(error)
				return df;
			})
    }

    set(data){
        App.loading(true);
        return axios.request({
			url: '/control/control/update',
			method: 'POST',
            data: data
			
		})
			.then(response => {
				App.loading(false, 'Loading...');
				response = response['data'];
                if(response['result']){
                    return response;
                }else{
                    error_handle(response);
                    return response;
                }
				
			})

			.catch((error) => {
				console.log(error);
				App.loading(false, 'Loading...');
				error_handle(error)
				return false;
			})
    }

}

export default Ctrl;
import model from "../model";

class Finance extends model{
    constructor(){
        super();
        this.links = {
         
            read: {
                link: '/admin/finance/read',
                method: 'POST'
            },

            get: {
                link: '/admin/finance/get',
                method: 'POST'
            },
           
         
        }
    }


    getStock() {
		
		App.loading(true);
		return axios.request({
			url: '/admin/finance/getStock',
			method: 'POST',
		}) 

			.then(response => {
				App.loading(false);
				response = response['data'];
				return response;
			})

			.catch((error) => {
				console.log(error);
				App.loading(false);
				error_handle(error)
				return false;
			})

	}

   

}

export default Finance;
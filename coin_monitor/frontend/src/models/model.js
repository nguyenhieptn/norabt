import axios from "axios";
class model {

	constructor() {
		this.links = {}
	}
	filter(filterData, loading = true, special = {}) {
		if (!this.links.filter){
			console.log('No filter link');
			return Promise.resolve(false)
			
		}
		// if (loading) App.loading(true, 'Loading...');
		

		return axios.request({
			url: this.links.filter.link,
			method: this.links.filter.method,
			data: {...filterData, ...special}
		})

			.then(response => {
				// if (loading) App.loading(false, 'Loading...');
				response = response['data'];
				return response;
			})

			.catch((error) => {
				console.log(error);
				// App.loading(false, 'Loading...');
				// error_handle(error)
				return false;
			})


	}

	read(dataKeys, loading = true, special = {}) {
		if (!this.links.read){
			console.log('No read link');
			return Promise.resolve(false)
			
		}
		// if (loading) App.loading(true, 'Loading...');
		if(this.links.read.method == 'GET'){
			var variable={
				params: {...dataKeys, ...special}
			}
		}else{
			var variable={
				data: {...dataKeys, ...special}
			}
		}
		return axios.request({
			url: this.links.read.link,
			method: this.links.read.method,
			...variable
		})
			.then(response => {
				// App.loading(false, 'Loading...');
				response = response['data'];
				return response;
			})

			.catch((error) => {
				console.log(error);
				// App.loading(false, 'Loading...');
				// error_handle(error)
				return false;
			})
	}


}

export default model;
import model from "../model";

class Lab_track_balance_gen extends model{
    updateData(data){
        App.loading(true, 'Loading...');
		return axios.request({
			url: '/admin/lab_track_balance_gen/updateData',
			method: 'POST',
			data: {...data}
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

	test(data , len , totalLen){
        App.loading(true, `Loading...`);
		return axios.request({
			url: '/admin/lab_track_balance_gen/test',
			method: 'POST',
			data: {...data},
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

	getExistId(data){
        App.loading(true, 'Loading...');
		return axios.request({
			url: '/admin/lab_track_balance_gen/getExistId',
			method: 'POST',
			data: {...data}
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

	check(data){
        App.loading(true, 'Loading...');
		return axios.request({
			url: '/admin/lab_track_balance_gen/check',
			method: 'POST',
			data: {...data}
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

	read(data){
        App.loading(true, 'Loading...');
		return axios.request({
			url: '/admin/lab_track_balance_gen/read',
			method: 'POST',
			data: {...data}
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
}

export default Lab_track_balance_gen;
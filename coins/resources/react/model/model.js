class model {

	constructor() {
		this.links = {}
	}

	add(rowData, loading = true, special = {}) {
		if (!isset(this.links.add)){
			console.log('No add link');
			return Promise.resolve(false)
			
		}
		if (loading) App.loading(loading, 'Adding...');
		return axios.request({
			url: this.links.add.link,
			method: this.links.add.method,
			data: {data: rowData, ...special}
		}) 

			.then(response => {
				App.loading(false, 'Adding...');
				response = response['data'];
				if(this.links.add.onSuccess) this.links.add.onSuccess(response);
				return response;
			})

			.catch((error) => {
				console.log(error);
				App.loading(false, 'Adding...');
				error_handle(error)
				return false;
			})

	}


	adds(rowDatas, loading = true, special = {}) {
		if (!isset(this.links.adds)){
			console.log('No adds link');
			return Promise.resolve(false)
			
		}
		if (loading) App.loading(loading, 'Adding...');
		return axios.request({
			url: this.links.adds.link,
			method: this.links.adds.method,
			data: {
				data: rowDatas,
				...special
			}
		})

			.then(response => {
				App.loading(false, 'Adding...');
				response = response['data'];
				if(this.links.adds.onSuccess) this.links.adds.onSuccess(response);
				return response;
			})

			.catch((error) => {
				console.log(error);
				App.loading(false, 'Adding...');
				error_handle(error)
				return false;
			})

	}

	/**
	 * 
	 * @param {object} editKey
	 * @param {object} editData 
	 * @param {boolean} loading 
	 */
	edit(editKey, editData, loading = true, special = {}) {
		
		if (!isset(this.links.edit)){
			console.log('No edit link');
			return Promise.resolve(false)
			
		}
		if (loading) App.loading(true, 'Editting...');
		return axios.request({
			url: this.links.edit.link,
			method: this.links.edit.method,
			data: {
				data_key: editKey,
				data_editor: editData,
				...special
			}
		})

			.then(response => {
				App.loading(false, 'Editting...');
				response = response['data'];
				if(this.links.edit.onSuccess) this.links.edit.onSuccess(response);
				return response;
			})

			.catch((error) => {
				App.loading(false, 'Editting...');
				error_handle(error)
				return false;
			})

	}

	/**
	 * 
	 * @param {array} editKeys 
	 * @param {object} editData 
	 * @param {boolean} loading 
	 */
	edits(editKeys, editData, loading = true, special = {}) {
		if (!isset(this.links.edit)){
			console.log('No edit link');
			return Promise.resolve(false)
			
		}
		if (loading) App.loading(true, 'Editting...');
		return axios.request({
			url: this.links.edits.link,
			method: this.links.edits.method,
			data: {
				data_key: editKeys,
				data_editor: editData,
				...special
			}
		})

			.then(response => {
				App.loading(false, 'Editting...');
				response = response['data'];
				if(this.links.edits.onSuccess) this.links.edits.onSuccess(response);
				return response;
			})

			.catch((error) => {
				App.loading(false, 'Editting...');
				error_handle(error)
				return false;
			})

	}

	//=========================================================

	delete(delKey, alert = true, special = {}) {
		if (!isset(this.links.delete)){
			console.log('No delete link');
			return Promise.resolve(false)
			
		}

		if (alert) {
			return this.deleteAlert().then(result => {
				if (result) {
					return this.delQuery(delKey, true)
				} else {
					return Promise.reject();
				}
			})
		}
		else {
			return this.delQuery(delKey, false, special)
		}

	}

	deletes(delKeys, alert = true, special = {}) {

		if (!isset(this.links.deletes)){
			console.log('No deletes link');
			return Promise.resolve(false)
			
		}

		if (alert) {
			return this.deleteAlert().then(result => {
				if (result) {
					return this.delsQuery(delKeys, true, special)
				} else {
					return Promise.reject();
				}
			})
		}
		else {
			return this.delsQuery(delKeys, false, special)
		}

	}

	deleteAlert() {
		return Swal({
			title: lang('Do you want to delete?'),
			text: lang("Can not recovery data after deleted"),
			type: 'warning',
			showCancelButton: true,
			confirmButtonColor: '#3085d6',
			cancelButtonColor: '#d33',
			confirmButtonText: lang('Yes')
		}).then((result) => {
			return result.value;
		})
	}

	delQuery(delKey, loading = true, special = {}) {
		if (loading) App.loading(true, 'Deleting...');

		return axios.request({
			url: this.links.delete.link,
			method: this.links.delete.method,
			data: {data: delKey, ...special}
		})

			.then(response => {
				App.loading(false);
				response = response['data'];
				if(this.links.delete.onSuccess) this.links.delete.onSuccess(response);
				return response;
			})
			.catch((error) => {
				App.loading(false, 'Deleting...');
				error_handle(error)
				return false;
			})
	}

	delsQuery(delKeys, loading = true, special = {}) {
		
		if (loading) App.loading(true, 'Deleting...');

		return axios.request({
			url: this.links.deletes.link,
			method: this.links.deletes.method,
			data: {data: delKeys, ...special}
		})

			.then(response => {
				App.loading(false);
				response = response['data'];
				if(this.links.deletes.onSuccess) this.links.deletes.onSuccess(response);
				return response;
			})
			.catch((error) => {
				App.loading(false, 'Deleting...');
				error_handle(error)
				return false;
			})
	}

	//================================

	read(dataKeys, loading = true, special = {}) {
		if (!isset(this.links.read)){
			console.log('No read link');
			return Promise.resolve(false)
			
		}
		if (loading) App.loading(true, 'Loading...');
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


	/**
	 * 
	 * @param {} data [ OR:[AND, AND], OR:[AND, AND] ] 
	 * example [ [[id, '=', 1]], [[id, '=', 2]] ] get data with id = 1 or id = 2
	 * example [[ [time, '>', 1654345434], [time, '<' , 1664345434] ]] get data with time in range {1654345434, 1664345434}
	 * @param {*} options 
	 * example options = {limit: 10, skip: 10, orderBy:[time, 'DESC']}
	 * @param {*} loading True/false
	 * @param {*} special {key: value}
	 * @returns 
	 */

	get(data, options={}, loading = true, special = {}) {
		if (!isset(this.links.get)){
			console.log('No read link');
			return Promise.resolve(false)
			
		}
		if (loading) App.loading(true, 'Loading...');
		if(this.links.get.method == 'GET'){
			console.log('Not support GET')
			return Promise.resolve(false)
		}else{
			var variable={
				data: {data: data, ...options, ...special}
			}
		}
		return axios.request({
			url: this.links.get.link,
			method: this.links.get.method,
			...variable
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


	/**
	 * @param {*} filterData // {
	 *  PAGE_ACTIVE
		PAGE_QUANTITY
		PAGE_TOTAL
		FLAG_FILTER_CHANGE
		FLAG_FILTER_LOGIC
		DATA_SORT
		DATA_FILTER : [{columnNames: logic: and, data:{"<":"abc", ">":"xyz"}}]
	 * }
	 */

	filter(filterData, loading = true, special = {}) {
		if (!isset(this.links.filter)){
			console.log('No filter link');
			return Promise.resolve(false)
			
		}
		if (loading) App.loading(true, 'Loading...');
		

		return axios.request({
			url: this.links.filter.link,
			method: this.links.filter.method,
			data: {...filterData, ...special}
		})

			.then(response => {
				if (loading) App.loading(false, 'Loading...');
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


	sort(src_id, dest_id, loading = true, special = {}) {
		if (!isset(this.links.sort)){
			console.log('No sort link');
			return Promise.resolve(false)
			
		}
		if (loading) App.loading(true, 'Loading...');

		return axios.request({
			url: this.links.sort.link,
			method: this.links.sort.method,
			data: { src_id, dest_id, ...special}
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
			})
	}


	map(loading = true) {

		if (!isset(this.links.map)){
			console.log('No map link');
			return Promise.resolve(false)
			
		}
		if (loading) App.loading(true, 'Loading...');

		return axios.request({
			url: this.links.map.link,
			method: this.links.map.method,
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
			})
	}


}

export default model;
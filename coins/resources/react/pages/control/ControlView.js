
import React, { Component } from 'react'


class Control extends Component {

	constructor(props) {
		super(props);

		this.state = {
			content: ''
		}

		this.struct = {
			'control_app_name': {
				[INPUT_NAME]: lang('App Name'),
				[INPUT_TYPE]: 'text',
			},
			'control_title': {
				[INPUT_NAME]: lang('Title'),
				[INPUT_TYPE]: 'text',
			},
			'control_app_icon': {
				[INPUT_NAME]: lang('App Icon'),
				[INPUT_TYPE]: 'image',
				[INPUT_EXTEND]: {
					'fileManager' : () => this.fileManager
				}
			},
			
		}


	}



	render() {
		return (<>
			<div className='box_shadow box_padding'>
			</div>
		</>
		);
	}

	componentDidMount() {
		this.loadData()
	}

	loadData() {
		App.loading(true, 'Loading...');
		return axios.request({
			url: '/control/control/read',
			method: 'post',
			data: {
				keys: ['control_logo', 'control_app_icon', 'control_title', 'control_app_name']
			}
		})

			.then(response => {
				App.loading(false, 'Adding...');
				response = response['data'];
				if (response['result']) {
					this.form.setValue(response['data'])
					if(isset(response['data']['control_logo'])){
						if (this.editor) this.editor.editor.setData(response['data']['control_logo']);
						this.setState({content: response['data']['control_logo']})
					}
				} else {
					return Promise.reject(response);
				}
			})

			.catch((error)=> {
				console.log(error);
				App.loading(false, 'Adding...');
				error_handle(error)
			})
	}

	updateData(data) {
		App.loading(true, 'Loading...');
		return axios.request({
			url: '/control/control/update',
			method: 'post',
			data: data,
		})

			.then(response => {
				App.loading(false, 'Adding...');
				response = response['data'];
				if (response['result']) {
					Swal(true, 'Success', 'success');
				} else {
					error_handle(response);
				}
			})

			.catch((error)=> {
				console.log(error);
				App.loading(false, 'Adding...');
				error_handle(error)
			})
	}



}

export default Control
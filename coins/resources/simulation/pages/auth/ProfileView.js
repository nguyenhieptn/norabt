import React, { Component } from 'react'

import Input from '../../components/input/Input';
import FormInput from '../../components/input/FormInput';
import FilesManager from '../../components/input/FilesManager';

class ProfileView extends Component {

	constructor(props) {
		super(props);

		this.inputStruct = {
			[AUTHEN_USERNAME]: {
				[INPUT_NAME]: lang(AUTHEN_USERNAME),
				[INPUT_TYPE]: 'text',
				[INPUT_NULL]: false,
			},
			[AUTHEN_EMAIL]: {
				[INPUT_NAME]: lang(AUTHEN_EMAIL),
				[INPUT_TYPE]: 'email',
				[INPUT_NULL]: false,
			},
			[AUTHEN_PHONE]: {
				[INPUT_NAME]: lang(AUTHEN_PHONE),
				[INPUT_TYPE]: 'phone',
				[INPUT_NULL]: true,
			},
		}

		this.inputPass = {
			old_pass: {
				[INPUT_NAME]: lang('Old Pass'),
				[INPUT_TYPE]: 'password',
				[INPUT_NULL]: false,
				[INPUT_DECORATOR_IN]: function (data) { return ""; },
				[INPUT_DECORATOR_OUT]: function (data) { if (data != "") return btoa(data); else return "" }
			},
			new_pass: {
				[INPUT_NAME]: lang('New Pass'),
				[INPUT_TYPE]: 'password',
				[INPUT_NULL]: false,
				[INPUT_DECORATOR_IN]: function (data) { return ""; },
				[INPUT_DECORATOR_OUT]: function (data) { if (data != "") return btoa(data); else return "" }
			},
			rep_pass: {
				[INPUT_NAME]: lang('Retype Pass'),
				[INPUT_TYPE]: 'password',
				[INPUT_NULL]: false,
				[INPUT_DECORATOR_IN]: (data)=>{ return ""; },
				[INPUT_DECORATOR_OUT]: (data)=>{ if (data != "") return btoa(data); else return "" }
			},
		}

	}


	render() {

		return (<>
			<div className='row box_shadow'>
				{/* <div className='col-md-4'>

					<div>
						<h4 className='title'>{lang(AUTHEN_IMG)}</h4>
						<hr />
						<Input ref={input => this.imgInput = input} struct={{
							[INPUT_NAME]: AUTHEN_IMG,
							[INPUT_TYPE]: 'image',
							[INPUT_NULL]: true,
							[INPUT_EXTEND]: {
								fileManager: ()=>this.fileManager
							}
						}}>
			
						</Input>

					</div>

				</div> */}

				<div className='col-md-12'>

					<div>
						<h4 className='title'>{lang('Informations')}</h4>
						<hr />
						<FormInput struct={this.inputStruct} ref={form => this.form = form}></FormInput>
						<br />
						<div className='box_flex' style={{ justifyContent: 'flex-end' }}>
							<div onClick={() => { this.updateUser() }} className='button btn btn-primary'>{lang('Save')}</div>
						</div>
					</div>
					<br />

				</div>


			</div>
			<br/>
			<div className='row box_shadow box_padding'>
				<div style={{width:'100%'}}>
					<h4 className='title'>{lang(AUTHEN_PASS)}</h4>
					<hr />
					<FormInput struct={this.inputPass} ref={form => this.formPass = form}></FormInput>
					<br />
					<div className='box_flex' style={{ justifyContent: 'flex-end' }}>
						<div onClick={() => { this.changePass() }} className='button btn btn-primary'>{lang('Change')}</div>
					</div>
				</div>
			</div>


			<FilesManager ref={c=>this.fileManager=c} column={AUTHEN_IMG} links={{
				get: {method: 'GET', link: '/auth/profile/uploader_get'},
				read: {method: 'GET', link: '/auth/profile/uploader_read'},
				upload: {method: 'POST', link: '/auth/profile/uploader_upload'},
				delete: {method: 'POST', link: '/auth/profile/uploader_delete'},
			}}></FilesManager>

			
		</>

		);
	}

	componentDidMount() {
		this.loadUser();
	}

	loadUser() {
		return axios.request({
			url: '/auth/profile/read',
			method: 'post',
		})

			.then(response => {
				App.loading(false, 'Adding...');
				response = response['data'];
				if (response['result']) {
					var data = response['data'];
					// this.imgInput.setValue(data[AUTHEN_IMG]);
					this.form.setValue(data);
					this.formData = data;

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

	async updateUser() {

		var img = this.imgInput.getValue();
		if (img === null) return;
		var formData = this.form.getValue();
		if (formData === null) return;
		formData[AUTHEN_IMG] = img;

		for(let i in formData){
			if(formData[i] == this.formData[i]){
				delete(formData[i])
			}
		}

		return axios.request({
			url: '/auth/profile/update',
			method: 'post',
			data: { data: formData },
		})

			.then(response => {
				App.loading(false, 'Adding...');
				response = response['data'];
				if (response['result']) {
					location.reload();
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

	changePass() {

		var formPass = this.formPass.getValue();
		if (formPass === null) return;
		var formData = this.form.getValue();
		if (formData === null) return;

		if (formPass.rep_pass != formPass.new_pass) {
			Swal('Error', 'Password not match', 'error');
			return;
		}

		return axios.request({
			url: '/auth/profile/update_pass',
			method: 'post',
			data: {
				old_pass: formPass.old_pass,
				new_pass: formPass.new_pass
			},
		})

			.then(response => {
				App.loading(false, 'Adding...');
				response = response['data'];
				if (response['result']) {
					Swal('Success', '', 'success');
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

}

export default ProfileView;

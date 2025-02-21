import React, { Component } from 'react'
import ContextMenu from '../common/ContextMenu';
import Style from '../common/Style'

class FileManager extends Component {

	constructor(props) {
		super(props);
		this.id = makeId();

		this.state = {
			files: {},
			folders: {},
			folderId: 0,
			selects: {},
			pwd: [],
			preview: null,
			editing: null,
			editing_value: '',
			key: get(this.props.use, 'objectCode')
		}
		this.selects = {};
		this.page = 1;
		this.number = 20;
	}

	modal(cmd = 'show') {
		if (cmd == 'hide') {
			$("#file_mng_modal" + this.id).modal('hide');
		} else {
			$("#file_mng_modal" + this.id).modal();
			this.setState({ selects: {} });
			this.getChild();
		}
	}


	onClickHandle() {
		if (this.onSelect) {
			this.onSelect(this.state.selects);
		}
	}

	setOnSelect(callback) {
		this.onSelect = callback;
	}

	setSelected(selected) {
		var valid = [];
		for (let i in selected) {
			if (isset(selected[i]) && selected[i] != '') {
				valid.push(selected[i])
			}
		}
		this.setState({ selects: valid })
	}

	setKey(key) {
		this.setState({ key: key });
	}

	getFolders() {
		App.loading(true)
		axios.request({
			url: App.baseApi(`/api/file/getMyChildFolder/${this.state.folderId}/1`),
			method: 'get',
		})

			.then(response => {
				App.loading(false)
				response = response['data'];
				var folders = {}
				response.map(item => {
					folders[item[this.state.key]] = item;
				})
				this.setState({ folders });
			})

			.catch((error) => {
				App.loading(false)
				console.log(error);
				error_handle(error);
			})
	}


	getFiles() {
		App.loading(true)
		axios.request({
			url: App.baseApi(`/api/file/getMyChildFile/${this.state.folderId}/1`),
			method: 'get',
		})

			.then(response => {
				App.loading(false)
				response = response['data'];
				var files = {}
				response.map(item => {
					files[item[this.state.key]] = item;
				})
				this.setState({ files });
			})

			.catch((error) => {
				App.loading(false)
				console.log(error);
				error_handle(error);
			})
	}

	getChild() {
		this.getFiles();
		this.getFolders();
	}

	basename(path) {
		if (!path) return '';
		return path.replace(/.*\//, '');
	}

	showSize(size) {
		if (size < 1000000) return Math.round(size / 1000) + 'KB';
		return Math.round(size / 10000000) / 10 + 'MB';
	}

	previewFile(id) {
		App.loading(true)
		return axios.request({
			url: App.baseApi(`/api/file/download?id=${id}`),
			method: 'get',
			responseType: 'blob'
		})

			.then(response => {
				//   var mime = response.headers['content-type'];
				//   response = response['data'];
				App.loading(false)
				var blob = response['data'];
				const blobURL = window.URL.createObjectURL(blob);
				var preview = this.state.preview;
				preview['link'] = blobURL;
				this.setState({ preview })
			})

			.catch((error) => {
				App.loading(false)
				console.log(error);
				error_handle(error);
			})
	}


	editFolder() {

		App.loading(true);
		return axios.request({
			url: App.baseApi(`/api/file/rename_folder`),
			method: 'put',
			data: {
				'id': this.state.editing,
				'updateName': this.state.editing_value,
			}
		})

			.then(response => {
				response = response['data'];
				App.loading(false);
				this.setState({ editing: '', editing_value: '' }, () => { this.getFolders() })

			})

			.catch((error) => {
				App.loading(false);
				error_handle(error);
			})
	}

	editFile() {

		App.loading(true);
		return axios.request({
			url: App.baseApi(`/api/file/rename_file`),
			method: 'put',
			data: {
				'id': this.state.editing,
				'updateName': this.state.editing_value,
			}
		})

			.then(response => {
				response = response['data'];
				App.loading(false);
				this.setState({ editing: '', editing_value: '' }, () => { this.getFiles() })

			})

			.catch((error) => {
				App.loading(false);
				error_handle(error);
			})
	}



	addNewFolder() {

		var newFolder = 'New Folder';
		var index = 1;
		while (this.state.folders.find(item => {
			var folderName = this.basename(item['name'])
			return folderName == newFolder;
		}) !== undefined) {
			newFolder = 'New Folder ' + index;
			index++;
		}

		App.loading(true);
		return axios.request({
			url: App.baseApi('/api/file/create_folder'),
			method: 'post',
			data: {
				name: newFolder,
				parentId: this.state.folderId,
				"mpermission": {
					"privatePermission": {
						"applications": {},
						"users": {}
					},
					"publicPermission": 1
				}
			}
		})

			.then(response => {
				response = response['data'];
				App.loading(false);
				this.setState({ editing: response['id'], editing_value: newFolder })
				this.getFolders();
			})

			.catch((error) => {
				App.loading(false);
				error_handle(error);
			})
	}


	delFolder(folderId) {

		App.loading(true);
		return axios.request({
			url: App.baseApi(`/api/file/deleteFolder/${folderId}`),
			method: 'delete',
		})

			.then(response => {
				response = response['data'];
				App.loading(false);
				this.getFolders();
			})

			.catch((error) => {
				App.loading(false);
				error_handle(error);
			})
	}

	delFile(fileId) {

		App.loading(true);
		return axios.request({
			url: App.baseApi(`/api/file/deleteFile/${fileId}`),
			method: 'delete',
		})

			.then(response => {
				response = response['data'];
				App.loading(false);
				this.getFiles();
			})

			.catch((error) => {
				App.loading(false);
				error_handle(error);
			})
	}

	delFile(fileId) {

		App.loading(true);
		return axios.request({
			url: App.baseApi(`/api/file/deleteFile/${fileId}`),
			method: 'delete',
		})

			.then(response => {
				response = response['data'];
				App.loading(false);
				this.setSelected([]);
				this.getFiles();
			})

			.catch((error) => {
				App.loading(false);
				error_handle(error);
			})
	}

	// uploadData(files){

	// 	let formData = new FormData();
	// 	formData.append('files', files);
	// 	App.loading(true);
	// 	return axios.request ({
	// 		url: App.baseApi(`/api/file/upload_files/${this.state.folderId}`),
	// 		method: 'post',
	// 		headers: {
	// 			'content-type': 'multipart/form-data',
	// 			},
	// 		data:formData,
	// 		onUploadProgress: event => {
	// 			App.Loading.update('Uploading...', Math.floor(event.loaded*100/event.total))
	// 		}
	// 		})

	// 	  .then(response => {
	// 		  response = response['data'];
	// 		  App.loading(false);
	// 		  this.getFiles();
	// 		  return response;

	// 	  })

	// 	  .catch((error)=>{
	// 		App.loading(false);
	// 		error_handle(error);
	// 	  })
	// }

	uploadData(files) {

		let formData = new FormData();
		for (let i = 0; i < files.length; i++) {
			formData.append(`files`, files[i]);
		}
		App.loading(true);
		return axios.request({
			url: App.baseApi(`/api/file/upload_files/${this.state.folderId}`),
			method: 'post',
			headers: {
				'content-type': 'multipart/form-data',
			},
			data: formData,
			onUploadProgress: event => {
				App.Loading.update('Uploading...', Math.floor(event.loaded * 100 / event.total))
			}
		})

			.then(response => {
				response = response['data'];
				App.loading(false);
				var selected = response.map((item) => item['objectCode'])
				this.setSelected(selected);

				this.getFiles();
				return response;

			})

			.catch((error) => {
				App.loading(false);
				error_handle(error);
			})
	}


	render() {

		return (
			<>
				<div className="modal fade" id={"file_mng_modal" + this.id}>
					<div className="modal-dialog modal-lg modal-dialog-centered">
						<div className="modal-content">

							<div className="modal-header">
								<h4 className="modal-title">{lang("Quản lý Files")}</h4>
								<button type="button" className="close" data-dismiss="modal">&times;</button>
							</div>

							<div className="modal-body" style={{ textAlign: 'initial' }}>

								<div>
									<nav aria-label="breadcrumb" >
										<ol className="breadcrumb" style={{ margin: 0, padding: '5px 10px' }}>
											<li className="breadcrumb-item"><i className="fa fa-folder-open" style={{ fontSize: 14, color: '#ffc107' }}></i></li>
											{this.state.pwd.map(item => {
												return <li key={item['id']} className="breadcrumb-item">{this.basename(item['name'])}</li>
											})}
										</ol>
									</nav>
								</div>


								<div className='row' style={{ padding: 0 }}>
									<div className='col-md-8' >
										<div className='file_button box_flex'>

											<div className='button' style={{ textAlign: 'center' }}>
												<i title={lang('Tạo mới Thư Mục')} className="fa fa-plus-square button" aria-hidden="true" style={{ fontSize: 14, marginLeft: 0 }} onClick={e => {
													this.addNewFolder();
												}}></i> &nbsp; {lang('Tạo Thư Mục')}
											</div>

											{this.state.pwd.length == 0 && <span style={{ color: 'red' }}>{lang('Tạo mới hoặc chọn một thư mục để upload file')}</span>}
											{this.state.pwd.length > 0 && <div className='box_flex' style={{ flexGrow: 1 }}>

												<label htmlFor={'input' + this.id} style={{ margin: 0 }}>

													<div className='button' style={{ textAlign: 'center' }}>
														<i title={lang('Upload File')} className="fa fa-cloud-upload button" aria-hidden="true" style={{ fontSize: 14, marginLeft: 0 }}></i>
														&nbsp;{lang('Upload File')}
													</div>

												</label>

												<input id={'input' + this.id} ref={input => this.fileInput = input}
													type="file"
													style={{ display: 'none' }}
													onChange={(event) => {
														this.uploadData(event.target.files)
													}}
													multiple
												/>
											</div>}



										</div>
										<div style={{ maxHeight: 600, overflow: 'auto', padding: 5 }}>

											{this.state.folderId == 0
												? ''
												: <div className='box_flex file_item_bar' onClick={e => {
													var pwd = this.state.pwd.length > 0 ? this.state.pwd.slice(0, this.state.pwd.length - 1) : [];
													var folderId = pwd.length > 0 ? pwd[pwd.length - 1]['id'] : 0;
													this.setState({
														folderId: folderId,
														pwd: pwd,
														preview: null,
													}, () => this.getChild())
												}}>
													<div style={{ width: 30 }}></div>
													<i className="fa fa-folder" style={{ color: '#ffc107', fontSize: 16 }}></i>&nbsp;<b className='button'>..</b></div>

											}

											{Object.values(this.state.folders).map(item => {
												return <div key={item['id']} className='file_item_bar box_flex' onContextMenu={e => {
													this.contextMenu.setMenu(<div className='box_shadow box_border' style={{ background: 'white', borderRadius: 3, padding: 5 }}>

														<div className='button' style={{ padding: 5 }} onClick={() => {
															this.setState({ editing: item['id'], editing_value: this.basename(item['name']) })
														}}><b>{lang('Edit')}</b></div>

														<div className='button' style={{ padding: 5 }} onClick={e => this.delFolder(item['id'])}><b>{lang('Delete')}</b></div>
													</div>)
													this.contextMenu.show(e);
												}}>
													<div style={{ width: 30 }}>
														<input type="checkbox" checked={isset(this.state.selects[item[this.state.key]])} onChange={e => {
															var select = this.state.selects;
															console.log('test')
															if (e.target.checked) {
																select[item[this.state.key]] = true;
															} else {
																delete (select[item[this.state.key]]);
															}
															this.setState({ selects: select });

														}} style={{ display: 'block', height: 14, width: 14 }}>
														</input>
													</div>

													<div>
														<i className="fa fa-folder" style={{ color: '#ffc107', fontSize: 16 }}></i>
													</div>
													&nbsp;
													<div className='button' onClick={e => {
														var pwd = this.state.pwd;
														pwd.push(item);
														this.setState({
															folderId: item['id'],
															files: {},
															folders: {},
															pwd: pwd,
															preview: null,
														}, e => this.getChild())
													}} >
														{this.state.editing == item['id']
															? <input className='input' value={this.state.editing_value} onChange={e => this.setState({ editing_value: e.target.value })}
																onBlur={e => this.editFolder()}
																onClick={e => e.stopPropagation()}
															></input>
															: this.basename(item['name'])}
													</div>
												</div>
											})}

											{Object.values(this.state.files).map(item => {
												return <div key={item['id']} className='file_item_bar box_flex' onContextMenu={e => {
													this.contextMenu.setMenu(<div className='box_shadow box_padding' style={{ background: 'white' }}>

														<div className='button' style={{ padding: 5 }} onClick={() => {
															this.setState({ editing: item['id'], editing_value: this.basename(item['name']) })
														}}><b>{lang('Edit')}</b></div>

														<div className='button' style={{ padding: 5 }} onClick={e => this.delFile(item['id'])}><b>{lang('Delete')}</b></div>
													</div>)
													this.contextMenu.show(e);
												}}>
													<div style={{ width: 30 }}>
														<input type="checkbox" checked={isset(this.state.selects[item[this.state.key]])} onChange={e => {
															var select = this.state.selects;

															if (e.target.checked) {
																select[item[this.state.key]] = true;
															} else {
																delete (select[item[this.state.key]]);
															}
															this.setState({ selects: select });

														}} style={{ display: 'block', height: 14, width: 14 }}>
														</input>
													</div>

													<div>
														<i className={item['mime'].includes('image') ? "fa fa-file-image-o" : "fa fa-file-o"} style={{ color: 'gray', fontSize: 16 }}></i>
													</div>
													&nbsp;
													<div className='button' onClick={() => {
														this.setState({ preview: item }, () => this.previewFile(item['id']));
													}} >
														{this.state.editing == item['id']
															? <input className='input' value={this.state.editing_value} onChange={e => this.setState({ editing_value: e.target.value })}
																onBlur={e => this.editFile()}
																onClick={e => e.stopPropagation()}
															></input>
															: this.basename(item['name'])}
													</div>
												</div>
											})}

										</div>
									</div>
									<div className='col-md-4'>

										{(() => {
											if (this.state.preview == null) return '';
											return <><div style={{ textAlign: 'center' }}>
												{this.state.preview['mime'].includes('image')
													? <img style={{ width: '100%' }} src={get(this.state.preview['link'], '')}></img>
													: <i className="fa fa-file-o" style={{ color: 'gray', fontSize: 36 }}></i>
												}

											</div>
												<div>
													<table>
														<tbody>
															<tr><th style={{ whiteSpace: 'nowrap' }}>{lang('Tên file')}</th><td>:</td><td style={{ wordBreak: 'break-all' }}>{this.state.preview['name']}</td></tr>
															<tr><th style={{ whiteSpace: 'nowrap' }}>{lang('Kích thước')}</th><td>:</td><td style={{ wordBreak: 'break-all' }}>{this.showSize(this.state.preview['size'])}</td></tr>
															<tr><th style={{ whiteSpace: 'nowrap' }}>{lang('Người tạo')}</th><td>:</td><td style={{ wordBreak: 'break-all' }}>{this.state.preview['createUsername']}</td></tr>
														</tbody>
													</table>
												</div>
											</>
										})()}

									</div>
								</div>

							</div>



							<div className="modal-footer">
								<button type="button" className="btn btn-primary" onClick={() => { this.onClickHandle() }}>{lang('Chọn')}</button>
								<button type="button" className="btn btn-danger" data-dismiss="modal">{lang('Hủy')}</button>
							</div>

						</div>
					</div>
				</div>
				<ContextMenu ref={c => this.contextMenu = c}></ContextMenu>
				<style>{`
									.file_item_bar{
										padding: 2px;
									}
									.file_item_bar:hover{
										background: aliceblue;
										box-shadow: 1px 0px #d2e9fe, -1px 0px #d2e9fe, 0px 1px #d2e9fe, 0px -1px #d2e9fe;
										border-radius: 3px;
									}

									.file_button .button { 
										padding: 5px;
										border-radius: 3px;
										background: #eee;
										color: #1774b5;
									}
									
									`}</style>
			</>
		)
	}


	componentDidMount() {

	}

}
export default FileManager
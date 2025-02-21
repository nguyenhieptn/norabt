import React, { Component } from 'react'
import Table from '../../components/table/TableStatic'
import MainTable from '../../components/table/MainTable'
import Pagination from '../../components/table/Pagination'
import FuncBar from '../../components/table/FuncBar'
import FuncDel from '../../components/table/FuncDel'


class FilesManager extends Component {

	constructor(props) {
		super(props);
		this.id = makeId();

		this.state = {
			preview: null,
		}
		
		this.uploader_files_struct = {};
		this.uploader_files_struct[STRUCT_FILTERS] = {}
		this.uploader_files_struct[STRUCT_COLUMNS] = {

			[FILE_NAME]: {
				[COL_NAME]: lang(FILE_NAME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var item = data[rowId];
					return <div className='box_flex'>
						<div>
							<i className={(item[FILE_MIME] && item[FILE_MIME].includes('image')) ? "fa fa-file-image-o" : "fa fa-file-o"} style={{ color: 'gray', fontSize: 16 }}></i>
						</div>
						&nbsp;
						<div className='button' onClick={() => {
								this.setState({ preview: item }, () =>{
									if(item[FILE_MIME].includes('image')) this.previewFile(item[FILE_PATH]);
								});
							}} >
								{this.state.editing == item[FILE_PATH]
									? <input className='input' value={this.state.editing_value} onChange={e => this.setState({ editing_value: e.target.value })}
										onBlur={e => this.editFile()}
										onClick={e => e.stopPropagation()}
									></input>
									: item[FILE_NAME]}
							</div>
						</div>
				}

			},

			[FILE_MODIFIED]: {
				[COL_NAME]: lang(FILE_MODIFIED),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => data != '' ? moment(data, 'X').format('DD/MM/YYYY HH:mm') : ''

			},

			[FILE_MIME]: {
				[COL_NAME]: lang(FILE_MIME),
				[COL_SORT]: true,
			},

			[FILE_SIZE]: {
				[COL_NAME]: lang(FILE_SIZE),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => this.showSize(data)

			},
		}

		this.uploader_files_struct[STRUCT_FILTERS] = {
			[FILE_NAME]: {
				[FILTER_NAME]: lang(FILE_NAME),
				[FILTER_TYPE]: 'text'

			},
		}

		this.uploader_files_struct[STRUCT_EDIT] = {}

		this.uploader_files_struct[STRUCT_ROWS] = {};

		this.uploader_files_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: UPLOADER_FILES_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionUploader_files(),
			[DATA_KEY]: [FILE_PATH],
			[DATA_SORT]: { [FILE_MODIFIED]: 'desc' },
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: false,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_FILTER]: true,
			[FLAG_ROW_INDEX]: false,
			[FLAG_HEAD_ROW]: true,
		};
	}

	permissionUploader_files() {
		return Object.assign(
			...Object.keys(this.uploader_files_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.uploader_files_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}


	modal(cmd = 'show') {
		if (cmd == 'hide') {
			$("#file_mng_modal" + this.id).modal('hide');
		} else {
			$("#file_mng_modal" + this.id).modal();
			this.setSelected([]);
			this.table.loadOrigin();
		}
	}


	onClickHandle() {
		if (this.onSelect) {
			this.onSelect(this.getSelected());
		}
	}

	setOnSelect(callback) {
		this.onSelect = callback;
	}

	setSelected(selected) {
		
		var selectedTable = {};
		for (let i in selected) {
			selectedTable[selected[i]] = {[FILE_PATH]: selected[i]}
		}
		console.log(selectedTable);
		this.table[STRUCT_TABLE][DATA_SELECT_ROWS] = selectedTable;
		this.table.reload();
	}

	getSelected() {
		var selectedTable = this.table[STRUCT_TABLE][DATA_SELECT_ROWS]
		var selected = [];
		for(let i in selectedTable){
			selected.push(selectedTable[i][FILE_PATH]);
		}
		return selected;
	}

	setKey(key) {
		this.setState({ key: key });
	}

	getFiles() {
		if (!this.props.links || !this.props.links.get) return;
		App.loading(true)
		axios.request({
			url: this.props.links.get.link,
			method: this.props.links.get.method,
			params: {
				column: this.props.column
			}
		})

			.then(response => {
				App.loading(false)
				response = response['data'];
				if (response['result']) {
					response = response['data'];
					this.table.setOrigin(response);
					this.table.filter();
				} else {
					error_handle(response)
				}

			})

			.catch((error) => {
				App.loading(false)
				console.log(error);
				error_handle(error);
			})
	}



	getChild() {
		this.getFiles();
	}

	basename(path) {
		if (!path) return '';
		return path.replace(/.*\//, '');
	}

	showSize(size) {
		if (size < 1000000) return Math.round(size / 1000) + 'KB';
		return Math.round(size / 10000000) / 10 + 'MB';
	}

	previewFile(path) {

		this.readFile(path).then(blob => {
			if(blob){
				const blobURL = window.URL.createObjectURL(blob);
				var preview = this.state.preview;
				preview['link'] = blobURL;
				this.setState({ preview })
			}
		})
	}

	getFileLink(path){
		return this.props.links.read.link + '?file=' + path;
	}

	downloadFile(path){
		this.readFile(path).then(blob => {
			if(blob){
				var a = document.createElement('a'); 
				a.download = path.replace(/^.*[\\\/]/, ''); 
				a.href = URL.createObjectURL(blob); 
				a.click();
			}
		})
	}

	readFile(path){
		if (!this.props.links || !this.props.links.read) {
			console.log('No read link');
			return Promise.resolve(false)
		}
		App.loading(true)
		return axios.request({
			url: this.props.links.read.link,
			method: this.props.links.read.method,
			params: { file: path },
			responseType: 'blob'
		})
		
		.then(response => {
			App.loading(false, 'Downloading...');
			response = response['data'];
			var blob = new Blob([response]);
			return blob;
    	    
		})
		
		.catch((error)=> {
			App.loading(false, 'Downloading...')
			console.log(error);
			error_handle(error);
		})
	}

	delRows(delkeys, alert = true) {
		
		var selected = this.getSelected();

		if (selected.length == 0) {
			showLog('Select rows you want to delete', 'error');
			return Promise.reject();
		}

		if (alert) {
			return this.table.deleteAlert().then(async result => {
				if (result) {
					for(let i in selected){
						var result = await this.delFile(selected[i]);
						if(!result || !result['result']) return;
					}
					
					this.table[STRUCT_TABLE][DATA_SELECT_ROWS] = {};
					this.table.loadOrigin();
				} else {
					return Promise.reject();
				}
			})
		}else {
			return Promise.reject();
		}
		
	}

	delFile(path) {
		if (!this.props.links || !this.props.links.delete) {
			console.log('No delete link');
			return Promise.resolve(false)
		};
		App.loading(true);
		return axios.request({
			url: this.props.links.delete.link,
			method: this.props.links.delete.method,
			data: {
				file: path
			}
		})

			.then(response => {
				response = response['data'];
				App.loading(false);
				return response;
			})

			.catch((error) => {
				App.loading(false);
				error_handle(error);
			})
	}


	async uploadDatas(files) {

		var selected = [];
		for (let i = 0; i < files.length; i++) {
			var result = await this.upload(files[i]);
			if (result && result['result']) {
				var file = result['data'];
				selected.push(file[FILE_PATH]);
			}
		}

		this.setSelected(selected);
		this.getFiles();
	}


	async upload(file) {
		var response = await this.getUploadLink(file);
		if (!response) return false;
		if (!response['result']) {
			error_handle(response);
			return false;
		}

		if (response['data']) {
			response = response['data'];
			response = await this.uploadData(response['ulink'], response['utoken'], file);
			if (!response) return false;
			if (!response['result']) {
				error_handle(response);
				return false;
			}
			return response;
		}

		return true;

	}


	getUploadLink(file) {
		if (!this.props.links || !this.props.links.upload) {
			console.log('No upload link');
			return Promise.resolve(false)
		}

		App.loading(true);
		return axios.request({
			url: this.props.links.upload.link,
			method: this.props.links.upload.method,
			data: {
				column: this.props.column,
				action: 'Upload',
				file: { 'size': file.size }
			}
		})

			.then(async (response) => {
				App.loading(false);
				response = response['data'];
				return response;
			})
			.catch((error) => {
				App.loading(false);
				console.log(error);
				error_handle(error)
			})
	}

	uploadData(url, token, file) {

		let formData = new FormData();
		formData.append('file', file);
		formData.append('utoken', token);

		App.loading(true);
		return axios.request({
			url: url,
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
				return response;

			})

			.catch((error) => {
				App.loading(false);
				console.log(error);
				error_handle(error)

			})
	}


	render() {

		return (
			<>
				<div className="modal fade" id={"file_mng_modal" + this.id}>
					<div className="modal-dialog modal-lg modal-dialog-centered">
						<div className="modal-content">

							<div className="modal-header">
								<h5 className="modal-title">{lang("Files Gallery")}</h5>
								<button type="button" className="close" data-dismiss="modal">&times;</button>
							</div>

							<div className="modal-body" style={{ textAlign: 'initial' }}>

								<div className='box_filedrag'
									onDragOver={(e) => e.preventDefault()}
									onDragEnter={(e) => e.preventDefault()}
									onDrop={(e) => { this.uploadDatas(e.dataTransfer.files); e.preventDefault() }}
								>
									<div><h5>Drag and Drop files here</h5></div>

									<div>OR</div>

									<label htmlFor={'input' + this.id} style={{ margin: 0 }}>

										<div className='button btn btn-outline-primary' style={{ textAlign: 'center' }}>
											<i title={lang('Browse Files')} className="fa fa-cloud-upload button" aria-hidden="true" style={{ fontSize: 14, marginLeft: 0 }}></i>&nbsp;{lang('Browse Files')}
										</div>

									</label>

									<input id={'input' + this.id} ref={input => this.fileInput = input}
										type="file"
										style={{ display: 'none' }}
										onChange={(event) => {

											this.uploadDatas(event.target.files).then(() => {
												this.fileInput.value = '';
											})


										}}
										multiple
									/>
								</div>

								<div className='row' style={{ padding: 0 }}>
									<div className='col-md-8' >


										<Table ref={table => this.table = table} table={this.uploader_files_struct} autoload={false} 
											loadOrigin={this.getFiles.bind(this)}
											delRows = {this.delRows.bind(this)}
										>
											<FuncBar
												right={<><FuncDel /></>}></FuncBar>
											<MainTable className='table_file'></MainTable>
											<Pagination></Pagination>
										</Table>

										
									</div>
									<div className='col-md-4'>

										{(() => {
											if (this.state.preview == null) return '';
											return <><div style={{ textAlign: 'center', marginBottom: 15 }}>
												{this.state.preview[FILE_MIME] && this.state.preview[FILE_MIME].includes('image')
													? <img style={{ width: '90%' }} src={get(this.state.preview['link'], '')}></img>
													: <i className="fa fa-file-o" style={{ color: 'gray', fontSize: 36 }}></i>
												}

											</div>
												<div>
													<table style={{ width: '100%', tableLayout: 'fixed' }}>
														<tbody>
															<tr><th style={{ whiteSpace: 'nowrap' }}>{lang(FILE_NAME)}</th><td style={{ width: 10 }}>:</td><td title={this.state.preview[FILE_NAME]}><div className='box_line'>{this.state.preview[FILE_NAME]}</div></td></tr>
															<tr><th style={{ whiteSpace: 'nowrap' }}>{lang(FILE_SIZE)}</th><td style={{ width: 10 }}>:</td><td>{this.showSize(this.state.preview[FILE_SIZE])}</td></tr>
															<tr><th style={{ whiteSpace: 'nowrap' }}>{lang('Download')}</th><td style={{ width: 10 }}>:</td><td><i className="fa fa-cloud-download button" onClick={()=>this.downloadFile(this.state.preview[FILE_PATH])}></i></td></tr>
														</tbody>
													</table>
												</div>
											</>
										})()}

									</div>
								</div>

							</div>



							<div className="modal-footer">
								<button type="button" className="btn btn-primary" onClick={() => { this.onClickHandle() }}>{lang('Select')}</button>
								<button type="button" className="btn btn-danger" data-dismiss="modal">{lang('Cancel')}</button>
							</div>

						</div>
					</div>
				</div>

				<style>{`
						.file_item_bar{
							padding: 2px;
						}
						
						.file_button .button { 
							padding: 5px;
							border-radius: 3px;
							background: #eee;
							color: #1774b5;
						}
						.table_file {
							width: 100%;
						}
						.table_file td {
							padding: 5px;
							border: none;
						}
						.table_file tr {
							border: none;
						}
						.table_file .button {
							font-size: 12px;
						}
						.table_file thead th {
							padding: 5px;
							white-space: nowrap;
							border: none;
							border-bottom: none;
							border-right: solid thin white;
							background: #eeee;

						}
						.box_filedrag{
							text-align: center;
							padding: 10px;
							border: thin dashed #ccc;
							border-radius: 5px;
						}
						.box_filedrag:hover{
							border: thin dashed #aaa;
						}

						
				`}</style>
			</>
		)
	}

}
export default FilesManager
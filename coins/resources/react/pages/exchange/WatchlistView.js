import React, { Component } from 'react'
import Table from '../../components/table/Table'
import MainTable from '../../components/table/MainTable'
import Pagination from '../../components/table/Pagination'
import FuncBar from '../../components/table/FuncBar'

import FuncEditRow from '../../components/table/FuncEditRow'
import FuncAdd from '../../components/table/FuncAdd'
import FuncHideCol from '../../components/table/FuncHideCol'
import FuncDel from '../../components/table/FuncDel'
import FuncClear from '../../components/table/FuncClear'
import FuncRefresh from '../../components/table/FuncRefresh'
import FuncExport from '../../components/table/FuncExport'
import { Link } from 'react-router-dom';
import Watchlist from '../../model/admin/Watchlist'
import FuncConfigModal from '../../components/table/FuncConfigModal'
import FilesManager from '../../components/input/FilesManager'

class WatchlistView extends Component {

	constructor(props) {
		super(props);

		this.watchlist_struct = {};
		this.watchlist_struct[STRUCT_FILTERS] = {}
		this.watchlist_struct[STRUCT_COLUMNS] = {


			[WL_SYMBOL]: {
				[COL_NAME]: lang(WL_SYMBOL),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => {
					return <b >{data}</b>
				},
				// [COL_STYLE]: { textAlign: 'center' }

			},

			[WL_ICON]: {
				[COL_NAME]: lang(WL_ICON),
				[COL_SORT]: false,
				[COL_DECORATOR_IN]: (data) => { if (data != null) return <img width='100px' src={'/admin/watchlist/uploader_read?file=' + data}></img> },
				[COL_STYLE]: { textAlign: 'center' }
			},

			'crawler_service': {
				[COL_NAME]: lang('Crawler Service'),
				[COL_DECORATOR_IN]: data => {
					return data ? <div style={{ color: '#00e209', fontWeight: 'bold', textAlign: 'center' }}>Running</div> : <div style={{ color: 'red', fontWeight: 'bold', textAlign: 'center' }}>Stopped</div>
				}
			},
			// 'lab_service': {
			// 	[COL_NAME]: lang('LAB Service'),
			// 	[COL_DECORATOR_IN]: data => {
			// 		return data ? <div style={{ color: '#00e209', fontWeight: 'bold', textAlign: 'center' }}>Running</div> : <div style={{ color: 'red', fontWeight: 'bold', textAlign: 'center' }}>Stopped</div>
			// 	}
			// },
			// [WL_PARAMS]: {
			// 	[COL_NAME]: lang(WL_PARAMS),
			// 	[COL_DECORATOR_IN]: data => {
			// 		var configs = JSON.parse(data);
			// 		if (isset(configs)) {
			// 			configs = Object.keys(configs).map((key) => {
			// 				return <div key={key} className="box_flex">
			// 					<div className="box_line" style={{ flex: 2 }}>{lang(key)}</div>
			// 					<div>:&nbsp;</div>
			// 					<div title={configs[key]} className="box_line" style={{ flex: 1 }}>{configs[key]}</div>
			// 				</div>
			// 			});
			// 		} else {
			// 			configs = '';
			// 		}
			// 		return <div>{configs}</div>
			// 	}
			// },
			[WL_TIME]: {
				[COL_NAME]: lang(WL_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' , textAlign : 'center' }

			},
			[WL_STOPTIME]: {
				[COL_NAME]: lang(WL_STOPTIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' , textAlign : 'center' }
			},
			[WL_NOTE]: {
				[COL_NAME]: lang(WL_NOTE),
				[COL_SORT]: false,

			},




		}
		this.watchlist_struct[STRUCT_FILTERS] = {


			[WL_SYMBOL]: {
				[FILTER_NAME]: lang(WL_SYMBOL),
				[FILTER_TYPE]: 'text',
			},


		}

		this.watchlist_struct[STRUCT_EDIT] = {


			[WL_SYMBOL]: {
				[EDIT_NAME]: lang(WL_SYMBOL),
				[EDIT_TYPE]: 'text',
				[EDIT_NULL]: false,

			},

			[WL_ICON]: {
				[EDIT_NAME]: lang(WL_ICON),
				[EDIT_TYPE]: 'image',
				[EDIT_EXTEND]: {
					fileManager: () => this.filesManagerWl_icon
				}
			},

			[WL_NOTE]: {
				[EDIT_NAME]: lang(WL_NOTE),
				[EDIT_TYPE]: 'textarea',

			},




		}

		this.watchlist_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex r' style={{ flexWrap: 'wrap', justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData} ><div className='button btn btn-warning btn-sm' style={{ fontSize: 12, marginRight: 0 }}>Edit</div></FuncEditRow>
					{/* <div className='button btn btn-warning btn-sm' onClick={() => {
						this.configModal.loadData(rowData);
						this.configModal.modal();
					}} style={{ fontSize: 12, marginRight: 0 }}>Parmas</div> */}
					{/* <div className='button btn btn-info btn-sm' onClick={() => { this.getHistory(rowData[WL_SYMBOL]) }} style={{fontSize:10, flexGrow:1, marginRight:0}}>History</div> */}
					{/* <div className='button btn btn-info btn-sm' onClick={() => { this.caculateEma(rowData[WL_SYMBOL]) }} style={{fontSize:10, flexGrow:1, marginRight:0}}>EMA Cal</div> */}
					<div className='button btn btn-danger btn-sm' onClick={() => { this.cleanData(rowData[WL_SYMBOL]) }} style={{ fontSize: 12, marginRight: 0 }}>Clean</div>
					{/* <div className='button btn btn-primary btn-sm' onClick={() => { this.startService(rowData[WL_SYMBOL]) }} style={{ fontSize: 12, marginRight: 0 }}>Start Crawler</div> */}
					{/* <div className='button btn btn-danger btn-sm' onClick={() => { this.stopService(rowData[WL_SYMBOL]) }} style={{ fontSize: 8, marginRight: 0 }}>Stop Crawler</div>
					<div className='button btn btn-danger btn-sm' onClick={() => { this.restartService(rowData[WL_SYMBOL]) }} style={{ fontSize: 8, marginRight: 0 }}>Restart Crawler</div>
					<div className='button btn btn-primary btn-sm' onClick={() => { this.startEventService(rowData[WL_SYMBOL]) }} style={{ fontSize: 8, marginRight: 0 }}>Restart LAB</div>
					<div className='button btn btn-danger btn-sm' onClick={() => { this.stopEventService(rowData[WL_SYMBOL]) }} style={{ fontSize: 8, marginRight: 0 }}>Stop LAB</div> */}
					<div className='button btn btn-primary btn-sm' onClick={() => { this.restartService(rowData[WL_SYMBOL]) }} style={{ fontSize: 12, marginRight: 0  }}>Start Crawler</div>
					<div className='button btn btn-danger btn-sm' onClick={() => { this.stopService(rowData[WL_SYMBOL]) }} style={{ fontSize: 12}}>Stop Crawler</div>
					{/* <Link to={App.link('/admin/watchlist/control?symbol='+rowData[WL_SYMBOL])}><div className='button btn btn-warning btn-sm' style={{fontSize:12}}>Parmas</div></Link> */}
				</div>
			}
		};
		this.watchlist_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: WATCHLIST_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionWatchlistView(),
			[DATA_KEY]: [WL_ID, WL_SYMBOL],
			[DATA_SORT]: { [WL_ID]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Watchlist()

		};


	}

	permissionWatchlistView() {
		return Object.assign(
			...Object.keys(this.watchlist_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.watchlist_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.watchlist_struct} autoload={true}>
					<FuncBar
						left={<>
							<FuncHideCol />
							{/* <div className='button btn btn-primary btn-sm' onClick={() => { this.startServices() }} style={{ fontSize: 12, marginRight: 0 }}>Start Crawler</div> */}
							<div className='button btn btn-primary btn-sm' onClick={() => { this.restartServices() }} style={{ fontSize: 12, marginRight: 0 }}>Start Crawler</div>
							<div className='button btn btn-danger btn-sm' onClick={() => { this.stopServices() }} style={{ fontSize: 12, marginRight: 0 }}>Stop Crawler</div>

							{/* <div className='button btn btn-primary btn-sm' onClick={() => { this.startEventServices() }} style={{ fontSize: 12, marginRight: 0 }}>Restart LAB</div>
							<div className='button btn btn-danger btn-sm' onClick={() => { this.stopEventServices() }} style={{ fontSize: 12, marginRight: 0 }}>Stop LAB</div> */}
						</>}
						right={<><FuncAdd /><FuncDel /><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-striped table-resizable'></MainTable>
					<Pagination></Pagination>

					{/* <FuncConfigModal ref={c => this.configModal = c} struct={{
						// [WL_PARAMS_STOPLOSS]: {
						// 	[INPUT_NAME]: lang(WL_PARAMS_STOPLOSS) + ' (%)',
						// 	[INPUT_TYPE]: 'number',
						// 	[INPUT_NULL]: false,
						// },
						// [WL_PARAMS_TAKEPROFIT]: {
						// 	[INPUT_NAME]: lang(WL_PARAMS_TAKEPROFIT) + ' (%)',
						// 	[INPUT_TYPE]: 'number',
						// 	[INPUT_NULL]: false,
						// },
						// [WL_PARAMS_BASEPROFIT]: {
						// 	[INPUT_NAME]: lang(WL_PARAMS_BASEPROFIT) + ' (%)',
						// 	[INPUT_TYPE]: 'number',
						// 	[INPUT_NULL]: false,
						// },
						// [WL_PARAMS_STEPPROFIT]: {
						// 	[INPUT_NAME]: lang(WL_PARAMS_STEPPROFIT) + ' (%)',
						// 	[INPUT_TYPE]: 'number',
						// 	[INPUT_NULL]: false,
						// },
						// [WL_PARAMS_BACK_STEPPROFIT]: {
						// 	[INPUT_NAME]: lang(WL_PARAMS_BACK_STEPPROFIT) + ' (%)',
						// 	[INPUT_TYPE]: 'number',
						// 	[INPUT_NULL]: false,
						// },
						// [WL_PARAMS_TIMELIFE]: {
						// 	[INPUT_NAME]: lang(WL_PARAMS_TIMELIFE) + ' (minute)',
						// 	[INPUT_TYPE]: 'number',
						// },
						[WL_PARAMS_LOG]: {
							[INPUT_NAME]: lang(WL_PARAMS_LOG),
							[INPUT_TYPE]: 'select',
							[INPUT_DEFAULT]: 0,
							[INPUT_OPTION]: {0: 'False', 1: 'True'},
						},
					}} column={WL_PARAMS}></FuncConfigModal> */}

				</Table>

				<FilesManager ref={c => this.filesManagerWl_icon = c} column={WL_ICON} links={{
					get: { method: "GET", link: "/admin/watchlist/uploader_get" },
					read: { method: "GET", link: "/admin/watchlist/uploader_read" },
					upload: { method: "POST", link: "/admin/watchlist/uploader_upload" },
					delete: { method: "POST", link: "/admin/watchlist/uploader_delete" },
				}}></FilesManager>


			</div>
		);
	}

	componentDidMount() {

	}


	getHistory(symbol) {
		App.loading(true)
		return axios.request({
			url: `/admin/watchlist/crawHistory`,
			method: 'POST',
			data: {
				symbol: symbol
			}
		})

			.then(response => {
				App.loading(false);
				response = response['data'];
				return response;
			})

			.catch((error) => {
				App.loading(false);
				error_handle(error)
				return false;
			})
	}

	// caculateEma(symbol) {
	// 	App.loading(true)
	// 	return axios.request({
	// 		url: `/admin/watchlist/caculateEma`,
	// 		method: 'POST',
	// 		data: {
	// 			symbol: symbol
	// 		}
	// 	})

	// 		.then(response => {
	// 			App.loading(false);
	// 			response = response['data'];
	// 			return response;
	// 		})

	// 		.catch((error) => {
	// 			App.loading(false);
	// 			error_handle(error)
	// 			return false;
	// 		})
	// }


	// startService(symbol, loading = true) {
	// 	if (loading) App.loading(true)
	// 	return axios.request({
	// 		url: `/admin/watchlist/restartService`,
	// 		method: 'POST',
	// 		data: {
	// 			symbol: symbol
	// 		}
	// 	})

	// 		.then(response => {
	// 			if (loading) App.loading(false);
	// 			response = response['data'];
	// 			if (response['result']) {
	// 				this.table.filter(loading);
	// 			}
	// 			else {
	// 				error_handle(response);
	// 			}
	// 		})

	// 		.catch((error) => {
	// 			if (loading) App.loading(false);
	// 			error_handle(error)
	// 			return false;
	// 		})
	// }


	// async startServices() {
	// 	var dataSelect = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];
	// 	var wl = [];
	// 	for (let i in dataSelect) {
	// 		wl.push(dataSelect[i][WL_SYMBOL]);
	// 	}

	// 	if (wl.length == 0) {
	// 		showLog('Please select a symbol');
	// 		return;
	// 	}

	// 	var confirm = await makeQuestion('Do you want to start service: ' + wl.join(', ') + '?');
	// 	if (!confirm) return;

	// 	var promises = [];
	// 	App.loading(true);
	// 	for (let i in wl) {
	// 		promises.push(this.startService(wl[i], false));
	// 	}

	// 	Promise.all(promises).then(value => {
	// 		App.loading(false);
	// 		this.table.filter();
	// 	});
	// }


	async stopServices() {

		var dataSelect = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];
		var wl = [];
		for (let i in dataSelect) {
			wl.push(dataSelect[i][WL_SYMBOL]);
		}

		if (wl.length == 0) {
			showLog('Please select a symbol');
			return;
		}

		var confirm = await makeQuestion('Do you want to Stop crawl Data: ' + wl.join(', ') + '?');
		if (!confirm) return;

		for (let i in wl) {
			await this.stopService(wl[i]);
		}
	}

	async stopService(symbol) {

		App.loading(true)
		return axios.request({
			url: `/admin/watchlist/stopService`,
			method: 'POST',
			data: {
				symbol: symbol
			}
		})

			.then(response => {
				App.loading(false);
				response = response['data'];
				if (response['result']) {
					this.table.filter();
				}
				else {
					error_handle(response);
				}
			})

			.catch((error) => {
				App.loading(false);
				error_handle(error)
				return false;
			})
	}


	async restartServices() {

		var dataSelect = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];
		var wl = [];
		for (let i in dataSelect) {
			wl.push(dataSelect[i][WL_SYMBOL]);
		}

		if (wl.length == 0) {
			showLog('Please select a symbol');
			return;
		}

		var confirm = await makeQuestion('All old data will be deleted. Do you want to restart crawl Data: ' + wl.join(', ') + '?');
		if (!confirm) return;

		for (let i in wl) {
			await this.restartService(wl[i]);
		}
	}

	restartService(symbol) {

		App.loading(true)
		return axios.request({
			url: `/admin/watchlist/restartService`,
			method: 'POST',
			data: {
				symbol: symbol
			}
		})

			.then(response => {
				App.loading(false);
				response = response['data'];
				if (response['result']) {
					this.table.filter();
				}
				else {
					error_handle(response);
				}
			})

			.catch((error) => {
				App.loading(false);
				error_handle(error)
				return false;
			})
	}


	// async startEventServices(){

	// 	var dataSelect = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];
	// 	var wl = [];
	// 	for(let i in dataSelect){
	// 		wl.push(dataSelect[i][WL_SYMBOL]);
	// 	}

	// 	if(wl.length == 0){
	// 		showLog('Please select a symbol');
	// 		return;
	// 	}

	// 	var confirm = await makeQuestion('Do you want to Start/Restart Lab service: ' + wl.join(', ') + '?');
	// 	if (!confirm) return;

	// 	for(let i in wl){
	// 		await this.startEventService(wl[i]);
	// 	}
	// }


	// startEventService(symbol) {
	// 	App.loading(true)
	// 	return axios.request({
	// 		url: `/admin/watchlist/startEventService`,
	// 		method: 'POST',
	// 		data: {
	// 			symbol: symbol
	// 		}
	// 	})

	// 		.then(response => {
	// 			App.loading(false);
	// 			response = response['data'];
	// 			if (response['result']) {
	// 				this.table.filter();
	// 			}
	// 			else {
	// 				error_handle(response);
	// 			}
	// 		})

	// 		.catch((error) => {
	// 			App.loading(false);
	// 			error_handle(error)
	// 			return false;
	// 		})
	// }


	// async stopEventServices(){

	// 	var dataSelect = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];
	// 	var wl = [];
	// 	for(let i in dataSelect){
	// 		wl.push(dataSelect[i][WL_SYMBOL]);
	// 	}

	// 	if(wl.length == 0){
	// 		showLog('Please select a symbol');
	// 		return;
	// 	}

	// 	var confirm = await makeQuestion('Do you want to Stop Lab service: ' + wl.join(', ') + '?');
	// 	if (!confirm) return;

	// 	for(let i in wl){
	// 		await this.stopEventService(wl[i]);

	// 	}
	// }

	// stopEventService(symbol) {
	// 	App.loading(true)
	// 	return axios.request({
	// 		url: `/admin/watchlist/stopEventService`,
	// 		method: 'POST',
	// 		data: {
	// 			symbol: symbol
	// 		}
	// 	})

	// 		.then(response => {
	// 			App.loading(false);
	// 			response = response['data'];
	// 			if (response['result']) {
	// 				this.table.filter();
	// 			}
	// 			else {
	// 				error_handle(response);
	// 			}
	// 		})

	// 		.catch((error) => {
	// 			App.loading(false);
	// 			error_handle(error)
	// 			return false;
	// 		})
	// }


	async cleanData(symbol) {
		var confirm = await makeQuestion('Do you want to clean data?');
		if (!confirm) return;
		App.loading(true)
		return axios.request({
			url: `/admin/watchlist/cleanData`,
			method: 'POST',
			data: {
				symbol: symbol
			}
		})

			.then(response => {
				App.loading(false);
				response = response['data'];
				if (response['result']) {
					this.table.filter();
				}
				else {
					error_handle(response);
				}
			})

			.catch((error) => {
				App.loading(false);
				error_handle(error)
				return false;
			})
	}


}

export default WatchlistView
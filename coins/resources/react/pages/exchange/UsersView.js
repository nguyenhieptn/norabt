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

import Accounts from '../../model/admin/Accounts'
import TradeList from '../../components/admin/TradeList'
import BinanceAccountBalanceChart from '../../components/admin/BinanceAccountBalanceChart'

class UsersView extends Component {

	constructor(props) {
		super(props);

		this.accounts_struct = {};
		this.accounts_struct[STRUCT_FILTERS] = {}
		this.accounts_struct[STRUCT_COLUMNS] = {


			// [ACCOUNT_SIGNATURE]: {
			// 	[COL_NAME]: lang(ACCOUNT_SIGNATURE),
			// 	[COL_SORT]: false,

			// },

			'Setup': {
				[COL_NAME]: lang("Setup"),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return (
						<div className='box_flex' style={{ justifyContent: 'center' }}>
							<FuncEditRow rowData={rowData}><div className='button btn btn-primary' style={{ fontSize: 12 }}>Edit</div></FuncEditRow>
							<div className='button btn btn-warning' onClick={() => {
								this.tradeList.setAccount(rowData[ACCOUNT_ID], rowData[ACCOUNT_NAME]);
								this.tradeList.modal();
							}} style={{ fontSize: 12 }}>Trades</div>

						</div>
					)
				}

			},

			'Action': {
				[COL_NAME]: lang("Action"),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return (
						<>
							<div className='button btn btn-primary btn-sm' onClick={() => { this.startService(rowData[ACCOUNT_ID]) }} style={{ fontSize: 12 }}>Reconnect</div>
						<div className='button btn btn-danger btn-sm' onClick={() => { this.stopService(rowData[ACCOUNT_ID]) }} style={{ fontSize: 12 }}>Disconnect</div>
						<div className='button btn btn-info' style={{ fontSize: 10 }} onClick={() => {
							this.accountBlanceChart.modal();
							this.accountBlanceChart.loadData(rowData);
						}}>Balance</div>
						</>
					)
				}

			},
			[ACCOUNT_NAME]: {
				[COL_NAME]: lang(ACCOUNT_NAME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => {
					return <b>{data}</b>
				}

			},
			'update_service': {
				[COL_NAME]: lang('Binance'),
				[COL_DECORATOR_IN]: data => {
					return data ? <div style={{ color: '#00e209', fontWeight: 'bold', textAlign: 'center' }}>Connected</div> : <div style={{ color: 'red', fontWeight: 'bold', textAlign: 'center' }}>Disconnected</div>
				}
			},
			[ACCOUNT_NOTE]: {
				[COL_NAME]: lang(ACCOUNT_NOTE),
				[COL_SORT]: false,

			},
			[ACCOUNT_TOTAL_INVEST]: {
				[COL_NAME]: lang(ACCOUNT_TOTAL_INVEST),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' }

			},
			[ACCOUNT_TYPE]: {
				[COL_NAME]: lang(ACCOUNT_TYPE),
				[COL_SORT]: true,

			},
			[ACCOUNT_USER]: {
				[COL_NAME]: lang(ACCOUNT_USER),
				[COL_SORT]: false,

			},
			[ACCOUNT_COMPOUND]: {
				[COL_NAME]: lang(ACCOUNT_COMPOUND),
				[COL_SORT]: false,

			},
			[ACCOUNT_START_TIME]: {
				[COL_NAME]: lang(ACCOUNT_START_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},
			[ACCOUNT_STOP_TIME]: {
				[COL_NAME]: lang(ACCOUNT_STOP_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},



			[ACCOUNT_TELE_BOT]: {
				[COL_NAME]: lang(ACCOUNT_TELE_BOT),
				[COL_SORT]: false,

			},
			[ACCOUNT_TELE_GR_NOTICE]: {
				[COL_NAME]: lang(ACCOUNT_TELE_GR_NOTICE),
				[COL_SORT]: false,

			},
			[ACCOUNT_TELE_GR_SUMMARY]: {
				[COL_NAME]: lang(ACCOUNT_TELE_GR_SUMMARY),
				[COL_SORT]: false,

			},
			[ACCOUNT_TELE_GR_ERROR]: {
				[COL_NAME]: lang(ACCOUNT_TELE_GR_ERROR),
				[COL_SORT]: false,

			},
			[ACCOUNT_API_KEY]: {
				[COL_NAME]: lang(ACCOUNT_API_KEY),
				[COL_SORT]: false,

			},
			[ACCOUNT_SECRET_KEY]: {
				[COL_NAME]: lang(ACCOUNT_SECRET_KEY),
				[COL_SORT]: false,

			},





		}
		this.accounts_struct[STRUCT_FILTERS] = {

			[ACCOUNT_NAME]: {
				[FILTER_NAME]: lang(ACCOUNT_NAME),
				[FILTER_TYPE]: 'text',
			},
			[ACCOUNT_TYPE]: {
				[FILTER_NAME]: lang(ACCOUNT_TYPE),
				[FILTER_TYPE]: 'select',
			},
			[ACCOUNT_USER]: {
				[FILTER_NAME]: lang(ACCOUNT_USER),
				[FILTER_TYPE]: 'select',
			},
			[ACCOUNT_COMPOUND]: {
				[FILTER_NAME]: lang(ACCOUNT_COMPOUND),
				[FILTER_TYPE]: 'select',
			},


		}

		this.accounts_struct[STRUCT_EDIT] = {

			[ACCOUNT_API_KEY]: {
				[EDIT_NAME]: lang(ACCOUNT_API_KEY),
				[EDIT_TYPE]: 'textarea',

			},
			[ACCOUNT_SECRET_KEY]: {
				[EDIT_NAME]: lang(ACCOUNT_SECRET_KEY),
				[EDIT_TYPE]: 'textarea',


			},
			// [ACCOUNT_SIGNATURE]: {
			// 	[EDIT_NAME]: lang(ACCOUNT_SIGNATURE),
			// 	[EDIT_TYPE]: 'textarea',

			// },
			[ACCOUNT_NAME]: {
				[EDIT_NAME]: lang(ACCOUNT_NAME),
				[EDIT_TYPE]: 'text',

			},
			[ACCOUNT_NOTE]: {
				[EDIT_NAME]: lang(ACCOUNT_NOTE),
				[EDIT_TYPE]: 'textarea',

			},
			[ACCOUNT_TOTAL_INVEST]: {
				[EDIT_NAME]: lang(ACCOUNT_TOTAL_INVEST),
				[EDIT_TYPE]: 'number',

			},
			[ACCOUNT_TYPE]: {
				[EDIT_NAME]: lang(ACCOUNT_TYPE),
				[EDIT_TYPE]: 'select',

			},
			[ACCOUNT_USER]: {
				[EDIT_NAME]: lang(ACCOUNT_USER),
				[EDIT_TYPE]: 'select',

			},

			[ACCOUNT_COMPOUND]: {
				[EDIT_NAME]: lang(ACCOUNT_COMPOUND),
				[EDIT_TYPE]: 'select',
				[EDIT_DEFAULT]: '1',

			},

			[ACCOUNT_TELE_BOT]: {
				[EDIT_NAME]: lang(ACCOUNT_TELE_BOT),
				[EDIT_TYPE]: 'text',

			},
			[ACCOUNT_TELE_GR_NOTICE]: {
				[EDIT_NAME]: lang(ACCOUNT_TELE_GR_NOTICE),
				[EDIT_TYPE]: 'text',

			},

			[ACCOUNT_TELE_GR_SUMMARY]: {
				[EDIT_NAME]: lang(ACCOUNT_TELE_GR_SUMMARY),
				[EDIT_TYPE]: 'textarea',
				[EDIT_DES]: 'Each group seprated by (,)'

			},

			[ACCOUNT_TELE_GR_ERROR]: {
				[EDIT_NAME]: lang(ACCOUNT_TELE_GR_ERROR),
				[EDIT_TYPE]: 'text',

			},


		}

		// this.accounts_struct[STRUCT_ROWS] = {
		// 	// [ROW_FUNCS]: (rowData) => {
		// 	// 	return <div className='box_flex' style={{ justifyContent: 'center' }}>
		// 	// 		<FuncEditRow rowData={rowData}><div className='button btn btn-primary' style={{ fontSize: 12 }}>Edit</div></FuncEditRow>
		// 	// 		<div className='button btn btn-warning' onClick={() => {
		// 	// 			this.tradeList.setAccount(rowData[ACCOUNT_ID], rowData[ACCOUNT_NAME]);
		// 	// 			this.tradeList.modal();
		// 	// 		}} style={{ fontSize: 12 }}>Trades</div>



		// 	// 	</div>
		// 	// }
		// };
		this.accounts_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: ACCOUNTS_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionUserView(),
			[DATA_KEY]: [ACCOUNT_ID],
			[DATA_SORT]: { [ACCOUNT_ID]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: false,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Accounts()

		};


	}

	permissionUserView() {
		return Object.assign(
			...Object.keys(this.accounts_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.accounts_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.accounts_struct} autoload={true}>
					<FuncBar
						left={<>
							<FuncHideCol />
							<div className='button btn btn-primary btn-sm' onClick={() => { this.startServices() }} style={{ fontSize: 12 }}>Connect</div>
							<div className='button btn btn-danger btn-sm' onClick={() => { this.stopServices() }} style={{ fontSize: 12 }}>Disconnect</div>
						</>}
						right={<><FuncAdd /><FuncDel /><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-striped table-resizable'></MainTable>
					<Pagination></Pagination>

				</Table>

				<TradeList ref={c => this.tradeList = c}></TradeList>

				<BinanceAccountBalanceChart ref={c => this.accountBlanceChart = c}></BinanceAccountBalanceChart>


			</div>
		);
	}

	componentDidMount() {

	}


	startService(id, loading = true) {
		if (loading) App.loading(true)
		return axios.request({
			url: `/admin/accounts/startService`,
			method: 'POST',
			data: {
				id: id
			}
		})

			.then(response => {
				if (loading) App.loading(false);
				response = response['data'];
				if (response['result']) {
					this.table.filter(loading);
				}
				else {
					error_handle(response);
				}
			})

			.catch((error) => {
				if (loading) App.loading(false);
				error_handle(error)
				return false;
			})
	}

	async startServices() {

		var dataSelect = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];
		var wl = [];
		for (let i in dataSelect) {
			wl.push(dataSelect[i][ACCOUNT_ID]);
		}

		if (wl.length == 0) {
			showLog('Please select a symbol');
			return;
		}

		var confirm = await makeQuestion('Do you want to Reconnect: ' + wl.length + ' Account?');
		if (!confirm) return;
		App.loading(true);
		for (let i in wl) {
			await this.startService(wl[i], false);
		}
		App.loading(false);
	}

	async stopServices() {

		var dataSelect = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];
		var wl = [];
		for (let i in dataSelect) {
			wl.push(dataSelect[i][ACCOUNT_ID]);
		}

		if (wl.length == 0) {
			showLog('Please select a symbol');
			return;
		}

		var confirm = await makeQuestion('Do you want to Disconnect: ' + wl.length + ' Account?');
		if (!confirm) return;
		App.loading(true);
		for (let i in wl) {
			await this.stopService(wl[i], false);
		}
		App.loading(false);
	}

	stopService(id, loading = true) {
		if (loading) App.loading(true)
		return axios.request({
			url: `/admin/accounts/stopService`,
			method: 'POST',
			data: {
				id: id
			}
		})

			.then(response => {
				if (loading) App.loading(false);
				response = response['data'];
				if (response['result']) {
					this.table.filter(loading);
				}
				else {
					error_handle(response);
				}
			})

			.catch((error) => {
				if (loading) App.loading(false);
				error_handle(error)
				return false;
			})
	}


}

export default UsersView
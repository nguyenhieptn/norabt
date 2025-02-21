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

import Testnet_account from '../../model/admin/Testnet_account'
import TestnetTradeList from '../../components/admin/TestnetTradeList'
import AccountBalanceChart from '../../components/admin/AccountBalanceChart'
import FuncClone from '../../components/table/FuncClone'

class Testnet_accountView extends Component {

	constructor(props) {
		super(props);

		this.testnet_account_struct = {};
		this.testnet_account_struct[STRUCT_FILTERS] = {}
		this.testnet_account_struct[STRUCT_COLUMNS] = {

			[TESTNET_ACCOUNT_ID]: {
				[COL_NAME]: lang(TESTNET_ACCOUNT_ID),
				[COL_SORT]: true,
				[COL_STYLE] : {textAlign : 'center'}

			},
			[TESTNET_ACCOUNT_NAME]: {
				[COL_NAME]: lang(TESTNET_ACCOUNT_NAME),
				[COL_SORT]: true,
				[COL_STYLE]: { maxWidth: 'unset' },

			},

			'testnet_start': {
				[COL_NAME]: lang('Service'),
				[COL_DECORATOR_IN]: data => {
					return data ? <div style={{ color: '#00e209', fontWeight: 'bold', textAlign: 'center' }}>Running</div> : <div style={{ color: 'red', fontWeight: 'bold', textAlign: 'center' }}>Stopped</div>
				}
			},

			[TESTNET_ACCOUNT_BALANCE]: {
				[COL_NAME]: lang(TESTNET_ACCOUNT_BALANCE),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => data != null ? data.toFixed(3) + ' USDT' : '',
				[COL_STYLE] : {textAlign : 'center'}
			},

			[TESTNET_ACCOUNT_RESERVE]: {
				[COL_NAME]: lang(TESTNET_ACCOUNT_RESERVE),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => data != null ? data + ' %' : '',
				[COL_STYLE] : {textAlign : 'center'}

			},

			[TESTNET_ACCOUNT_COMPOUND]: {
				[COL_NAME]: lang(TESTNET_ACCOUNT_COMPOUND),
				[COL_SORT]: true,
				[COL_STYLE] : {textAlign : 'center'}

			},

			[TESTNET_ACCOUNT_MARGIN_TYPE]: {
				[COL_NAME]: lang(TESTNET_ACCOUNT_MARGIN_TYPE),
				[COL_SORT]: false,
				[COL_STYLE] : {textAlign : 'center'}
			},

			
			[TESTNET_ACCOUNT_RUNTIME]: {
				[COL_NAME]: lang(TESTNET_ACCOUNT_RUNTIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => Math.round(data) + ' ms',
				[COL_STYLE] : {textAlign : 'center'}

			},
			[TESTNET_ACCOUNT_TELE_BOT]: {
				[COL_NAME]: lang(TESTNET_ACCOUNT_TELE_BOT),
				[COL_SORT]: true,
				// [COL_DECORATOR_IN]: data => Math.round(data) + ' ms',
				[COL_STYLE] : {textAlign : 'center'}

			},
			[TESTNET_ACCOUNT_TELE_GROUP_NOTICE]: {
				[COL_NAME]: lang(TESTNET_ACCOUNT_TELE_GROUP_NOTICE),
				[COL_SORT]: true,
				// [COL_DECORATOR_IN]: data => Math.round(data) + ' ms',
				[COL_STYLE] : {textAlign : 'center'}

			},
			[TESTNET_ACCOUNT_TELE_GROUP_SUMMARY]: {
				[COL_NAME]: lang(TESTNET_ACCOUNT_TELE_GROUP_SUMMARY),
				[COL_SORT]: true,
				// [COL_DECORATOR_IN]: data => Math.round(data) + ' ms',
				[COL_STYLE] : {textAlign : 'center'}

			},
			[TESTNET_ACCOUNT_TELE_GROUP_ERROR]: {
				[COL_NAME]: lang(TESTNET_ACCOUNT_TELE_GROUP_ERROR),
				[COL_SORT]: true,
				// [COL_DECORATOR_IN]: data => Math.round(data) + ' ms',
				[COL_STYLE] : {textAlign : 'center'}

			},

			[TESTNET_ACCOUNT_USER]: {
				[COL_NAME]: lang(TESTNET_ACCOUNT_USER),
				[COL_SORT]: false,

			},
			[TESTNET_ACCOUNT_NOTE]: {
				[COL_NAME]: lang(TESTNET_ACCOUNT_NOTE),
				[COL_SORT]: false,

			},



		}
		this.testnet_account_struct[STRUCT_FILTERS] = {

			[TESTNET_ACCOUNT_ID]: {
				[FILTER_NAME]: lang(TESTNET_ACCOUNT_ID),
				[FILTER_TYPE]: 'text',
			},
			[TESTNET_ACCOUNT_NAME]: {
				[FILTER_NAME]: lang(TESTNET_ACCOUNT_NAME),
				[FILTER_TYPE]: 'text',
			},

			[TESTNET_ACCOUNT_COMPOUND]: {
				[FILTER_NAME]: lang(TESTNET_ACCOUNT_COMPOUND),
				[FILTER_TYPE]: 'select',
			},
			[TESTNET_ACCOUNT_MARGIN_TYPE]: {
				[FILTER_NAME]: lang(TESTNET_ACCOUNT_MARGIN_TYPE),
				[FILTER_TYPE]: 'select',
			},
			[TESTNET_ACCOUNT_TELE_BOT]: {
				[FILTER_NAME]: lang(TESTNET_ACCOUNT_TELE_BOT),
				[FILTER_TYPE]: 'select',
			},
			[TESTNET_ACCOUNT_TELE_GROUP_NOTICE]: {
				[FILTER_NAME]: lang(TESTNET_ACCOUNT_TELE_GROUP_NOTICE),
				[FILTER_TYPE]: 'select',
			},
			[TESTNET_ACCOUNT_TELE_GROUP_SUMMARY]: {
				[FILTER_NAME]: lang(TESTNET_ACCOUNT_TELE_GROUP_SUMMARY),
				[FILTER_TYPE]: 'select',
			},
			[TESTNET_ACCOUNT_TELE_GROUP_ERROR]: {
				[FILTER_NAME]: lang(TESTNET_ACCOUNT_TELE_GROUP_ERROR),
				[FILTER_TYPE]: 'select',
			},
			[TESTNET_ACCOUNT_USER]: {
				[FILTER_NAME]: lang(TESTNET_ACCOUNT_USER),
				[FILTER_TYPE]: 'select',
			},


		}

		this.testnet_account_struct[STRUCT_EDIT] = {

			[TESTNET_ACCOUNT_NAME]: {
				[EDIT_NAME]: lang(TESTNET_ACCOUNT_NAME),
				[EDIT_TYPE]: 'text',

			},
			[TESTNET_ACCOUNT_BALANCE]: {
				[EDIT_NAME]: lang(TESTNET_ACCOUNT_BALANCE),
				[EDIT_TYPE]: 'money',

			},
			[TESTNET_ACCOUNT_RESERVE]: {
				[EDIT_NAME]: lang(TESTNET_ACCOUNT_RESERVE),
				[EDIT_TYPE]: 'number',

			},
			[TESTNET_ACCOUNT_COMPOUND]: {
				[EDIT_NAME]: lang(TESTNET_ACCOUNT_COMPOUND),
				[EDIT_TYPE]: 'select',

			},
			[TESTNET_ACCOUNT_MARGIN_TYPE]: {
				[EDIT_NAME]: lang(TESTNET_ACCOUNT_MARGIN_TYPE),
				[EDIT_TYPE]: 'select',
				[EDIT_DEFAULT]: 'ISOLATE'

			},
			[TESTNET_ACCOUNT_NOTE]: {
				[EDIT_NAME]: lang(TESTNET_ACCOUNT_NOTE),
				[EDIT_TYPE]: 'textarea',

			},

			[TESTNET_ACCOUNT_TELE_BOT]: {
				[EDIT_NAME]: lang(TESTNET_ACCOUNT_TELE_BOT),
				[EDIT_TYPE]: 'select',

			},
			[TESTNET_ACCOUNT_TELE_GROUP_NOTICE]: {
				[EDIT_NAME]: lang(TESTNET_ACCOUNT_TELE_GROUP_NOTICE),
				[EDIT_TYPE]: 'select',

			},
			[TESTNET_ACCOUNT_TELE_GROUP_SUMMARY]: {
				[EDIT_NAME]: lang(TESTNET_ACCOUNT_TELE_GROUP_SUMMARY),
				[EDIT_TYPE]: 'select',

			},
			[TESTNET_ACCOUNT_TELE_GROUP_ERROR]: {
				[EDIT_NAME]: lang(TESTNET_ACCOUNT_TELE_GROUP_ERROR),
				[EDIT_TYPE]: 'select',

			},

			[TESTNET_ACCOUNT_USER]: {
				[EDIT_NAME]: lang(TESTNET_ACCOUNT_USER),
				[EDIT_TYPE]: 'select',
			},


		}

		this.testnet_account_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<div className='button btn btn-danger' onClick={() => {
						var model = new Testnet_account()
						model.cleanData(rowData[TESTNET_ACCOUNT_ID])
					}} style={{ fontSize: 12 }}>Clean</div>
					<FuncEditRow rowData={rowData}><div className='button btn btn-primary' style={{ fontSize: 12 }}>Edit</div></FuncEditRow>
					<div className='button btn btn-warning' onClick={() => {
						this.testnetTradeList.setAccount(rowData);
						this.testnetTradeList.modal();
					}} style={{ fontSize: 12 }}>Trades</div>
					<div className='button btn btn-info' style={{ fontSize: 10 }} onClick={() => {
						this.accountBlanceChart.modal();
						this.accountBlanceChart.loadData(rowData);
					}}>Balance</div>
					<div className='button btn btn-primary btn-sm' onClick={() => {
						this.startEventService(rowData[TESTNET_ACCOUNT_ID]);
					}} style={{ fontSize: 12, marginRight: 0 }}>Restart</div>
					
				</div>
			}
		};

		this.model = new Testnet_account()
		this.testnet_account_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: TESTNET_ACCOUNT_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionTestnet_accountView(),
			[DATA_KEY]: [TESTNET_ACCOUNT_ID],
			[DATA_SORT]: { [TESTNET_ACCOUNT_ID]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: this.model

		};


	}

	permissionTestnet_accountView() {
		return Object.assign(
			...Object.keys(this.testnet_account_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.testnet_account_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
			{ [TESTNET_ACCOUNT_USER]: App.user[AUTHEN_GROUP] == 0 ? 'Write' : 'Read' }
		)
	}

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.testnet_account_struct} autoload={true}>
					<FuncBar
						left={<>
							<FuncHideCol />
							<div className='button btn btn-primary btn-sm' onClick={() => { this.startEventServices() }} style={{ fontSize: 12, marginRight: 0 }}>Restart Testnet</div>
							<div className='button btn btn-danger btn-sm' onClick={() => { this.stopEventServices() }} style={{ fontSize: 12, marginRight: 0 }}>Stop Testnet</div>
						</>}
						right={<><FuncAdd />
						<FuncClone onClick={()=>{this.cloneAccount()}}></FuncClone>
						<FuncDel /><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-striped table-resizable'></MainTable>
					<Pagination></Pagination>

				</Table>

				<TestnetTradeList ref={c => this.testnetTradeList = c}></TestnetTradeList>

				<AccountBalanceChart ref={c => this.accountBlanceChart = c}></AccountBalanceChart>

			</div>
		);
	}


	cloneAccount(){
		var dataSelect = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];
		var wl = [];
		for (let i in dataSelect) {
			wl.push(dataSelect[i][TESTNET_ACCOUNT_ID]);
		}

		if (wl.length == 0) {
			showLog('Please select a account');
			return;
		}

		this.model.cloneData(wl[0]).then(res => {
			if(res['result']){
				this.table.filter()
			}
		})

	}


	async startEventServices() {

		var dataSelect = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];
		var wl = [];
		for (let i in dataSelect) {
			wl.push(dataSelect[i][TESTNET_ACCOUNT_ID]);
		}

		if (wl.length == 0) {
			showLog('Please select a account');
			return;
		}

		var confirm = await makeQuestion('Do you want to Start/Restart Testnet service: ' + wl.length + ' account ?');
		if (!confirm) return;

		for (let i in wl) {
			await this.startEventService(wl[i]);
		}
	}


	startEventService(account) {

		App.loading(true)
		return axios.request({
			url: `/admin/testnet_account/restartTrading`,
			method: 'POST',
			data: {
				account: account
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


	async stopEventServices() {

		var dataSelect = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];
		var wl = [];
		for (let i in dataSelect) {
			wl.push(dataSelect[i][TESTNET_ACCOUNT_ID]);
		}

		if (wl.length == 0) {
			showLog('Please select a account');
			return;
		}

		var confirm = await makeQuestion('Do you want to Stop Testnet service: ' + wl.length + ' account?');
		if (!confirm) return;

		for (let i in wl) {
			await this.stopEventService(wl[i]);

		}
	}

	stopEventService(account) {
		App.loading(true)
		return axios.request({
			url: `/admin/testnet_account/stopTrading`,
			method: 'POST',
			data: {
				account: account
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

export default Testnet_accountView
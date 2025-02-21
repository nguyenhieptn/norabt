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
import FuncEdit from '../../components/table/FuncEdit'

import Trades from '../../model/admin/Trades'
import Watchlist from '../../model/admin/Watchlist'
class TradesView extends Component {

	constructor(props) {
		super(props);

		this.trades_struct = {};
		this.trades_struct[STRUCT_FILTERS] = {}
		this.trades_struct[STRUCT_COLUMNS] = {

			[TRADE_ACCOUNT]: {
				[COL_NAME]: lang(TRADE_ACCOUNT),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => {
					return <b >{this.table.mapping[TRADE_ACCOUNT] && this.table.mapping[TRADE_ACCOUNT][data]}</b>
				}


			},
			[TRADE_SYMBOL]: {
				[COL_NAME]: lang(TRADE_SYMBOL),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => {
					return <b >	<img style={{ width: '20px', height: '20px', marginRight: '10px' }} src={this.watchlistIcon[data]}></img>{data}</b>
				}

			},
			[TRADE_PRIORITY]: {
				[COL_NAME]: lang(TRADE_PRIORITY),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => {
					return <b >{data}</b>
				}

			},
			'isTrading': {
				[COL_NAME]: lang('Position'),
				[COL_DECORATOR_IN]: data => {
					return data ? <div style={{ color: 'red', fontWeight: 'bold', textAlign: 'center' }}>Pending</div> : ''
				}
			},
			'update_service': {
				[COL_NAME]: lang('Binance'),
				[COL_DECORATOR_IN]: data => {
					return data ? <div style={{ color: '#00e209', fontWeight: 'bold', textAlign: 'center' }}>Connected</div> : <div style={{ color: 'red', fontWeight: 'bold', textAlign: 'center' }}>Disconnected</div>
				}
			},
			'trade_service': {
				[COL_NAME]: lang('Trading'),
				[COL_DECORATOR_IN]: data => {
					return data ? <div style={{ color: '#00e209', fontWeight: 'bold', textAlign: 'center' }}>Trading</div> : <div style={{ color: 'red', fontWeight: 'bold', textAlign: 'center' }}>Stopped</div>
				}
			},
			[TRADE_BUDGET]: {
				[COL_NAME]: lang(TRADE_BUDGET),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' }

			},
			[TRADE_ACTION_BUDGET]: {
				[COL_NAME]: lang(TRADE_ACTION_BUDGET),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' }

			},
			[TRADE_MONEY]: {
				[COL_NAME]: lang(TRADE_MONEY),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' }

			},
			[TRADE_COMPOUND]: {
				[COL_NAME]: lang(TRADE_COMPOUND),
				[COL_SORT]: true,
			},
			[TRADE_STRATEGY]: {
				[COL_NAME]: lang(TRADE_STRATEGY),
				[COL_SORT]: true,
				[COL_STYLE]: { whiteSpace: 'nowrap', textAlign: 'center' }

			},
			[TRADE_SIDE]: {
				[COL_NAME]: lang(TRADE_SIDE),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' }

			},
			// [TRADE_PARAM]: {
			// 	[COL_NAME]: lang(TRADE_PARAM),
			// 	[COL_SORT]: false,
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
			[TRADE_START_TIME]: {
				[COL_NAME]: lang(TRADE_START_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap', textAlign: 'center' }
			},
			[TRADE_STOP_TIME]: {
				[COL_NAME]: lang(TRADE_STOP_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap', textAlign: 'center' }
			},



		}
		this.trades_struct[STRUCT_FILTERS] = {

			[TRADE_ACCOUNT]: {
				[FILTER_NAME]: lang(TRADE_ACCOUNT),
				[FILTER_TYPE]: 'select',
			},
			[TRADE_SYMBOL]: {
				[FILTER_NAME]: lang(TRADE_SYMBOL),
				[FILTER_TYPE]: 'select',
			},
			// [TRADE_BUDGET]: {
			// 	[FILTER_NAME]: lang(TRADE_BUDGET),
			// 	[FILTER_TYPE]: 'text',
			// },
			// [TRADE_ACTION_BUDGET]: {
			// 	[FILTER_NAME]: lang(TRADE_ACTION_BUDGET),
			// 	[FILTER_TYPE]: 'text',
			// },
			// [TRADE_MONEY]: {
			// 	[FILTER_NAME]: lang(TRADE_MONEY),
			// 	[FILTER_TYPE]: 'text',
			// },
			// [TRADE_PROFIT]: {
			// 	[FILTER_NAME]: lang(TRADE_PROFIT),
			// 	[FILTER_TYPE]: 'text',
			// },
			// [TRADE_PARAM]: {
			// 	[FILTER_NAME]: lang(TRADE_PARAM),
			// 	[FILTER_TYPE]: 'select',
			// },
			[TRADE_STRATEGY]: {
				[FILTER_NAME]: lang(TRADE_STRATEGY),
				[FILTER_TYPE]: 'select',
			},
			[TRADE_SIDE]: {
				[FILTER_NAME]: lang(TRADE_SIDE),
				[FILTER_TYPE]: 'select',
			},


		}

		this.trades_struct[STRUCT_EDIT] = {

			[TRADE_ACCOUNT]: {
				[EDIT_NAME]: lang(TRADE_ACCOUNT),
				[EDIT_TYPE]: 'select',

			},
			[TRADE_SYMBOL]: {
				[EDIT_NAME]: lang(TRADE_SYMBOL),
				[EDIT_TYPE]: 'select',

			},
			[TRADE_BUDGET]: {
				[EDIT_NAME]: lang(TRADE_BUDGET),
				[EDIT_TYPE]: 'text',

			},
			
			[TRADE_ACTION_BUDGET]: {
				[EDIT_NAME]: lang(TRADE_ACTION_BUDGET),
				[EDIT_TYPE]: 'text',

			},

			[TRADE_COMPOUND]: {
				[EDIT_NAME]: lang(TRADE_COMPOUND),
				[EDIT_TYPE]: 'select',
			},

			[TRADE_STRATEGY]: {
				[EDIT_NAME]: lang(TRADE_STRATEGY),
				[EDIT_TYPE]: 'select',

			},
			[TRADE_SIDE]: {
				[EDIT_NAME]: lang(TRADE_SIDE),
				[EDIT_TYPE]: 'select',

			},

			[TRADE_PRIORITY]: {
				[EDIT_NAME]: lang(TRADE_PRIORITY),
				[EDIT_TYPE]: 'number',
			},

			[TRADE_PARAM]: {
				[EDIT_NAME]: lang(TRADE_PARAM),
				[EDIT_TYPE]: 'textarea',

			},


		}

		this.trades_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData}><div className='button btn-sm btn-primary' style={{ fontSize: 10 }}>Edit</div></FuncEditRow>
					<div className='button btn-sm btn-danger' style={{ fontSize: 10 }} onClick={() => {
						makeQuestion('Do you want to Stop Trading: ' + rowData[TRADE_SYMBOL] + '?').then(res => {
							if (res) {
								this.stopService(rowData[TRADE_SYMBOL], rowData[TRADE_ACCOUNT]);
							}
						})
					}}>Stop</div>

					<div className='button btn-sm btn-primary' style={{ fontSize: 10 }} onClick={() => {
						makeQuestion('Do you want to Start/Restart Trading: ' + rowData[TRADE_SYMBOL] + '?').then(res => {
							if (res) {
								this.startService(rowData[TRADE_SYMBOL], rowData[TRADE_ACCOUNT], true);
							}
						})
					}}>Start/Restart</div>

				</div>
			}
		};
		this.trades_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: TRADES_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionTradesView(),
			[DATA_KEY]: [TRADE_ID, TRADE_ACCOUNT, TRADE_SYMBOL],
			[DATA_SORT]: { [TRADE_PRIORITY]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Trades()

		};

		this.watchlistIcon = {};


	}

	getIcon() {
		var watchlist = new Watchlist();

		return watchlist.getIcon();

	}

	permissionTradesView() {
		return Object.assign(
			...Object.keys(this.trades_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.trades_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.trades_struct} autoload={false}>
					<FuncBar
						left={<>
							<FuncHideCol />
							<div className='button btn btn-primary btn-sm' onClick={() => { this.startServices() }} style={{ fontSize: 12 }}>Restart Trade</div>
							<div className='button btn btn-danger btn-sm' onClick={() => { this.stopServices() }} style={{ fontSize: 12 }}>Stop Trade</div>
						</>}
						right={<><FuncAdd /><FuncDel /><FuncEdit ref={c => this.multiEdit = c} extraFunction={
							<div className='button btn btn-warning' onClick={() => {
								this.multiEdit.onClickHandle();
								this.startServices();
							}}>Save and Restart</div>
						}></FuncEdit><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-striped table-resizable'></MainTable>
					<Pagination></Pagination>

				</Table>


			</div>
		);
	}


	componentDidMount() {
		this.table.map();
		this.getIcon().then((res) => {
			this.watchlistIcon = res;
			this.table.setFilter({
				"trade_account": {
					"logic": "and",
					"data": {
						"=": App.accountSelector.selected()
					}
				}
	
			}
			)
	
		})
	

		if (App.accountSelector) {
			App.accountSelector.register('trade_view', () => {
				this.table.map();
				this.table.setFilter({
					"trade_account": {
						"logic": "and",
						"data": {
							"=": App.accountSelector.selected()
						}
					}
				});
				this.table.filter();
			});
		}
	}

	componentWillUnmount() {
		App.accountSelector.unregister('trade_view')
	}


	async startServices() {

		var dataSelect = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];
		var wl = [];
		for (let i in dataSelect) {
			wl.push(dataSelect[i][TRADE_SYMBOL]);
		}

		if (wl.length == 0) {
			showLog('Please select a symbol');
			return;
		}

		var confirm = await makeQuestion('Do you want to Start/Restart ' + wl.length + ' Symbols:' + wl.join(', ') + '?');
		if (!confirm) return;
		App.loading(true)
		for (let i in dataSelect) {
			await this.startService(dataSelect[i][TRADE_SYMBOL], dataSelect[i][TRADE_ACCOUNT], false);

		}
		App.loading(false)
	}

	startService(symbol, id, loading = true) {
		if (loading) App.loading(true)
		return axios.request({
			url: `/admin/trades/startService`,
			method: 'POST',
			data: {
				id, symbol
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

	async stopServices() {


		var dataSelect = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];
		var wl = [];
		for (let i in dataSelect) {
			wl.push(dataSelect[i][TRADE_SYMBOL]);
		}

		if (wl.length == 0) {
			showLog('Please select a symbol');
			return;
		}

		var confirm = await makeQuestion('Do you want to Stop Trading ' + wl.length + ' Symbols:' + wl.join(', ') + '?');
		if (!confirm) return;
		App.loading(true)
		for (let i in dataSelect) {
			await this.stopService(dataSelect[i][TRADE_SYMBOL], dataSelect[i][TRADE_ACCOUNT], false);

		}
		App.loading(false);

	}


	stopService(symbol, id, loading = true) {
		if (loading) App.loading(true)
		return axios.request({
			url: `/admin/trades/stopService`,
			method: 'POST',
			data: {
				id, symbol
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

export default TradesView
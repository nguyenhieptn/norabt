import React, { Component } from 'react'
import Table from '../../components/table/Table'
import MainTable from '../../components/table/MainTable'
import Pagination from '../../components/table/Pagination'
import FuncBar from '../../components/table/FuncBar'

import FuncEditRow from '../../components/table/FuncEditRow'
import FuncAdd from '../../components/table/FuncAdd'
import FuncEdit from '../../components/table/FuncEdit'
import FuncHideCol from '../../components/table/FuncHideCol'
import FuncDel from '../../components/table/FuncDel'
import FuncClear from '../../components/table/FuncClear'
import FuncRefresh from '../../components/table/FuncRefresh'
import FuncExport from '../../components/table/FuncExport'

import Testnet_campaign from '../../model/admin/Testnet_campaign'
import FuncConfigModal from '../../components/table/FuncConfigModal'
import Watchlist from '../../model/admin/Watchlist'
import Coinmarket from '../../model/admin/Coinmarket'
class Testnet_campaignView extends Component {

	constructor(props) {
		super(props);

		this.testnet_campaign_struct = {};
		this.testnet_campaign_struct[STRUCT_FILTERS] = {}
		this.testnet_campaign_struct[STRUCT_COLUMNS] = {

			[TESTNET_NAME]: {
				[COL_NAME]: lang(TESTNET_NAME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {

					var rowData = data[rowId];
					var data = rowData[colId];
					return <div style={{ cursor: 'pointer' }} onClick={() => {
						window.open(App.link('/admin/testnetchart/view?campaign=' + rowData[TESTNET_ID] + '&symbol=' + rowData[TESTNET_SYMBOL]), '_blank');
					}}><b>{data}</b></div>
				}

			},
			[TESTNET_SYMBOL]: {
				[COL_NAME]: lang(TESTNET_SYMBOL),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {
					var rankData = (data == '1000SHIBUSDT' ? 'SHIBUSDT' : data);
					return <b>
							<img style={{ width: '20px', height: '20px', marginRight: '10px' }} src={this.watchlistIcon[data]}></img>
						{data}
						<span style={{ color: 'blue', fontWeight: 'normal' }}> [{get(this.coinMarketData[rankData], '')}]</span>
						</b>
				}


			},

			[TESTNET_ACTIVE]: {
				[COL_NAME]: lang(TESTNET_ACTIVE),
				[COL_SORT]: true,
			},

			[TESTNET_ACCOUNT]: {
				[COL_NAME]: lang(TESTNET_ACCOUNT),
				[COL_SORT]: true,
			},

			[TESTNET_PRIORITY]: {
				[COL_NAME]: lang(TESTNET_PRIORITY),
				[COL_SORT]: true,
			},

			[TESTNET_STRATEGY]: {
				[COL_NAME]: lang(TESTNET_STRATEGY),
				[COL_SORT]: true,

			},
			[TESTNET_SIDE]: {
				[COL_NAME]: lang(TESTNET_SIDE),
				[COL_SORT]: true,

			},
			'testnet_start': {
				[COL_NAME]: lang('Service'),
				[COL_DECORATOR_IN]: data => {
					return data ? <div style={{ color: '#00e209', fontWeight: 'bold', textAlign: 'center' }}>Running</div> : <div style={{ color: 'red', fontWeight: 'bold', textAlign: 'center' }}>Stopped</div>
				}
			},

			
			[TESTNET_BUDGET]: {
				[COL_NAME]: lang(TESTNET_BUDGET),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => data != null ? data.toFixed(3) + ' USDT' : '',

			},

			[TESTNET_ACTIVE_BUDGET]: {
				[COL_NAME]: lang(TESTNET_ACTIVE_BUDGET),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => data != null ? data + ' %' : '',

			},

			[TESTNET_MONEY]: {
				[COL_NAME]: lang(TESTNET_MONEY),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => data != null ? data + ' USDT' : '',

			},

			// [TESTNET_PROFIT]: {
			// 	[COL_NAME]: lang(TESTNET_PROFIT),
			// 	[COL_SORT]: true,
			// 	[COL_DECORATOR_IN]: data => data != null ? data.toFixed(3) + ' USDT' : ''

			// },

			[TESTNET_COMPOUND]: {
				[COL_NAME]: lang(TESTNET_COMPOUND),
				[COL_SORT]: true,

			},

			[TESTNET_START_TIME]: {
				[COL_NAME]: lang(TESTNET_START_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},
			[TESTNET_STOP_TIME]: {
				[COL_NAME]: lang(TESTNET_STOP_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},

			[TESTNET_NOTE]: {
				[COL_NAME]: lang(TESTNET_NOTE),
				[COL_SORT]: false,

			},
			[TESTNET_TELE_BOT]: {
				[COL_NAME]: lang(TESTNET_TELE_BOT),
				[COL_SORT]: false,

			},
			[TESTNET_TELE_GR_NOTICE]: {
				[COL_NAME]: lang(TESTNET_TELE_GR_NOTICE),
				[COL_SORT]: false,

			},

			[TESTNET_TELE_GR_SUMMARY]: {
				[COL_NAME]: lang(TESTNET_TELE_GR_SUMMARY),
				[COL_SORT]: false,

			},
			[TESTNET_TELE_GR_ERROR]: {
				[COL_NAME]: lang(TESTNET_TELE_GR_ERROR),
				[COL_SORT]: false,

			},

			[TESTNET_TELE_GR_SUMMARY]: {
				[COL_NAME]: lang(TESTNET_TELE_GR_SUMMARY),
				[COL_SORT]: false,

			},
			

			[TESTNET_PARAM]: {
				[COL_NAME]: lang(TESTNET_PARAM),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => {
					var configs = JSON.parse(data);
					if (isset(configs)) {
						configs = Object.keys(configs).map((key) => {
							return <div key={key} className="box_flex">
								<div className="box_line" style={{ flex: 2 }}>{lang(key)}</div>
								<div>:&nbsp;</div>
								<div title={configs[key]} className="box_line" style={{ flex: 1 }}>{configs[key]}</div>
							</div>
						});
					} else {
						configs = '';
					}
					return <div>{configs}</div>
				}

			},



		}
		this.testnet_campaign_struct[STRUCT_FILTERS] = {

			[TESTNET_ID]: {
				[FILTER_NAME]: lang(TESTNET_ID),
				[FILTER_TYPE]: 'text',
			},

			[TESTNET_NAME]: {
				[FILTER_NAME]: lang(TESTNET_NAME),
				[FILTER_TYPE]: 'text',
			},

			[TESTNET_SYMBOL]: {
				[FILTER_NAME]: lang(TESTNET_SYMBOL),
				[FILTER_TYPE]: 'select',
			},

			[TESTNET_ACCOUNT]: {
				[FILTER_NAME]: lang(TESTNET_ACCOUNT),
				[FILTER_TYPE]: 'select',
			},

			[TESTNET_STRATEGY]: {
				[FILTER_NAME]: lang(TESTNET_STRATEGY),
				[FILTER_TYPE]: 'select',
			},

			[TESTNET_SIDE]: {
				[FILTER_NAME]: lang(TESTNET_SIDE),
				[FILTER_TYPE]: 'select',
			},

			[TESTNET_ACTIVE]: {
				[FILTER_NAME]: lang(TESTNET_ACTIVE),
				[FILTER_TYPE]: 'select',
			},


		}

		this.testnet_campaign_struct[STRUCT_EDIT] = {

			[TESTNET_NAME]: {
				[EDIT_NAME]: lang(TESTNET_NAME),
				[EDIT_TYPE]: 'text',
			},

			[TESTNET_SYMBOL]: {
				[EDIT_NAME]: lang(TESTNET_SYMBOL),
				[EDIT_TYPE]: 'select',
			},

			[TESTNET_ACTIVE]: {
				[EDIT_NAME]: lang(TESTNET_ACTIVE),
				[EDIT_TYPE]: 'select',
				[EDIT_DEFAULT]: 1
			},

			[TESTNET_ACCOUNT]: {
				[EDIT_NAME]: lang(TESTNET_ACCOUNT),
				[EDIT_TYPE]: 'select',
			},

			[TESTNET_STRATEGY]: {
				[EDIT_NAME]: lang(TESTNET_STRATEGY),
				[EDIT_TYPE]: 'select',
			},

			[TESTNET_PRIORITY]: {
				[EDIT_NAME]: lang(TESTNET_PRIORITY),
				[EDIT_TYPE]: 'number',

			},

			[TESTNET_SIDE]: {
				[EDIT_NAME]: lang(TESTNET_SIDE),
				[EDIT_TYPE]: 'select',

			},
			[TESTNET_PARAM]: {
				[EDIT_NAME]: lang(TESTNET_PARAM),
				[EDIT_TYPE]: 'textarea',

			},
			[TESTNET_BUDGET]: {
				[EDIT_NAME]: lang(TESTNET_BUDGET),
				[EDIT_TYPE]: 'Number',
				[EDIT_DEFAULT]: 100,

			},
			[TESTNET_ACTIVE_BUDGET]: {
				[EDIT_NAME]: lang(TESTNET_ACTIVE_BUDGET),
				[EDIT_TYPE]: 'Number',
				[EDIT_DEFAULT]: 100,

			},

			[TESTNET_MONEY]: {
				[EDIT_NAME]: lang(TESTNET_MONEY),
				[EDIT_TYPE]: 'Number',
				[EDIT_DEFAULT]: 100,

			},

			[TESTNET_COMPOUND]: {
				[EDIT_NAME]: lang(TESTNET_COMPOUND),
				[EDIT_TYPE]: 'select',
				[EDIT_DEFAULT]: 0,

			},
			
			[TESTNET_NOTE]: {
				[EDIT_NAME]: lang(TESTNET_NOTE),
				[EDIT_TYPE]: 'textarea',

			},
			[TESTNET_TELE_BOT]: {
				[EDIT_NAME]: lang(TESTNET_TELE_BOT),
				[EDIT_TYPE]: 'text',

			},
			[TESTNET_TELE_GR_NOTICE]: {
				[EDIT_NAME]: lang(TESTNET_TELE_GR_NOTICE),
				[EDIT_TYPE]: 'text',

			},
			[TESTNET_TELE_GR_ERROR]: {
				[EDIT_NAME]: lang(TESTNET_TELE_GR_ERROR),
				[EDIT_TYPE]: 'text',

			},
			[TESTNET_TELE_GR_SUMMARY]: {
				[EDIT_NAME]: lang(TESTNET_TELE_GR_SUMMARY),
				[EDIT_TYPE]: 'textarea',
				[EDIT_DES]: 'Each group seprated by (,)'

			},


		}

		this.testnet_campaign_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData}><div className='button btn btn-warning btn-sm' style={{ fontSize: 12, marginRight: 0 }}>Edit</div></FuncEditRow>
					<div className='button btn btn-warning btn-sm' onClick={() => {
						this.configModal.loadData(rowData);
						this.configModal.modal();
					}} style={{ fontSize: 12, marginRight: 0 }}>Parmas</div>

					<div className='button btn btn-primary btn-sm' onClick={() => {
						this.startEventService(rowData[TESTNET_ID]);
					}} style={{ fontSize: 12, marginRight: 0 }}>Restart</div>
				</div>
			}
		};
		this.testnet_campaign_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: TESTNET_CAMPAIGN_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionTestnet_campaignView(),
			[DATA_KEY]: [TESTNET_ID],
			[DATA_SORT]: { [TESTNET_ID]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Testnet_campaign()

		};
		this.watchlistIcon = {};
		this.coinMarketData = {}


	}

	permissionTestnet_campaignView() {
		return Object.assign(
			...Object.keys(this.testnet_campaign_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.testnet_campaign_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.testnet_campaign_struct} autoload={false} addRow={this.addRow.bind(this)}>
					<FuncBar
						left={<>
							<FuncHideCol />
							<div className='button btn btn-primary btn-sm' onClick={() => { this.startEventServices() }} style={{ fontSize: 12, marginRight: 0 }}>Restart Testnet</div>
							<div className='button btn btn-danger btn-sm' onClick={() => { this.stopEventServices() }} style={{ fontSize: 12, marginRight: 0 }}>Stop Testnet</div>
						</>}
						right={<><FuncAdd /><FuncDel /><FuncEdit ref={c => this.multiEdit = c} extraFunction={
							<div className='button btn btn-warning' onClick={() => {
								this.multiEdit.onClickHandle();
								this.startEventServices();
							}}>Save and Restart</div>
						}></FuncEdit><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-striped table-resizable'></MainTable>
					<Pagination></Pagination>

					<FuncConfigModal ref={c => this.configModal = c} struct={{

						[TESTNET_PARAM_LOG]: {
							[INPUT_NAME]: lang(TESTNET_PARAM_LOG),
							[INPUT_TYPE]: 'select',
							[INPUT_DEFAULT]: 0,
							[INPUT_OPTION]: { 0: 'False', 1: 'True' },
						},
						[TESTNET_PARAM_LOG_ORDER]: {
							[INPUT_NAME]: lang(TESTNET_PARAM_LOG_ORDER),
							[INPUT_TYPE]: 'select',
							[INPUT_DEFAULT]: 0,
							[INPUT_OPTION]: { 0: 'False', 1: 'True' },
						},
					}} column={TESTNET_PARAM}></FuncConfigModal>

				</Table>




			</div>
		);
	}
	getIcon() {
		var watchlist = new Watchlist();
		return watchlist.getIcon();

	}

	getRankCoinMarket(){
		var model = new Coinmarket();

		return model.getRank()
	}

	async componentDidMount() {

		if (App.accountSelectorTestnet) {
			App.accountSelectorTestnet.register('testnet_results_view', () => {
				this.table.setFilter({
					[TESTNET_ACCOUNT]: {
						"logic": "and",
						"data": {
							"=": App.accountSelectorTestnet ? App.accountSelectorTestnet.selected() : ''
						}
					}
				})
				this.table.filter();
			});

			
			
		}

		this.table.map();
		this.coinMarketData = await this.getRankCoinMarket()
		this.getIcon().then((res) => {
			this.watchlistIcon = res;
			this.table.setFilter({
				[TESTNET_ACCOUNT]: {
					"logic": "and",
					"data": {
						"=": App.accountSelectorTestnet ? App.accountSelectorTestnet.selected() : ''
					}
				}
			})
	
		})
	
	}


	addRow(rowData, loading = true) {

		if (rowData[TESTNET_SYMBOL] == 'all') {
			var listOfSymbol = this.table.mapping[TESTNET_SYMBOL];
			var rowDatas = [];
			for (let i in listOfSymbol) {
				if (i != 'all') {
					rowDatas.push({
						...rowData, ...{
							[TESTNET_NAME]: rowData[TESTNET_NAME] + ' - ' + listOfSymbol[i],
							[TESTNET_SYMBOL]: listOfSymbol[i],
						}
					})
				}

			}

			return this.table[STRUCT_TABLE].model.adds(rowDatas, loading, this.table[STRUCT_TABLE][DATA_SPECIAL]).then((res) => {
				if (res) {
					if (res['result']) {
						this.table[STRUCT_TABLE][FLAG_FILTER_CHANGE] = true;
						return res;
					} else {
						error_handle(res);
					}

				}
			})
		} else {
			return this.table[STRUCT_TABLE].model.add(rowData, loading, this.table[STRUCT_TABLE][DATA_SPECIAL]).then((res) => {
				if (res) {
					if (res['result']) {
						this.table[STRUCT_TABLE][FLAG_FILTER_CHANGE] = true;
						return res;
					} else {
						error_handle(res);
					}

				}

			})
		}


	}


	async startEventServices() {

		var dataSelect = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];
		var wl = [];
		for (let i in dataSelect) {
			wl.push(dataSelect[i][TESTNET_ID]);
		}

		if (wl.length == 0) {
			showLog('Please select a campaign');
			return;
		}

		var confirm = await makeQuestion('Do you want to Start/Restart Testnet service: ' + wl.length + ' campaign ?');
		if (!confirm) return;

		for (let i in wl) {
			await this.startEventService(wl[i]);
		}
	}


	startEventService(campaign) {

		App.loading(true)
		return axios.request({
			url: `/admin/testnet_campaign/startEventService`,
			method: 'POST',
			data: {
				campaign: campaign
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
			wl.push(dataSelect[i][TESTNET_ID]);
		}

		if (wl.length == 0) {
			showLog('Please select a campaign');
			return;
		}

		var confirm = await makeQuestion('Do you want to Stop Testnet service: ' + wl.length + ' Campaign?');
		if (!confirm) return;

		for (let i in wl) {
			await this.stopEventService(wl[i]);

		}
	}

	stopEventService(campaign) {
		App.loading(true)
		return axios.request({
			url: `/admin/testnet_campaign/stopEventService`,
			method: 'POST',
			data: {
				campaign: campaign
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

export default Testnet_campaignView
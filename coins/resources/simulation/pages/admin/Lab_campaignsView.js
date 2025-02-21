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

import Lab_campaigns from '../../model/admin/Lab_campaigns'
import FuncConfigModal from '../../components/table/FuncConfigModal'
import { Link } from 'react-router-dom'
import FuncImport from '../../../react/components/table/FuncImport'
import FuncEdit from '../../components/table/FuncEdit'
import Watchlist from '../../model/admin/Lab_watchlist'


import Coinmarket from '../../../react/model/admin/Coinmarket'
class Lab_campaignsView extends Component {

	constructor(props) {
		super(props);

		this.state = {
			strategies: {}
		}

		this.lab_campaigns_struct = {};
		this.lab_campaigns_struct[STRUCT_FILTERS] = {}
		this.lab_campaigns_struct[STRUCT_COLUMNS] = {

			[LAB_CAMPAIGN_NAME]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_NAME),
				[COL_SORT]: true,
				[COL_STYLE]: { maxWidth: 'unset' },
				[COL_DECORATOR_IN]: (colId, rowId, data) => {

					var rowData = data[rowId];
					var data = rowData[colId];
					return <div style={{ cursor: 'pointer' }} onClick={() => {
						window.open(App.link('/admin/chart/view?campaign=' + rowData[LAB_CAMPAIGN_ID] + '&symbol=' + rowData[LAB_CAMPAIGN_SYMBOL]), '_blank');
					}}><b>{data}</b></div>
				}

			},
			[LAB_CAMPAIGN_SYMBOL]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_SYMBOL),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => {
					var rankData = (data == '1000SHIBUSDT' ? 'SHIBUSDT' : data);
					return <span >
						{/* <img style={{ width: '20px', height: '20px', marginRight: '10px' }} src={this.watchlistIcon[data]}></img> */}
						{data}
						<span style={{ color: 'blue', fontWeight: 'normal' }}> [{get(this.coinMarketData[rankData], '')}]</span>

					</span>
				}



			},

			[LAB_CAMPAIGN_SYM_RANK]:{
				[COL_NAME]: lang(LAB_CAMPAIGN_SYM_RANK),
				[COL_SORT]: true,
				
			},
			'lab_sym_start_time': {
				[COL_NAME]: 'Symbol Start Time',
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }

			},
			[LAB_CAMPAIGN_ACCOUNT]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_ACCOUNT),
				[COL_SORT]: true,

			},
			
			[LAB_CAMPAIGN_PRIORITY]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_PRIORITY),
				[COL_SORT]: true,

			},
			
			[LAB_CAMPAIGN_START]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_START),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},
			[LAB_CAMPAIGN_STOP]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_STOP),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},

			[LAB_CAMPAIGN_RUNTIME]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_RUNTIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap', fontWeight:'bold' }
			},

			[LAB_CAMPAIGN_STATUS]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_STATUS),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {

					var rowData = data[rowId];
					var data = rowData[colId];
					var id = rowData[LAB_CAMPAIGN_ID];
					var running = rowData[LAB_CAMPAIGN_RUNNING];
					if (!data) data = '0,0';
					data = data.split(',');
					var total = get(data[0], 0);
					var process = get(data[1], 0);
					var percent = total > 0 ? Math.round(process * 100 / total) : 0;

					return <div className='box_flex' style={{ minWidth: 200 }}>

						<div className="progress" style={{ flexGrow: 1 }}>
							<div className="progress-bar progress-bar-striped active" role="progressbar" style={{ width: `${percent}%` }}>
								{`${process}/${total}`}
							</div>
						</div>

						{running
							? <i className="button fa fa-times-circle" style={{ color: 'red', marginLeft: 5 }} onClick={() => this.killSimulate(id)}></i>
							: <i className="button fa fa-play-circle" style={{ color: 'green', marginLeft: 5 }} onClick={() => this.simulate(id)}></i>
						}


					</div>
				},
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},

			[LAB_CAMPAIGN_RUNNING]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_RUNNING),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => {
					return data == 1 ? <b style={{ color: 'limegreen' }}>Running</b> : <b style={{ color: 'red' }}>Stopped</b>
				}

			},

			[LAB_CAMPAIGN_STRATEGY]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_STRATEGY),
				[COL_SORT]: true,
			},

			[LAB_CAMPAIGN_SIDE]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_SIDE),
				[COL_SORT]: true,
			},
			[LAB_CAMPAIGN_BUDGET]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_BUDGET),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => formatNumber(Number(data).toFixed(3)),
				[COL_SUM]: true
			},
			[LAB_CAMPAIGN_MONEY]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_MONEY),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => formatNumber(Number(data).toFixed(3)),
				[COL_SUM]: true
			},
			[LAB_CAMPAIGN_ACTIVE_BUDGET]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_ACTIVE_BUDGET),
				[COL_SORT]: true,

			},
			// [LAB_CAMPAIGN_RESERVE]: {
			// 	[COL_NAME]: lang(LAB_CAMPAIGN_RESERVE),
			// 	[COL_SORT]: true,
			// 	[COL_DECORATOR_IN]: data => data != null ? data + ' %' : '',

			// },
			[LAB_CAMPAIGN_COMPOUND]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_COMPOUND),
				[COL_SORT]: true,
			},
			// [LAB_CAMPAIGN_PROFIT]: {
			// 	[COL_NAME]: lang(LAB_CAMPAIGN_PROFIT),
			// 	[COL_SORT]: true,
			// 	[COL_DECORATOR_IN]: data => data != null ? data.toFixed(3) + ' USDT' : '',
			// },

			[LAB_CAMPAIGN_PARAMS]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_PARAMS),
				[COL_SORT]: false,
				[COL_DECORATOR_IN]: data => {
					var configs = JSON.parse(data);
					if (isset(configs)) {
						configs = Object.keys(configs).map((key) => {
							return <div key={key} className="box_flex">
								<div className="box_line" style={{ flex: 2 }}>{lang(key)}</div>
								<div>:&nbsp;</div>
								<div className="box_line" style={{ flex: 1 }}>{configs[key]}</div>
							</div>
						});
					} else {
						configs = '';
					}
					return <div>{configs}</div>
				}

			},

			[LAB_CAMPAIGN_LAST]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_LAST),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},
			[LAB_CAMPAIGN_LOG]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_LOG),
				[COL_SORT]: true,
				
			},



		}
		this.lab_campaigns_struct[STRUCT_FILTERS] = {

			[LAB_CAMPAIGN_NAME]: {
				[FILTER_NAME]: lang(LAB_CAMPAIGN_NAME),
				[FILTER_TYPE]: 'text',
			},
			[LAB_CAMPAIGN_SYMBOL]: {
				[FILTER_NAME]: lang(LAB_CAMPAIGN_SYMBOL),
				[FILTER_TYPE]: 'select',
			},
			[LAB_CAMPAIGN_STRATEGY]: {
				[FILTER_NAME]: lang(LAB_CAMPAIGN_STRATEGY),
				[FILTER_TYPE]: 'select',
			},
			[LAB_CAMPAIGN_SIDE]: {
				[FILTER_NAME]: lang(LAB_CAMPAIGN_SIDE),
				[FILTER_TYPE]: 'select',
			},
			[LAB_CAMPAIGN_ACCOUNT]: {
				[FILTER_NAME]: lang(LAB_CAMPAIGN_ACCOUNT),
				[FILTER_TYPE]: 'select_unsort',
			},
			[LAB_CAMPAIGN_RUNNING]: {
				[FILTER_NAME]: lang(LAB_CAMPAIGN_RUNNING),
				[FILTER_TYPE]: 'select',
			},
			[LAB_CAMPAIGN_SYM_RANK]: {
				[FILTER_NAME]: lang(LAB_CAMPAIGN_SYM_RANK),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<='],

			},
			// [LAB_CAMPAIGN_START]: {
			// 	[FILTER_NAME]: lang(LAB_CAMPAIGN_START),
			// 	[FILTER_TYPE]: 'date',
			// },
			// [LAB_CAMPAIGN_STOP]: {
			// 	[FILTER_NAME]: lang(LAB_CAMPAIGN_STOP),
			// 	[FILTER_TYPE]: 'date',
			// },


		}

		this.lab_campaigns_struct[STRUCT_EDIT] = {

			[LAB_CAMPAIGN_NAME]: {
				[EDIT_NAME]: lang(LAB_CAMPAIGN_NAME),
				[EDIT_TYPE]: 'text',

			},
			[LAB_CAMPAIGN_SYMBOL]: {
				[EDIT_NAME]: lang(LAB_CAMPAIGN_SYMBOL),
				[EDIT_TYPE]: 'select',

			},
			[LAB_CAMPAIGN_STRATEGY]: {
				[EDIT_NAME]: lang(LAB_CAMPAIGN_STRATEGY),
				[EDIT_TYPE]: 'select',

			},
			[LAB_CAMPAIGN_SIDE]: {
				[EDIT_NAME]: lang(LAB_CAMPAIGN_SIDE),
				[EDIT_TYPE]: 'select',

			},
			[LAB_CAMPAIGN_ACCOUNT]: {
				[EDIT_NAME]: lang(LAB_CAMPAIGN_ACCOUNT),
				[EDIT_TYPE]: 'Number',

			},

			[LAB_CAMPAIGN_START]: {
				[EDIT_NAME]: lang(LAB_CAMPAIGN_START),
				[EDIT_TYPE]: 'date',

			},
			[LAB_CAMPAIGN_STOP]: {
				[EDIT_NAME]: lang(LAB_CAMPAIGN_STOP),
				[EDIT_TYPE]: 'date',

			},
			[LAB_CAMPAIGN_PARAMS]: {
				[EDIT_NAME]: lang(LAB_CAMPAIGN_PARAMS),
				[EDIT_TYPE]: 'textarea',

			},

			[LAB_CAMPAIGN_BUDGET]: {
				[EDIT_NAME]: lang(LAB_CAMPAIGN_BUDGET),
				[EDIT_TYPE]: 'money',
				[EDIT_DEFAULT]: 1000,

			},
			[LAB_CAMPAIGN_RESERVE]: {
				[EDIT_NAME]: lang(LAB_CAMPAIGN_RESERVE),
				[EDIT_TYPE]: 'number',
				[EDIT_DEFAULT]: 20,

			},

			[LAB_CAMPAIGN_ACTIVE_BUDGET]: {
				[EDIT_NAME]: lang(LAB_CAMPAIGN_ACTIVE_BUDGET),
				[EDIT_TYPE]: 'text',

			},

			[LAB_CAMPAIGN_MONEY]: {
				[EDIT_NAME]: lang(LAB_CAMPAIGN_MONEY),
				[EDIT_TYPE]: 'money',
				[EDIT_DEFAULT]: 1000,
			},

			[LAB_CAMPAIGN_PRIORITY]: {
				[EDIT_NAME]: lang(LAB_CAMPAIGN_PRIORITY),
				[EDIT_TYPE]: 'Number',

			},

			[LAB_CAMPAIGN_COMPOUND]: {
				[EDIT_NAME]: lang(LAB_CAMPAIGN_COMPOUND),
				[EDIT_TYPE]: 'select',
				[EDIT_DEFAULT]: 1,

			},




		}

		this.lab_campaigns_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData} ><div className='button btn btn-warning btn-sm' style={{ fontSize: 12 }}>Edit</div></FuncEditRow>
					<div className='button btn btn-warning  btn-sm' onClick={() => {
						this.configModal.loadData(rowData);
						this.configModal.modal();
					}} style={{ fontSize: 12 }}>Params</div>

				</div>
			}
		};
		this.lab_campaigns_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: LAB_CAMPAIGNS_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionLab_campaignsView(),
			[DATA_KEY]: [LAB_CAMPAIGN_ID],
			[DATA_SORT]: { [LAB_CAMPAIGN_ID]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Lab_campaigns()

		};

		// this.watchlistIcon = {};

		this.coinMarketData = {}


	}

	permissionLab_campaignsView() {
		return Object.assign(
			...Object.keys(this.lab_campaigns_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.lab_campaigns_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	getRankCoinMarket(){
		var model = new Coinmarket();

		return model.getRank()
	}

	updateData(){

		let nameAccount = App.accountSelectorLab.accountIndex[ App.accountSelectorLab.selected()][LAB_ACCOUNT_NAME]
		makeQuestion(`Do you want update Rank for account ${nameAccount} `).then(res => {
			if(res){
				let model = new Lab_campaigns();


				model.updateRank({'account_id' : App.accountSelectorLab.selected()}).then(res => {
			
					if(res['result']){
						this.table.filter()
					}

					
				})
			}
		})
	}

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.lab_campaigns_struct} autoload={false} addRow={this.addRow.bind(this)}>
					<FuncBar
						left={<><FuncHideCol />
							<div className='button btn btn-primary  btn-sm' onClick={() => { this.simulates() }} style={{ fontSize: 12 }}>Simulates</div>
							<div className='button btn btn-danger btn-sm' onClick={() => { this.killsimulates() }} style={{ fontSize: 12 }}>Stop</div>

							<button type="button" className="button btn btn-sm btn-primary" onClick={() => this.updateData()}>Update Rank</button>
						</>}
						right={<><FuncAdd /><FuncDel /><FuncEdit></FuncEdit><FuncClear /><FuncRefresh /><FuncExport /><FuncImport></FuncImport></>}></FuncBar>
					<MainTable className='table table-bordered table-striped table-resizable'></MainTable>
					<Pagination></Pagination>

					<FuncConfigModal ref={c => this.configModal = c} struct={{

						[LAB_CAMPAIGN_PARAMS_LOG]: {
							[INPUT_NAME]: 'Enable Log',
							[INPUT_TYPE]: 'select',
							[INPUT_DEFAULT]: 0,
							[INPUT_OPTION]: { 0: 'False', 1: 'True' }

						},
						[LAB_CAMPAIGN_PARAMS_LOG_ORDER]: {
							[INPUT_NAME]: 'Enable Order Log',
							[INPUT_TYPE]: 'select',
							[INPUT_DEFAULT]: 0,
							[INPUT_OPTION]: { 0: 'False', 1: 'True' }

						},

					}} column={LAB_CAMPAIGN_PARAMS}></FuncConfigModal>

				</Table>


			</div>
		);
	}
	// getIcon() {
	// 	var watchlist = new Watchlist();

	// 	return watchlist.getIcon();

	// }

	async componentDidMount() {
		this.table.map = (loading) => {
			this.table.model.map(loading).then((res) => {
				if (res) {
					if (res['result']) {
						this.table.setMapping(res['data']);
						this.setState({ strategies: { '': '', ...res['data']['strategies'] } })
					}
				}
			})
		}

		this.coinMarketData = await this.getRankCoinMarket()

		if (App.accountSelectorLab) {
			App.accountSelectorLab.register('lab_campaign', () => {
				this.table.setFilter({
					[LAB_CAMPAIGN_ACCOUNT]: {
						"logic": "and",
						"data": {
							"=": App.accountSelectorLab ? App.accountSelectorLab.selected() : ''
						}
					}
				})
				this.table.filter();
			});

			this.table.setFilter({
				[LAB_CAMPAIGN_ACCOUNT]: {
					"logic": "and",
					"data": {
						"=": App.accountSelectorLab ? App.accountSelectorLab.selected() : ''
					}
				}
			});
			this.table.map();
			this.table.filter();
		}

		

		this.updateInterval = setInterval(() => { this.table.filter(false) }, 7000);
	}

	componentWillUnmount() {
		
		if (App.accountSelectorLab) {
			App.accountSelectorLab.unregister('lab_campaign')
		}
		
		if (this.updateInterval)
			clearInterval(this.updateInterval);
	}


	async simulate(id, loading = true) {

		if (loading) {
			var confirm = await makeQuestion('Old result will be deleted. Do you want to start this campaign?');
			if (!confirm) return;
			App.loading(true)
		}

		return axios.request({
			url: `/admin/lab_campaigns/simulate`,
			method: 'POST',
			data: {
				id: id
			}
		})

			.then(response => {
				if (loading) App.loading(false);
				response = response['data'];
				if (response['result']) {
					this.table.filter();
				}
				else {
					error_handle(response);
				}
				return response;
			})

			.catch((error) => {
				if (loading) App.loading(false);
				error_handle(error)
				return false;
			})
	}


	async simulates() {
		var dataSelect = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];
		var wl = [];
		for (let i in dataSelect) {
			wl.push(dataSelect[i][LAB_CAMPAIGN_ID]);
		}

		if (wl.length == 0) {
			showLog('Please select a symbol');
			return;
		}

		var confirm = await makeQuestion('Old result will be deleted. Do you want to Start ' + wl.length + ' campaigns?');
		if (!confirm) return;

		for (let i in wl) {
			await this.simulate(wl[i], false);
		}
	}

	async killsimulates() {
		var dataSelect = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];
		var wl = [];
		for (let i in dataSelect) {
			wl.push(dataSelect[i][LAB_CAMPAIGN_ID]);
		}

		if (wl.length == 0) {
			showLog('Please select a symbol');
			return;
		}

		var confirm = await makeQuestion('Do you want to stop ' + wl.length + ' campaigns?');
		if (!confirm) return;

		for (let i in wl) {
			await this.killSimulate(wl[i], false);
		}
	}

	async killSimulate(id, loading = true) {

		if (loading) {
			var confirm = await makeQuestion('Do you want to Cancle this campaign?');
			if (!confirm) return;
		}

		if (loading) App.loading(true)
		return axios.request({
			url: `/admin/lab_campaigns/kill`,
			method: 'POST',
			data: {
				id: id
			}
		})

			.then(response => {
				if (loading) App.loading(false);
				response = response['data'];
				if (response['result']) {
					this.table.filter();
				}
				else {
					error_handle(response);
				}
				return response;
			})

			.catch((error) => {
				if (loading) App.loading(false);
				error_handle(error)
				return false;
			})
	}

	addRow(rowData, loading = true) {

		if (rowData[LAB_CAMPAIGN_SYMBOL] == 'all') {
			console.log(this.table.mapping);
			var listOfSymbol = this.table.mapping[LAB_CAMPAIGN_SYMBOL];
			var rowDatas = [];
			for (let i in listOfSymbol) {
				if (i != 'all') {
					rowDatas.push({
						...rowData, ...{
							[LAB_CAMPAIGN_NAME]: rowData[LAB_CAMPAIGN_NAME] + ' - ' + listOfSymbol[i],
							[LAB_CAMPAIGN_SYMBOL]: listOfSymbol[i],
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


}

export default Lab_campaignsView
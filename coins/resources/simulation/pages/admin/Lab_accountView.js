import React, { Component } from 'react'
import Table from '../../components/table/Table'
import MainTable from '../../components/table/MainTable'
import Pagination from '../../components/table/Pagination'
import FuncBar from '../../components/table/FuncBar'

import FuncEditRow from '../../components/table/FuncEditRow'
import FuncEdit from '../../components/table/FuncEdit'
import FuncAdd from '../../components/table/FuncAdd'
import FuncHideCol from '../../components/table/FuncHideCol'
import FuncDel from '../../components/table/FuncDel'
import FuncClear from '../../components/table/FuncClear'
import FuncRefresh from '../../components/table/FuncRefresh'
import FuncExport from '../../components/table/FuncExport'

import Lab_account from '../../model/admin/Lab_account'
import InputDate from '../../components/inputs/InputDate'
import LabTradeList from '../../components/admin/LabTradeList'
import AccountBalanceChart from '../../components/admin/AccountBalanceChart'
import FuncClone from '../../components/table/FuncClone'
import Lab_campaigns from '../../model/admin/Lab_campaigns'
import OptLogModal from '../../components/admin/OptLogModal'
import StrategyModal from '../../components/admin/Opt_result/StrategyModal'
import LabResult4h1dModal from '../../components/admin/LabResult4h1dModal'
import Lab_track_balance_gen from '../../model/admin/Lab_track_balance_gen '


class Lab_accountView extends Component {

	constructor(props) {
		super(props);

		this.lab_account_struct = {};
		this.lab_account_struct[STRUCT_FILTERS] = {}
		this.lab_account_struct[STRUCT_COLUMNS] = {

			'action': {
				[COL_NAME]: lang('Action'),
				[COL_SORT]: false,
				[COL_DECORATOR_IN]: (col, row, data) => {
					var rowData = data[row];
					var id = rowData[LAB_ACCOUNT_ID];
					return <div className='box_flex' style={{ justifyContent: 'center' }}>
						{/* <div className='button btn btn-primary' style={{fontSize:10}} onClick={()=>{
							this.simulate(id, true, 'php');
						}}>Start PHP</div> */}
						{/* <div className='button btn btn-primary' style={{fontSize:10}} onClick={()=>{
							this.simulate(id, true, 'python');
						}}>Start</div> */}
						<div className='button btn btn-primary' style={{ fontSize: 10 }} onClick={() => {
							this.simulate(id, true, 'python_1m');
						}}>Start</div>
						<div className='button btn btn-danger' style={{ fontSize: 10 }} onClick={() => {
							this.killSimulate(id, true);
						}}>Stop</div>
						<div className='button btn btn-info' style={{ fontSize: 10 }} onClick={() => {
							this.accountBlanceChart.modal();
							this.accountBlanceChart.loadData(rowData);
						}}>Balance</div>
						{
							this.genId.includes(id) ?
								<div className='button btn btn-danger' style={{ fontSize: 10 }} onClick={() => {
									this.updateData(rowData)
								}}>Gen Balance</div> :
								<div className='button btn btn-info' style={{ fontSize: 10 }} onClick={() => {
									this.updateData(rowData)
								}}>Gen Balance</div>
						}
						<div className='button btn btn-info' style={{ fontSize: 10 }} onClick={() => {
							this.modal4h1d.modal();
							this.modal4h1d.loadData(rowData);
						}}>4H1D</div>
					</div>
				}

			},
			[LAB_ACCOUNT_ID]: {
				[COL_NAME]: lang(LAB_ACCOUNT_ID),
				[COL_SORT]: true,

			},
			[LAB_ACCOUNT_NAME]: {
				[COL_NAME]: lang(LAB_ACCOUNT_NAME),
				[COL_SORT]: true,
				[COL_STYLE]: { maxWidth: 'unset' }

			},
			[LAB_ACCOUNT_RUNNING]: {
				[COL_NAME]: lang(LAB_ACCOUNT_RUNNING),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => {
					return data == 1 ? <b style={{ color: 'limegreen' }}>Running</b> : <b style={{ color: 'red' }}>Stopped</b>
				}

			},
			'lab_account_status': {
				[COL_NAME]: 'Status',
				[COL_SORT]: false,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {

					if (Object.keys(this.maxStatus) == 0) return

					var accountId = data[rowId][LAB_ACCOUNT_ID];
					var data = this.maxStatus[accountId];

					var process, total, percent;
					if (data) {
						process = data['process']
						total = data['total']

					} else {
						process = 0
						total = 0
					}

					percent = total > 0 ? Math.round(process * 100 / total) : 0;

					return (
						<div className='box_flex' style={{ minWidth: 200 }}>

							<div className="progress" style={{ flexGrow: 1 }}>
								<div className="progress-bar progress-bar-striped active" role="progressbar" style={{ width: `${percent}%` }}>
									{`${process}/${total}`}
								</div>
							</div>

						</div>
					)

				}

			},

			[LAB_ACCOUNT_BALANCE]: {
				[COL_NAME]: lang(LAB_ACCOUNT_BALANCE),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => formatNumber(Number(data).toFixed(3))

			},
			[LAB_ACCOUNT_RESERVE]: {
				[COL_NAME]: lang(LAB_ACCOUNT_RESERVE),
				[COL_SORT]: true,

			},
			[LAB_ACCOUNT_COMPOUND]: {
				[COL_NAME]: lang(LAB_ACCOUNT_COMPOUND),
				[COL_SORT]: true,

			},
			[LAB_ACCOUNT_MARGIN_TYPE]: {
				[COL_NAME]: lang(LAB_ACCOUNT_MARGIN_TYPE),
				[COL_SORT]: false,

			},
			[LAB_ACCOUNT_TRACK_BALANCE]: {
				[COL_NAME]: lang(LAB_ACCOUNT_TRACK_BALANCE),
				[COL_SORT]: false,

			},
			[LAB_ACCOUNT_SYNC]: {
				[COL_NAME]: lang(LAB_ACCOUNT_SYNC),
				[COL_SORT]: false,

			},
			[LAB_ACCOUNT_LEAP]: {
				[COL_NAME]: lang(LAB_ACCOUNT_LEAP),
				[COL_SORT]: false,

			},
			[LAB_ACCOUNT_DB]: {
				[COL_NAME]: lang(LAB_ACCOUNT_DB),
				[COL_SORT]: false,

			},
			[LAB_ACCOUNT_DATA_TYPE]: {
				[COL_NAME]: lang(LAB_ACCOUNT_DATA_TYPE),
				[COL_SORT]: false,

			},
			[LAB_ACCOUNT_DATA_LENGTH]: {
				[COL_NAME]: lang(LAB_ACCOUNT_DATA_LENGTH),
				[COL_SORT]: false,

			},
			[LAB_ACCOUNT_PARAMS]: {
				[COL_NAME]: lang(LAB_ACCOUNT_PARAMS),
				[COL_SORT]: false,
				[COL_STYLE]: { whiteSpace: 'break-spaces' },
				[COL_DECORATOR_IN]: data => {
					try {
						if (!data || data == '') return ''
						data = JSON.parse(data)
						return JSON.stringify(data, null, 2)
					} catch (error) {
						return ''
					}

				}

			},
			[LAB_ACCOUNT_SERVER]: {
				[COL_NAME]: lang(LAB_ACCOUNT_SERVER),
				[COL_SORT]: false,

			},
			[LAB_ACCOUNT_CHOICE_STRATEGY]: {
				[COL_NAME]: lang(LAB_ACCOUNT_CHOICE_STRATEGY),
				[COL_SORT]: false,

			},
			[LAB_ACCOUNT_CHOICE_CONDITION]: {
				[COL_NAME]: lang(LAB_ACCOUNT_CHOICE_CONDITION),
				[COL_SORT]: false,
				[COL_STYLE]: { whiteSpace: 'pre', minWidth: 400 }

			},
			[LAB_ACCOUNT_CHOICE_PERIOD]: {
				[COL_NAME]: lang(LAB_ACCOUNT_CHOICE_PERIOD),
				[COL_SORT]: true,

			},
			[LAB_ACCOUNT_CHOICE_RESULT]: {
				[COL_NAME]: lang(LAB_ACCOUNT_CHOICE_RESULT),
				[COL_SORT]: false,
				[COL_DECORATOR_IN]: (data) => {

					return <button type="button" className="btn btn-info" onClick={() => {

						this.StrategyModal.modal();
						this.StrategyModal.setValue(data, 'Result');
					}}>Info</button>;
				},
				[COL_STYLE]: { textAlign: 'center' },

			},
			[LAB_ACCOUNT_TELE_BOT]: {
				[COL_NAME]: lang(LAB_ACCOUNT_TELE_BOT),
				[COL_SORT]: false,

			},
			[LAB_ACCOUNT_TELE_GROUP_NOTICE]: {
				[COL_NAME]: lang(LAB_ACCOUNT_TELE_GROUP_NOTICE),
				[COL_SORT]: true,

			},
			[LAB_ACCOUNT_TELE_GROUP_SUMMARY]: {
				[COL_NAME]: lang(LAB_ACCOUNT_TELE_GROUP_SUMMARY),
				[COL_SORT]: true,

			},
			[LAB_ACCOUNT_TELE_GROUP_ERROR]: {
				[COL_NAME]: lang(LAB_ACCOUNT_TELE_GROUP_ERROR),
				[COL_SORT]: true,

			},
			[LAB_ACCOUNT_USER]: {
				[COL_NAME]: lang(LAB_ACCOUNT_USER),
				[COL_SORT]: true,

			},
			[LAB_ACCOUNT_GROUP]: {
				[COL_NAME]: lang(LAB_ACCOUNT_GROUP),
				[COL_SORT]: true,

			},
			[LAB_ACCOUNT_NOTE]: {
				[COL_NAME]: lang(LAB_ACCOUNT_NOTE),
				[COL_SORT]: false,

			},



		}
		this.lab_account_struct[STRUCT_FILTERS] = {

			[LAB_ACCOUNT_ID]: {
				[FILTER_NAME]: lang(LAB_ACCOUNT_ID),
				[FILTER_TYPE]: 'text',
			},
			[LAB_ACCOUNT_NAME]: {
				[FILTER_NAME]: lang(LAB_ACCOUNT_NAME),
				[FILTER_TYPE]: 'text',
			},
			[LAB_ACCOUNT_BALANCE]: {
				[FILTER_NAME]: lang(LAB_ACCOUNT_BALANCE),
				[FILTER_TYPE]: 'number',
			},
			[LAB_ACCOUNT_RUNNING]: {
				[FILTER_NAME]: lang(LAB_ACCOUNT_RUNNING),
				[FILTER_TYPE]: 'select',
			},
			[LAB_ACCOUNT_RESERVE]: {
				[FILTER_NAME]: lang(LAB_ACCOUNT_RESERVE),
				[FILTER_TYPE]: 'number',
			},
			[LAB_ACCOUNT_COMPOUND]: {
				[FILTER_NAME]: lang(LAB_ACCOUNT_COMPOUND),
				[FILTER_TYPE]: 'select',
			},
			[LAB_ACCOUNT_TRACK_BALANCE]: {
				[FILTER_NAME]: lang(LAB_ACCOUNT_TRACK_BALANCE),
				[FILTER_TYPE]: 'select',
			},
			[LAB_ACCOUNT_SYNC]: {
				[FILTER_NAME]: lang(LAB_ACCOUNT_SYNC),
				[FILTER_TYPE]: 'select',
			},
			[LAB_ACCOUNT_LEAP]: {
				[FILTER_NAME]: lang(LAB_ACCOUNT_LEAP),
				[FILTER_TYPE]: 'select',
			},
			[LAB_ACCOUNT_DB]: {
				[FILTER_NAME]: lang(LAB_ACCOUNT_DB),
				[FILTER_TYPE]: 'select',
			},
			[LAB_ACCOUNT_DATA_TYPE]: {
				[FILTER_NAME]: lang(LAB_ACCOUNT_DATA_TYPE),
				[FILTER_TYPE]: 'select',
			},
			[LAB_ACCOUNT_DATA_LENGTH]: {
				[FILTER_NAME]: lang(LAB_ACCOUNT_DATA_LENGTH),
				[FILTER_TYPE]: 'text',
			},
			[LAB_ACCOUNT_PARAMS]: {
				[FILTER_NAME]: lang(LAB_ACCOUNT_PARAMS),
				[FILTER_TYPE]: 'text',
			},
			[LAB_ACCOUNT_MARGIN_TYPE]: {
				[FILTER_NAME]: lang(LAB_ACCOUNT_MARGIN_TYPE),
				[FILTER_TYPE]: 'select',
			},
			[LAB_ACCOUNT_SERVER]: {
				[FILTER_NAME]: lang(LAB_ACCOUNT_SERVER),
				[FILTER_TYPE]: 'select',
			},
			[LAB_ACCOUNT_CHOICE_STRATEGY]: {
				[FILTER_NAME]: lang(LAB_ACCOUNT_CHOICE_STRATEGY),
				[FILTER_TYPE]: 'select',
			},
			[LAB_ACCOUNT_CHOICE_PERIOD]: {
				[FILTER_NAME]: lang(LAB_ACCOUNT_CHOICE_PERIOD),
				[FILTER_TYPE]: 'number',
			},
			[LAB_ACCOUNT_TELE_BOT]: {
				[FILTER_NAME]: lang(LAB_ACCOUNT_TELE_BOT),
				[FILTER_TYPE]: 'select',
			},
			[LAB_ACCOUNT_TELE_GROUP_NOTICE]: {
				[FILTER_NAME]: lang(LAB_ACCOUNT_TELE_GROUP_NOTICE),
				[FILTER_TYPE]: 'select',
			},
			[LAB_ACCOUNT_TELE_GROUP_SUMMARY]: {
				[FILTER_NAME]: lang(LAB_ACCOUNT_TELE_GROUP_SUMMARY),
				[FILTER_TYPE]: 'select',
			},
			[LAB_ACCOUNT_TELE_GROUP_ERROR]: {
				[FILTER_NAME]: lang(LAB_ACCOUNT_TELE_GROUP_ERROR),
				[FILTER_TYPE]: 'select',
			},
			[LAB_ACCOUNT_USER]: {
				[FILTER_NAME]: lang(LAB_ACCOUNT_USER),
				[FILTER_TYPE]: 'select',
			},
			[LAB_ACCOUNT_GROUP]: {
				[FILTER_NAME]: lang(LAB_ACCOUNT_GROUP),
				[FILTER_TYPE]: 'text',
			},


		}

		this.lab_account_struct[STRUCT_EDIT] = {

			[LAB_ACCOUNT_NAME]: {
				[EDIT_NAME]: lang(LAB_ACCOUNT_NAME),
				[EDIT_TYPE]: 'text',

			},
			[LAB_ACCOUNT_BALANCE]: {
				[EDIT_NAME]: lang(LAB_ACCOUNT_BALANCE),
				[EDIT_TYPE]: 'number',

			},
			[LAB_ACCOUNT_RESERVE]: {
				[EDIT_NAME]: lang(LAB_ACCOUNT_RESERVE),
				[EDIT_TYPE]: 'number',

			},
			[LAB_ACCOUNT_COMPOUND]: {
				[EDIT_NAME]: lang(LAB_ACCOUNT_COMPOUND),
				[EDIT_TYPE]: 'select',

			},

			[LAB_ACCOUNT_MARGIN_TYPE]: {
				[EDIT_NAME]: lang(LAB_ACCOUNT_MARGIN_TYPE),
				[EDIT_TYPE]: 'select',
				[EDIT_DEFAULT]: 'CROSS',

			},

			[LAB_ACCOUNT_TRACK_BALANCE]: {
				[EDIT_NAME]: lang(LAB_ACCOUNT_TRACK_BALANCE),
				[EDIT_TYPE]: 'select',
				[EDIT_DEFAULT]: '0',

			},
			[LAB_ACCOUNT_SYNC]: {
				[EDIT_NAME]: lang(LAB_ACCOUNT_SYNC),
				[EDIT_TYPE]: 'select',
				[EDIT_DEFAULT]: '1',

			},
			[LAB_ACCOUNT_LEAP]: {
				[EDIT_NAME]: lang(LAB_ACCOUNT_LEAP),
				[EDIT_TYPE]: 'select',
				[EDIT_DEFAULT]: 0,

			},
			[LAB_ACCOUNT_DB]: {
				[EDIT_NAME]: lang(LAB_ACCOUNT_DB),
				[EDIT_TYPE]: 'select',
				[EDIT_DEFAULT]: 'coin_lab_1_year',

			},
			[LAB_ACCOUNT_DATA_TYPE]: {
				[EDIT_NAME]: lang(LAB_ACCOUNT_DATA_TYPE),
				[EDIT_TYPE]: 'select',
				[EDIT_DEFAULT]: '1m',

			},
			[LAB_ACCOUNT_DATA_LENGTH]: {
				[EDIT_NAME]: lang(LAB_ACCOUNT_DATA_LENGTH),
				[EDIT_TYPE]: 'text',
				[EDIT_DEFAULT]: '1',

			},
			[LAB_ACCOUNT_PARAMS]: {
				[EDIT_NAME]: lang(LAB_ACCOUNT_PARAMS),
				[EDIT_TYPE]: 'textarea',


			},

			[LAB_ACCOUNT_NOTE]: {
				[EDIT_NAME]: lang(LAB_ACCOUNT_NOTE),
				[EDIT_TYPE]: 'textarea',

			},
			[LAB_ACCOUNT_SERVER]: {
				[EDIT_NAME]: lang(LAB_ACCOUNT_SERVER),
				[EDIT_TYPE]: 'select',
				[EDIT_DEFAULT]: 'localhost',

			},
			[LAB_ACCOUNT_CHOICE_STRATEGY]: {
				[EDIT_NAME]: lang(LAB_ACCOUNT_CHOICE_STRATEGY),
				[EDIT_TYPE]: 'select',


			},
			[LAB_ACCOUNT_CHOICE_PERIOD]: {
				[EDIT_NAME]: lang(LAB_ACCOUNT_CHOICE_PERIOD),
				[EDIT_TYPE]: 'number',
				[EDIT_DES]: 'By Day'

			},

			[LAB_ACCOUNT_CHOICE_CONDITION]: {
				[EDIT_NAME]: lang(LAB_ACCOUNT_CHOICE_CONDITION),
				[EDIT_TYPE]: 'ace',
				[EDIT_OPTION]: [
					{ value: 'profit' },
					{ value: 'profit_index' },
					{ value: 'total_position' },
					{ value: 'total_position_index' },
					{ value: 'avg_interval' },
					{ value: 'avg_interval_index' },
				]
			},

			[LAB_ACCOUNT_TELE_BOT]: {
				[EDIT_NAME]: lang(LAB_ACCOUNT_TELE_BOT),
				[EDIT_TYPE]: 'select',


			},

			[LAB_ACCOUNT_TELE_GROUP_NOTICE]: {
				[EDIT_NAME]: lang(LAB_ACCOUNT_TELE_GROUP_NOTICE),
				[EDIT_TYPE]: 'select',

			},
			[LAB_ACCOUNT_TELE_GROUP_SUMMARY]: {
				[EDIT_NAME]: lang(LAB_ACCOUNT_TELE_GROUP_SUMMARY),
				[EDIT_TYPE]: 'select',

			},
			[LAB_ACCOUNT_TELE_GROUP_ERROR]: {
				[EDIT_NAME]: lang(LAB_ACCOUNT_TELE_GROUP_ERROR),
				[EDIT_TYPE]: 'select',

			},

			[LAB_ACCOUNT_USER]: {
				[EDIT_NAME]: lang(LAB_ACCOUNT_USER),
				[EDIT_TYPE]: 'select',
			},
			[LAB_ACCOUNT_GROUP]: {
				[EDIT_NAME]: lang(LAB_ACCOUNT_GROUP),
				[EDIT_TYPE]: 'text',
				[EDIT_DEFAULT]: App.parsed.group
			},



		}

		this.lab_account_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData}><div className='button btn btn-primary' style={{ fontSize: 12 }}>Edit</div></FuncEditRow>
					<div className='button btn btn-warning' onClick={() => {
						this.testnetTradeList.setAccount(rowData);
						this.testnetTradeList.modal();
					}} style={{ fontSize: 12 }}>Trades</div>

					<div className='button btn btn-sm btn-info' style={{ fontSize: 12 }} onClick={e => {

						this.OptLogModal.modal()
						this.OptLogModal.setValue(rowData[LAB_ACCOUNT_ID], true)

					}}>Log</div>
				</div>
			}
		};

		this.lab_account_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: LAB_ACCOUNT_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionLab_accountView(),
			[DATA_KEY]: [LAB_ACCOUNT_ID],
			[DATA_SORT]: { [LAB_ACCOUNT_ID]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Lab_account()

		};

		this.maxStatus = {}
		this.genId = []


	}

	permissionLab_accountView() {
		return Object.assign(
			...Object.keys(this.lab_account_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.lab_account_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
			{ [LAB_ACCOUNT_USER]: App.user[AUTHEN_GROUP] == 0 ? 'Write' : 'Read' }
		)
	}

	async afterClone(clone, res) {
		var oldId = clone[LAB_ACCOUNT_ID];
		var newId = res[LAB_ACCOUNT_ID];

		var LabCampignModel = new Lab_campaigns();

		var labData = await LabCampignModel.read({ [LAB_CAMPAIGN_ACCOUNT]: oldId });

		if (labData['result']) {
			labData = labData['data'];
			labData.map(item => {
				item[LAB_CAMPAIGN_ACCOUNT] = newId;
				delete item[LAB_CAMPAIGN_ID];
			})
		}


		LabCampignModel.adds(labData)

	}


	async getMaxStatusCampaign() {
		var LabCampignModel = new Lab_campaigns();
		var labData = await LabCampignModel.read({});


		if (labData['result']) {
			labData = labData['data'];
			var maxStatus = {};
			labData.map(item => {
				var accountId = item[LAB_CAMPAIGN_ACCOUNT];
				var status = item[LAB_CAMPAIGN_STATUS];
				var process, total;
				if (status) {
					status = status.split(',');
					total = get(Number(status[0]), 0);
					process = get(Number(status[1]), 0);
				}

				if (process) {
					if (maxStatus[accountId]) {
						if (process > maxStatus[accountId]['process']) {
							maxStatus[accountId] = {
								'process': process,
								'total': total
							}
						}
					} else {
						maxStatus[accountId] = {
							'process': process,
							'total': total
						}
					}
				}
			})

			this.maxStatus = maxStatus
			// this.table.filter()
		}

		var LabCampignModel = new Lab_track_balance_gen();
		var Data = await LabCampignModel.getExistId({});

		if (Data['result']) {
			Data = Data['data'];
			var genId = []
			Data.map(item => {
				genId.push(item['lab_track_balance_gen_account'])
			})

			this.genId = genId
		}

		this.table.filter()
	}

	render() {
		return (
			<div>
				
				<Table ref={c => this.table = c} table={this.lab_account_struct} autoload={false} afterClone={(clone, res) => this.afterClone(clone, res)}>
					<FuncBar
						left={<><FuncHideCol /> <div style={{display : 'flex' , alignItems : 'center', fontSize : '16px'}}>
							
							<b><span style={{ cursor : 'pointer'}} onClick={() => {  window.location.href = App.link('/admin/lab_account_group/view')}}>Account</span> / {App.parsed.group}</b>

						</div></>}
						right={<><FuncAdd /><FuncClone ></FuncClone><FuncEdit></FuncEdit><FuncDel /><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-striped table-resizable'></MainTable>
					<Pagination></Pagination>

				</Table>
				<LabTradeList ref={c => this.testnetTradeList = c}></LabTradeList>

				<AccountBalanceChart ref={c => this.accountBlanceChart = c}></AccountBalanceChart>
				<OptLogModal ref={c => this.OptLogModal = c}></OptLogModal>

				<StrategyModal ref={c => this.StrategyModal = c} ></StrategyModal>
				<LabResult4h1dModal ref={c => this.modal4h1d = c}></LabResult4h1dModal>



			</div>
		);
	}

	componentDidMount() {
		this.table.map().then(res => {
			this.table[STRUCT_TABLE][DATA_SPECIAL] = { group: App.parsed.group }
			this.table.filter();
		})
		this.getMaxStatusCampaign()

	}
	updateData(rowData) {
		let model = new Lab_track_balance_gen();
		model.check({ 'account_id': rowData[LAB_ACCOUNT_ID] }).then(res => {
			if (res['result']) {
				if (res['data'] == 1) {

					makeQuestion(`Balance chart for existing accounts ${rowData[LAB_ACCOUNT_NAME]}? Do you want clean and save data`, 'Yes', 'No', 'error').then(res => {
						if (res) {
							let model = new Lab_track_balance_gen();


							model.updateData({ 'account_id': rowData[LAB_ACCOUNT_ID] }).then(res => {

								// if(res['result']){
								// 	this.table.filter()
								// }


							})
						}
					})
				} else {
					makeQuestion(`Do you want save data   Balance Chart for account ${rowData[LAB_ACCOUNT_NAME]} `).then(res => {
						if (res) {
							let model = new Lab_track_balance_gen();


							model.updateData({ 'account_id': rowData[LAB_ACCOUNT_ID] }).then(res => {

								// if(res['result']){
								// 	this.table.filter()
								// }


							})
						}
					})
				}
			}
		})


	}

	async simulate(id, loading = true, code = 'python') {

		if (loading) {
			var confirm = await makeQuestion('Old result will be deleted. Do you want to start this account?');
			if (!confirm) return;
			App.loading(true)
		}

		var url = code == 'python'
			? `/admin/lab_account/pysimulate`
			: code == 'python_1m'
				? `/admin/lab_account/pysimulate1m`
				: `/admin/lab_account/simulate`;

		return axios.request({
			url: url,
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
			var confirm = await makeQuestion('Do you want to stop this account?');
			if (!confirm) return;
		}

		if (loading) App.loading(true)
		return axios.request({
			url: `/admin/lab_account/kill`,
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

}

export default Lab_accountView
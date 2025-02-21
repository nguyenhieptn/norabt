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


import Lab_opt_result from '../../model/admin/Lab_opt_result'
import AccountModal from '../../components/admin/Opt_result/AccountModal'
import CampaignModal from '../../components/admin/Opt_result/CampaignModal'
import StrategyModal from '../../components/admin/Opt_result/StrategyModal'
import EventModal from '../../components/admin/Opt_result/EventModal'
import Lab_campaigns from '../../model/admin/Lab_campaigns'
import Lab_account from '../../model/admin/Lab_account'
import ToolTip from '../../components/common/Tooltip'



class Opt_resultView extends Component {

	constructor(props) {
		super(props);

		this.lab_opt_result_struct = {};
		this.lab_opt_result_struct[STRUCT_FILTERS] = {}
		this.lab_opt_result_struct[STRUCT_COLUMNS] = {

			[LAB_OPT_RESULT_OPTIMIZATION]: {
				[COL_NAME]: lang(LAB_OPT_RESULT_OPTIMIZATION),
				[COL_SORT]: true,


			},




			[LAB_OPT_RESULT_PARAMS]: {
				[COL_NAME]: lang(LAB_OPT_RESULT_PARAMS),
				[COL_SORT]: false,
				[COL_STYLE]: { overflow: 'unset' },
				[COL_DECORATOR_IN]: (data) => {
					if (!data) return
					data = JSON.parse(data);
					let tooltip = null;
					return (
						<div>
							{
								Object.keys(data).map((item, index) => {
									if (index == 0) {
										return (<div key={item} style={{ display: 'flex', justifyContent: 'space-between' }}>
											<div>{item} : {data[item]}</div>
											<div style={{ position: 'relative', display: 'flex', justifyContent: 'center' }} >
												<ToolTip ref={c => tooltip = c}  ></ToolTip>
												<i className="fa fa-clone" style={{ cursor: 'pointer' }} onMouseEnter={() => {
													tooltip.set(true, 'Click to copy params', false)
												}} onClick={(e) => {

													this.onCache(data)
													tooltip.set(true, 'Copied', false)
												}}></i>

											</div>
										</div>)
									}

									return (<div key={item}>{item} : {data[item]}</div>)
								})
							}
						</div>
					)
				}

			},
			[LAB_OPT_RESULT_BALANCE]: {
				[COL_NAME]: lang(LAB_OPT_RESULT_BALANCE),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {
					if (!data) return
					data = formatNumber(data.toFixed(3))
					return data;
				}

			},


			[LAB_OPT_RESULT_MARGIN_BALANCE]: {
				[COL_NAME]: lang(LAB_OPT_RESULT_MARGIN_BALANCE),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {
					if (!data) return
					data = formatNumber(data.toFixed(3))
					return data;
				}

			},
			[LAB_OPT_RESULT_UNRELIZE_MAX]: {
				[COL_NAME]: lang(LAB_OPT_RESULT_UNRELIZE_MAX),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {
					if (!data) return
					data = formatNumber(data.toFixed(3)) + '%';
					return data;
				}


			},
			[LAB_OPT_RESULT_INVEST_MAX]: {
				[COL_NAME]: lang(LAB_OPT_RESULT_INVEST_MAX),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {
					if (!data) return
					data = formatNumber(data.toFixed(3)) + '%';
					return data;
				}

			},
			'invest': {
				[COL_NAME]: 'Investment',
				[COL_SORT]: false,
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var account = data[rowid][LAB_OPT_RESULT_ACCOUNT];
					if (!account) return
					account = JSON.parse(account);
					var invest = this.invest[account[LAB_ACCOUNT_ID]];
					if (!invest) return
					return formatNumber(invest)
				}
			},
			'profit': {
				[COL_NAME]: 'Profit',
				[COL_SORT]: false,
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var account = data[rowid][LAB_OPT_RESULT_ACCOUNT];
					if (!account) return
					account = JSON.parse(account);
					var invest = this.invest[account[LAB_ACCOUNT_ID]];
					if (!invest) return
					// var balance = data[rowid][LAB_OPT_RESULT_BALANCE]
					var balance = data[rowid][LAB_OPT_RESULT_MARGIN_BALANCE]

					var result = (balance - invest) / invest;
					result = (result * 100).toFixed(2)
					return result

				}
			},


			[LAB_OPT_RESULT_INTERVAL_AVG]: {
				[COL_NAME]: lang(LAB_OPT_RESULT_INTERVAL_AVG),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {
					if (!data) return
					data = Math.round(data / 1000);
					var d = Math.floor(data / (3600 * 24));
					var h = Math.floor(data % (3600 * 24) / 3600);
					var m = Math.floor(data % 3600 / 60);

					var dDisplay = d > 0 ? d + 'd ' : "";
					var hDisplay = h > 0 ? h + 'h ' : "";
					var mDisplay = m > 0 ? m + 'm' : 0;
					var color = '';
					// if(h > 0 || d >0) color = 'red'
					var date = dDisplay + hDisplay + mDisplay;
					return <span style={{ color: color }}>{date}</span>;
				},

			},
			[LAB_OPT_RESULT_INTERVAL_MAX]: {
				[COL_NAME]: lang(LAB_OPT_RESULT_INTERVAL_MAX),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {
					if (!data) return
					data = Math.round(data / 1000);
					var d = Math.floor(data / (3600 * 24));
					var h = Math.floor(data % (3600 * 24) / 3600);
					var m = Math.floor(data % 3600 / 60);

					var dDisplay = d > 0 ? d + 'd ' : "";
					var hDisplay = h > 0 ? h + 'h ' : "";
					var mDisplay = m > 0 ? m + 'm' : 0;
					var color = '';
					// if(h > 0 || d >0) color = 'red'
					var date = dDisplay + hDisplay + mDisplay;
					return <span style={{ color: color }}>{date}</span>;
				},

			},
			[LAB_OPT_RESULT_TOTAL_POSITION]: {
				[COL_NAME]: lang(LAB_OPT_RESULT_TOTAL_POSITION),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {
					if (!data) return
					data = formatNumber(data);
					return data;
				}

			},
			[LAB_OPT_RESULT_TOTAL_LONG]: {
				[COL_NAME]: lang(LAB_OPT_RESULT_TOTAL_LONG),
				[COL_SORT]: true,

			},
			[LAB_OPT_RESULT_TOTAL_SHORT]: {
				[COL_NAME]: lang(LAB_OPT_RESULT_TOTAL_SHORT),
				[COL_SORT]: true,

			},
			[LAB_OPT_RESULT_PENDING_EVENT]: {
				[COL_NAME]: lang(LAB_OPT_RESULT_PENDING_EVENT),
				[COL_SORT]: true,

			},
			[LAB_OPT_RESULT_TOTAL_TAKEPROFIT]: {
				[COL_NAME]: lang(LAB_OPT_RESULT_TOTAL_TAKEPROFIT),
				[COL_SORT]: true,

			},
			[LAB_OPT_RESULT_TOTAL_STOPLOSS]: {
				[COL_NAME]: lang(LAB_OPT_RESULT_TOTAL_STOPLOSS),
				[COL_SORT]: true,

			},
			[LAB_OPT_RESULT_ACCOUNT]: {
				[COL_NAME]: lang(LAB_OPT_RESULT_ACCOUNT),
				[COL_SORT]: false,
				[COL_DECORATOR_IN]: (data) => {

					return <button type="button" className="btn btn-info" onClick={() => {

						this.AccountModal.modal();
						this.AccountModal.loadOrigin(data);
					}}>Info</button>;
				},
				[COL_STYLE]: { textAlign: 'center' },

			},
			[LAB_OPT_RESULT_CAMPAIGN]: {
				[COL_NAME]: lang(LAB_OPT_RESULT_CAMPAIGN),
				[COL_SORT]: false,
				[COL_DECORATOR_IN]: (data) => {

					return <button type="button" className="btn btn-info" onClick={() => {

						this.CampaignModal.modal();
						this.CampaignModal.loadOrigin(data);
					}}>Info</button>;
				},
				[COL_STYLE]: { textAlign: 'center' },

			},
			[LAB_OPT_RESULT_STRATEGY]: {
				[COL_NAME]: lang(LAB_OPT_RESULT_STRATEGY),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {
					return <button type="button" className="btn btn-info" onClick={() => {

						this.StrategyModal.modal();
						this.StrategyModal.setValue(data);
					}}>Info</button>;
				},
				[COL_STYLE]: { textAlign: 'center' },

			},

			[LAB_OPT_RESULT_EVENT]: {
				[COL_NAME]: lang(LAB_OPT_RESULT_EVENT),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {

					return <button type="button" className="btn btn-info" onClick={() => {

						this.EventModal.modal();
						this.EventModal.loadOrigin(data);
					}}>Info</button>;
				},
				[COL_STYLE]: { textAlign: 'center' },

			},
			[LAB_OPT_RESULT_DONE]: {
				[COL_NAME]: lang(LAB_OPT_RESULT_DONE),
				[COL_SORT]: true,

			},
			[LAB_OPT_RESULT_LOG]: {
				[COL_NAME]: lang(LAB_OPT_RESULT_LOG),
				[COL_SORT]: false,

			},



		}
		this.lab_opt_result_struct[STRUCT_FILTERS] = {

			[LAB_OPT_RESULT_OPTIMIZATION]: {
				[FILTER_NAME]: lang(LAB_OPT_RESULT_OPTIMIZATION),
				[FILTER_TYPE]: 'select',
			},
			[LAB_OPT_RESULT_DONE]: {
				[FILTER_NAME]: lang(LAB_OPT_RESULT_DONE),
				[FILTER_TYPE]: 'select',
			},
			[LAB_OPT_RESULT_PARAMS]: {
				[FILTER_NAME]: lang(LAB_OPT_RESULT_PARAMS),
				[FILTER_TYPE]: 'text',
				// [FILTER_LOGIC] : ['contain'],
				// [FILTER_OPERATION] : 'or'

			},
			[LAB_OPT_RESULT_BALANCE]: {
				[FILTER_NAME]: lang(LAB_OPT_RESULT_BALANCE),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<='],
			},

			[LAB_OPT_RESULT_MARGIN_BALANCE]: {
				[FILTER_NAME]: lang(LAB_OPT_RESULT_MARGIN_BALANCE),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<='],

			},
			[LAB_OPT_RESULT_UNRELIZE_MAX]: {
				[FILTER_NAME]: lang(LAB_OPT_RESULT_UNRELIZE_MAX),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<='],


			},
			[LAB_OPT_RESULT_INVEST_MAX]: {
				[FILTER_NAME]: lang(LAB_OPT_RESULT_INVEST_MAX),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<='],

			},

			[LAB_OPT_RESULT_TOTAL_POSITION]: {
				[FILTER_NAME]: lang(LAB_OPT_RESULT_TOTAL_POSITION),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<='],

			},
			[LAB_OPT_RESULT_TOTAL_LONG]: {
				[FILTER_NAME]: lang(LAB_OPT_RESULT_TOTAL_LONG),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<='],

			},
			[LAB_OPT_RESULT_TOTAL_SHORT]: {
				[FILTER_NAME]: lang(LAB_OPT_RESULT_TOTAL_SHORT),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<='],

			},

			[LAB_OPT_RESULT_TOTAL_TAKEPROFIT]: {
				[FILTER_NAME]: lang(LAB_OPT_RESULT_TOTAL_TAKEPROFIT),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<='],

			},
			[LAB_OPT_RESULT_TOTAL_STOPLOSS]: {
				[FILTER_NAME]: lang(LAB_OPT_RESULT_TOTAL_STOPLOSS),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<='],

			},

		}

		this.lab_opt_result_struct[STRUCT_EDIT] = {

			[LAB_OPT_RESULT_OPTIMIZATION]: {
				[EDIT_NAME]: lang(LAB_OPT_RESULT_OPTIMIZATION),
				[EDIT_TYPE]: 'Number',

			},
			[LAB_OPT_RESULT_PARAMS]: {
				[EDIT_NAME]: lang(LAB_OPT_RESULT_PARAMS),
				[EDIT_TYPE]: 'textarea',

			},
			[LAB_OPT_RESULT_STRATEGY]: {
				[EDIT_NAME]: lang(LAB_OPT_RESULT_STRATEGY),
				[EDIT_TYPE]: 'text',

			},
			[LAB_OPT_RESULT_BALANCE]: {
				[EDIT_NAME]: lang(LAB_OPT_RESULT_BALANCE),
				[EDIT_TYPE]: 'text',

			},
			[LAB_OPT_RESULT_MARGIN_BALANCE]: {
				[EDIT_NAME]: lang(LAB_OPT_RESULT_MARGIN_BALANCE),
				[EDIT_TYPE]: 'text',

			},
			[LAB_OPT_RESULT_UNRELIZE_MAX]: {
				[EDIT_NAME]: lang(LAB_OPT_RESULT_UNRELIZE_MAX),
				[EDIT_TYPE]: 'text',

			},
			[LAB_OPT_RESULT_INVEST_MAX]: {
				[EDIT_NAME]: lang(LAB_OPT_RESULT_INVEST_MAX),
				[EDIT_TYPE]: 'text',

			},
			[LAB_OPT_RESULT_ACCOUNT]: {
				[EDIT_NAME]: lang(LAB_OPT_RESULT_ACCOUNT),
				[EDIT_TYPE]: 'textarea',

			},
			[LAB_OPT_RESULT_CAMPAIGN]: {
				[EDIT_NAME]: lang(LAB_OPT_RESULT_CAMPAIGN),
				[EDIT_TYPE]: 'textarea',

			},
			[LAB_OPT_RESULT_EVENT]: {
				[EDIT_NAME]: lang(LAB_OPT_RESULT_EVENT),
				[EDIT_TYPE]: 'text',

			},
			[LAB_OPT_RESULT_INTERVAL_AVG]: {
				[EDIT_NAME]: lang(LAB_OPT_RESULT_INTERVAL_AVG),
				[EDIT_TYPE]: 'text',

			},
			[LAB_OPT_RESULT_INTERVAL_MAX]: {
				[EDIT_NAME]: lang(LAB_OPT_RESULT_INTERVAL_MAX),
				[EDIT_TYPE]: 'text',

			},
			[LAB_OPT_RESULT_TOTAL_POSITION]: {
				[EDIT_NAME]: lang(LAB_OPT_RESULT_TOTAL_POSITION),
				[EDIT_TYPE]: 'Number',

			},
			[LAB_OPT_RESULT_DONE]: {
				[EDIT_NAME]: lang(LAB_OPT_RESULT_DONE),
				[EDIT_TYPE]: 'select',

			},
			[LAB_OPT_RESULT_LOG]: {
				[EDIT_NAME]: lang(LAB_OPT_RESULT_LOG),
				[EDIT_TYPE]: 'textarea',

			},
		}

		this.lab_opt_result_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData}  ></FuncEditRow>
				</div>
			},
		};
		this.lab_opt_result_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: LAB_OPT_RESULT_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionLab_resultsView(),
			[DATA_KEY]: [LAB_OPT_RESULT_ID],
			[DATA_SORT]: {},
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Lab_opt_result()

		};

		this.invest = {};

	}

	permissionLab_resultsView() {
		return Object.assign(
			...Object.keys(this.lab_opt_result_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.lab_opt_result_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	onCache(item) {
		// data = JSON.stringify(data, null, 2);
		item = JSON.stringify(item, null, 2)

		const el = document.createElement('TEXTAREA');
		el.value = item;
		el.style.position = 'absolute';
		el.style.left = '-9999px';
		document.body.appendChild(el);
		el.select();
		document.execCommand('copy');
		document.body.removeChild(el);

	}

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.lab_opt_result_struct} autoload={false}>
					<FuncBar
						left={<FuncHideCol />}
						right={<><FuncDel /><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-striped table-resizable'></MainTable>
					<Pagination></Pagination>

				</Table>


				<AccountModal ref={c => this.AccountModal = c}></AccountModal>
				<CampaignModal ref={c => this.CampaignModal = c}></CampaignModal>
				<StrategyModal ref={c => this.StrategyModal = c}></StrategyModal>
				<EventModal ref={c => this.EventModal = c}></EventModal>


			</div>
		);
	}

	async getInvest() {

		var accountModel = new Lab_account();

		var accountData = await accountModel.read({});
		var reserveAccount = {};
		if (accountData['result']) {
			accountData = accountData['data'];
			accountData.map(item => {
				reserveAccount[item[LAB_ACCOUNT_ID]] = item[LAB_ACCOUNT_RESERVE]
			})
		}

		var campaignModel = new Lab_campaigns();
		return campaignModel.read({}).then(res => {
			if (res['result']) {
				var data = {};
				res = res['data'];
				res.map(item => {


					if (!isset(data[item[LAB_CAMPAIGN_ACCOUNT]])) {
						data[item[LAB_CAMPAIGN_ACCOUNT]] = [];
						data[item[LAB_CAMPAIGN_ACCOUNT]].push(item);
					} else {
						data[item[LAB_CAMPAIGN_ACCOUNT]].push(item);
					}
				})

				var dataResult = {};
				Object.keys(data).map(item => {
					dataResult[item] = 0;
					var totalInvestment = 0;
					data[item].map(row => {
						totalInvestment += row[LAB_CAMPAIGN_MONEY];
					})

					var reserve = 100 - Number(reserveAccount[item]);
					dataResult[item] = totalInvestment / reserve * 100;
				})

				return Promise.resolve(dataResult);
			}
		})
	}

	componentDidMount() {
		this.getInvest().then(res => {

			this.invest = res;
			this.table.map().then(res => {
				this.table.setFilter({
					[LAB_OPT_RESULT_OPTIMIZATION]: {
						"logic": "and",
						"data": {
							"=": App.parsed.optimization ? App.parsed.optimization : ''
						}
					}
				});

				this.table.filter();
			})
		})


	}





}

export default Opt_resultView 
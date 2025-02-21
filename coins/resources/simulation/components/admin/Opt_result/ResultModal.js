import React, { Component } from 'react'



import Table from '../../table/TableStatic'
import MainTable from '../../table/MainTable'
import Pagination from '../../table/Pagination'
import FuncBar from '../../table/FuncBar'

import FuncEditRow from '../../table/FuncEditRow'
import FuncAdd from '../../table/FuncAdd'
import FuncHideCol from '../../table/FuncHideCol'
import FuncDel from '../../table/FuncDel'
import FuncClear from '../../table/FuncClear'
import FuncRefresh from '../../table/FuncRefresh'
import FuncExport from '../../table/FuncExport'

import Lab_opt_result from '../../../model/admin/Lab_opt_result'
import AccountModal from './AccountModal'
import CampaignModal from './CampaignModal'
import StrategyModal from './StrategyModal'

class ResultModal extends Component {

	constructor(props) {
		super(props);
		this.id = makeId();


		this.show_db_struct = {};
		this.show_db_struct[STRUCT_FILTERS] = {}
		this.show_db_struct[STRUCT_COLUMNS] = {

			// [LAB_OPT_RESULT_OPTIMIZATION]: {
			// 	[COL_NAME]: lang(LAB_OPT_RESULT_OPTIMIZATION),
			// 	[COL_SORT]: true,

			// },


			[LAB_OPT_RESULT_BALANCE]: {
				[COL_NAME]: lang(LAB_OPT_RESULT_BALANCE),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {
					if (!data) return
					data = formatNumber(data.toFixed(3))
					return data;
				}

			},
			[LAB_OPT_RESULT_PARAMS]: {
				[COL_NAME]: lang(LAB_OPT_RESULT_PARAMS),
				[COL_SORT]: false,
				[COL_DECORATOR_IN]: (data) => {
					if (!data) return
					data = JSON.parse(data);
					return (
						<div>
							{
								Object.keys(data).map(item => <div key={item}>{item} : {data[item]}</div>)
							}
						</div>
					)
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

			// [LAB_OPT_RESULT_ACCOUNT]: {
			// 	[COL_NAME]: lang(LAB_OPT_RESULT_ACCOUNT),
			// 	[COL_SORT]: false,
			// 	[COL_DECORATOR_IN]: (data) => {

			// 		return <button type="button" className="btn btn-info" onClick={() => {
			// 			if (!data) return
			// 			this.AccountModal.modal();
			// 			this.AccountModal.loadOrigin(data);
			// 		}}>Info</button>;
			// 	},
			// 	[COL_STYLE]: { textAlign: 'center' },

			// },
			// [LAB_OPT_RESULT_CAMPAIGN]: {
			// 	[COL_NAME]: lang(LAB_OPT_RESULT_CAMPAIGN),
			// 	[COL_SORT]: false,
			// 	[COL_DECORATOR_IN]: (data) => {

			// 		return <button type="button" className="btn btn-info" onClick={() => {
			// 			if (!data) return
			// 			this.CampaignModal.modal();
			// 			this.CampaignModal.loadOrigin(data);
			// 		}}>Info</button>;
			// 	},
			// 	[COL_STYLE]: { textAlign: 'center' },

			// },
			// [LAB_OPT_RESULT_STRATEGY]: {
			// 	[COL_NAME]: lang(LAB_OPT_RESULT_STRATEGY),
			// 	[COL_SORT]: true,
			// 	[COL_DECORATOR_IN]: (data) => {
			// 		return <button type="button" className="btn btn-info" onClick={() => {
			// 			if (!data) return
			// 			this.StrategyModal.modal();
			// 			this.StrategyModal.loadOrigin(data);
			// 		}}>Info</button>;
			// 	},
			// 	[COL_STYLE]: { textAlign: 'center' },

			// },

			// [LAB_OPT_RESULT_EVENT]: {
			// 	[COL_NAME]: lang(LAB_OPT_RESULT_EVENT),
			// 	[COL_SORT]: true,
			// 	[COL_DECORATOR_IN]: (data) => {
			// 		return <button type="button" className="btn btn-info">Info</button>;
			// 	},
			// 	[COL_STYLE]: { textAlign: 'center' },

			// },
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

			},
			[LAB_OPT_RESULT_LOG]: {
				[COL_NAME]: lang(LAB_OPT_RESULT_LOG),
				[COL_SORT]: false,

			},



		}

		this.show_db_struct[STRUCT_EDIT] = {

			[LAB_OPT_RESULT_OPTIMIZATION]: {
				[FILTER_NAME]: lang(LAB_OPT_RESULT_OPTIMIZATION),
				[FILTER_TYPE]: 'select',
			},
		}

		this.show_db_struct[STRUCT_FILTERS] = {



		}


		this.show_db_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: '1sss222',
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionAccountDetailView(),
			[DATA_KEY]: [],
			[DATA_SORT]: {},
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: false,
			[FLAG_SETTING_ROWS]: false,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,



		};
	}

	permissionAccountDetailView() {
		return Object.assign(
			...Object.keys(this.show_db_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.show_db_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}




	async loadOrigin(data) {


		var labOptModal = new Lab_opt_result();
		var labOptData = await labOptModal.read({ [LAB_OPT_RESULT_OPTIMIZATION]: data });
		labOptData = labOptData['data'];

		this.table.setOrigin(labOptData);



	}

	modal(cmd = 'show') {
		if (cmd == 'hide') {
			$("#bladeModal" + this.id).modal('hide');
		} else {
			$("#bladeModal" + this.id).modal();
		}
	}


	render() {

		return (
			<>
				<div className="modal fade" id={"bladeModal" + this.id}>
					<div className="modal-dialog modal-lg modal-dialog-centered" style={{ maxWidth: '75%' }}>
						<div className="modal-content">

							<div className="modal-header">
								<h4 className="modal-title">Account</h4>
								<button type="button" className="close" data-dismiss="modal">&times;</button>
							</div>

							<div className="modal-body" style={{ textAlign: 'initial' }}>


								<Table ref={c => this.table = c} table={this.show_db_struct} autoload={false} loadOrigin={this.loadOrigin.bind(this)}>
									<FuncBar
										left={<>
											<div className='box_flex'>
												<FuncHideCol />
											</div>
										</>}
										right={<><FuncClear></FuncClear><FuncRefresh /><FuncExport /></>}></FuncBar>
									<MainTable className='table table-bordered table-striped table-resizable' minHeight={0}></MainTable>
									<Pagination></Pagination>

								</Table>
								<AccountModal ref={c => this.AccountModal = c}></AccountModal>
								<CampaignModal ref={c => this.CampaignModal = c}></CampaignModal>
								<StrategyModal ref={c => this.StrategyModal = c}></StrategyModal>


							</div>

							<div className="modal-footer">
								<button type="button" className="btn btn-danger" data-dismiss="modal">Close</button>
							</div>

						</div>
					</div>
				</div>

			</>
		)
	}




}
export default ResultModal
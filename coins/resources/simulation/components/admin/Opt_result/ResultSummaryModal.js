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

import Lab_account from '../../../model/admin/Lab_account'
import Lab_opt_result from '../../../model/admin/Lab_opt_result'

class ResultSummaryModal extends Component {

	constructor(props) {
		super(props);
		this.id = makeId();


		this.show_db_struct = {};
		this.show_db_struct[STRUCT_FILTERS] = {}
		this.show_db_struct[STRUCT_COLUMNS] = {

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
					data = formatNumber(data.toFixed(3)) ;
					return data;
				}

			},
			[LAB_OPT_RESULT_TOTAL_LONG]: {
				[COL_NAME]: lang(LAB_OPT_RESULT_TOTAL_LONG),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {
					if (!data) return
					data = formatNumber(data.toFixed(3)) ;
					return data;
				}

			},
			[LAB_OPT_RESULT_TOTAL_SHORT]: {
				[COL_NAME]: lang(LAB_OPT_RESULT_TOTAL_SHORT),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {
					if(data == 0) return 0
					if (!data) return
					data = formatNumber(data.toFixed(3)) ;
					return data;
				}

			},
			[LAB_OPT_RESULT_TOTAL_TAKEPROFIT]: {
				[COL_NAME]: lang(LAB_OPT_RESULT_TOTAL_TAKEPROFIT),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {
					if (!data) return
					data = formatNumber(data.toFixed(3)) ;
					return data;
				}

			},
			[LAB_OPT_RESULT_TOTAL_STOPLOSS]: {
				[COL_NAME]: lang(LAB_OPT_RESULT_TOTAL_STOPLOSS),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {
					if (!data) return
					data = formatNumber(data.toFixed(3)) ;
					return data;
				}

			},


		}

		this.show_db_struct[STRUCT_EDIT] = {


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




	async loadOrigin(id) {
		// console.log(id)
		var lab_opt_resultModal = new Lab_opt_result()

		let data = await lab_opt_resultModal.read({'lab_opt_result_optimization' : id})

		let totalWalletBalance = 0
		let totalMargintBalance = 0
		let totalUreMax = 0
		let totalInvestMax = 0
		let totalIntervalAVG = 0
		let totalIntervalMAX = 0
		let totalPosition = 0
		let totalLong = 0
		let totalShort = 0
		let totalTakeProfit = 0
		let totalStopLoss = 0
		let length = 0
		if(data['result']){
			data = data['data']
			length = data.length

			data.map(item => {
				totalWalletBalance += item[LAB_OPT_RESULT_BALANCE];
				totalMargintBalance += item[LAB_OPT_RESULT_MARGIN_BALANCE]
				totalUreMax += item[LAB_OPT_RESULT_UNRELIZE_MAX]
				totalInvestMax += item[LAB_OPT_RESULT_INVEST_MAX]
				totalIntervalAVG += item[LAB_OPT_RESULT_INTERVAL_AVG]
				totalIntervalMAX += item[LAB_OPT_RESULT_INTERVAL_MAX]
				totalPosition += item[LAB_OPT_RESULT_TOTAL_POSITION]
				totalLong += item[LAB_OPT_RESULT_TOTAL_LONG]
				totalShort += item[LAB_OPT_RESULT_TOTAL_SHORT]
				totalTakeProfit += item[LAB_OPT_RESULT_TOTAL_TAKEPROFIT]
				totalStopLoss += item[LAB_OPT_RESULT_TOTAL_STOPLOSS]
				
			})
		}

		let result = [
			{
				[LAB_OPT_RESULT_BALANCE] : totalWalletBalance / length,
				[LAB_OPT_RESULT_MARGIN_BALANCE] : totalMargintBalance / length,
				[LAB_OPT_RESULT_UNRELIZE_MAX] : totalUreMax / length,
				[LAB_OPT_RESULT_INVEST_MAX] : totalInvestMax / length,
				[LAB_OPT_RESULT_INTERVAL_AVG] : totalIntervalAVG / length,
				[LAB_OPT_RESULT_INTERVAL_MAX] : totalIntervalMAX / length,
				[LAB_OPT_RESULT_TOTAL_POSITION] : totalPosition / length,
				[LAB_OPT_RESULT_TOTAL_LONG] : totalLong / length,
				[LAB_OPT_RESULT_TOTAL_SHORT] : totalShort / length,
				[LAB_OPT_RESULT_TOTAL_TAKEPROFIT] : totalTakeProfit / length,
				[LAB_OPT_RESULT_TOTAL_STOPLOSS] : totalStopLoss / length,
			}
		]
		

		this.table.setOrigin(result);


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
					<div className="modal-dialog modal-lg modal-dialog-centered" style={{ maxWidth: '98%' }}>
						<div className="modal-content">

							<div className="modal-header">
								<h4 className="modal-title">Summary</h4>
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
export default ResultSummaryModal
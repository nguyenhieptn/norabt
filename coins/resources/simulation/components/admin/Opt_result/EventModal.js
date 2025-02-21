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


import Lab_results from '../../../model/admin/Lab_results'
class EventModal extends Component {

	constructor(props) {
		super(props);
		this.id = makeId();


		this.show_db_struct = {};
		this.show_db_struct[STRUCT_FILTERS] = {}
		this.show_db_struct[STRUCT_COLUMNS] = {

			[LAB_RESULT_SYMBOL]: {
				[COL_NAME]: lang(LAB_RESULT_SYMBOL),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {

					return <b>{data}</b>
				}

			},

			[LAB_RESULT_INTERVAL]: {
				// [COL_NAME]: lang(LAB_RESULT_INTERVAL),
				[COL_NAME]: 'Interval',
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: (data) => {
					// data = Math.round(data/60000);
					// if(data > 60)  	return <b style={{color : 'red'}} >{data}</b>;
					// return <b  >{data}</b>;

					data = Math.round(data / 1000);
					var d = Math.floor(data / (3600 * 24));
					var h = Math.floor(data % (3600 * 24) / 3600);
					var m = Math.floor(data % 3600 / 60);
			
					var dDisplay = d > 0 ? d + 'd ' : "";
					var hDisplay = h > 0 ? h + 'h ' : "";
					var mDisplay = m > 0 ? m + 'm' : 0;
					var color = '';
					if(h > 0 || d >0) color = 'red'
					var date = dDisplay + hDisplay + mDisplay;
					return <b style={{color : color}}>{date}</b> ;
				},
			},

			[LAB_RESULT_CAMPAIGN]: {
				[COL_NAME]: lang(LAB_RESULT_CAMPAIGN),
				[COL_SORT]: true,

			},
			[LAB_RESULT_ACCOUNT]: {
				[COL_NAME]: lang(LAB_RESULT_ACCOUNT),
				[COL_SORT]: true,

			},
			[LAB_RESULT_CONTAINER]: {
				[COL_NAME]: lang(LAB_RESULT_CONTAINER),
				[COL_SORT]: true,

			},
			[LAB_RESULT_STRATEGY]: {
				[COL_NAME]: lang(LAB_RESULT_STRATEGY),
				[COL_SORT]: true,

			},

			[LAB_RESULT_FLOW]: {
				[COL_NAME]: lang(LAB_RESULT_FLOW),
				[COL_SORT]: true,

			},

			[LAB_RESULT_CHART]: {
				[COL_NAME]: lang(LAB_RESULT_CHART),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},

			[LAB_RESULT_ENTER_TIME]: {
				[COL_NAME]: lang(LAB_RESULT_ENTER_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},
			[LAB_RESULT_ENTER_PRICE]: {
				[COL_NAME]: lang(LAB_RESULT_ENTER_PRICE),
				[COL_SORT]: true,
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},

			[LAB_RESULT_ORDER_TIME]: {
				[COL_NAME]: lang(LAB_RESULT_ORDER_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},
			[LAB_RESULT_ORDER_PRICE]: {
				[COL_NAME]: lang(LAB_RESULT_ORDER_PRICE),
				[COL_SORT]: true,
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},

			[LAB_RESULT_BUDGET]: {
				[COL_NAME]: lang(LAB_RESULT_BUDGET),
				[COL_SORT]: true,
				[COL_STYLE]: { whiteSpace: 'nowrap' },
				[COL_DECORATOR_IN]: data => data != null ? data.toFixed(3) + ' USDT' : ''
			},
			[LAB_RESULT_MARGIN]: {
				[COL_NAME]: lang(LAB_RESULT_MARGIN),
				[COL_SORT]: true,
			},

			[LAB_RESULT_REAL_PROFIT]: {
				[COL_NAME]: lang(LAB_RESULT_REAL_PROFIT),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => data != null ? data.toFixed(3) + ' %' : '',
				[COL_SUM]: true
			},

			[LAB_RESULT_REAL_PNL]: {
				[COL_NAME]: lang(LAB_RESULT_REAL_PNL),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => data != null ? data.toFixed(3) + ' USDT' : '',
				[COL_SUM]: true
			},

			[LAB_RESULT_EVENT_PROFIT]: {
				[COL_NAME]: lang(LAB_RESULT_EVENT_PROFIT),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => data != null ? data.toFixed(3) + ' %' : ''

			},

			[LAB_RESULT_PROFIT]: {
				[COL_NAME]: lang(LAB_RESULT_PROFIT),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var rowData = data[rowId];
					var data = rowData[colId];
					if (!data) return '';
					var style = { fontWeight: 'bold' };
					if (data >= 0) style['color'] = 'limegreen';
					if (data < 0) style['color'] = 'red';
					if (rowData[LAB_RESULT_PENDING] == 0) style['color'] = 'black';

					return <div style={style}>{(data != null && data != "") ? data.toFixed(3) + "%" : ""}</div>
				}

			},
			[LAB_RESULT_BASEPROFIT]: {
				[COL_NAME]: lang(LAB_RESULT_BASEPROFIT),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: (data) => (data != null && data != "") ? <div style={{ color: 'blue' }}> <b>{data.toFixed(3) + "%"}</b></div> : ""

			},

			[LAB_RESULT_PHASE]: {
				[COL_NAME]: lang(LAB_RESULT_PHASE),
				[COL_SORT]: true,
			},

			[LAB_RESULT_ORDER_PRICE]: {
				[COL_NAME]: lang(LAB_RESULT_ORDER_PRICE),
				[COL_SORT]: true,

			},
			[LAB_RESULT_HIGH]: {
				[COL_NAME]: lang(LAB_RESULT_HIGH),
				[COL_SORT]: true,

			},
			[LAB_RESULT_LOW]: {
				[COL_NAME]: lang(LAB_RESULT_LOW),
				[COL_SORT]: true,

			},

			[LAB_RESULT_TYPE]: {
				[COL_NAME]: lang(LAB_RESULT_TYPE),
				[COL_SORT]: true,

			},
			[LAB_RESULT_BASE]: {
				[COL_NAME]: lang(LAB_RESULT_BASE),
				[COL_SORT]: true,
			},

			[LAB_RESULT_BTC_WMA45_1D]: {
				[COL_NAME]: lang(LAB_RESULT_BTC_WMA45_1D),
				[COL_SORT]: true,
			},

			[LAB_RESULT_BTC_WMA45_1W]: {
				[COL_NAME]: lang(LAB_RESULT_BTC_WMA45_1W),
				[COL_SORT]: true,
			},

			[LAB_RESULT_LOG]: {
				[COL_NAME]: lang(LAB_RESULT_LOG),
				[COL_SORT]: true,

			},

			[LAB_RESULT_START_REASON]: {
				[COL_NAME]: lang(LAB_RESULT_START_REASON),
				[COL_SORT]: false,

			},
			[LAB_RESULT_PARAMS]: {
				[COL_NAME]: lang(LAB_RESULT_PARAMS),
				[COL_SORT]: false,

			},
			[LAB_RESULT_STATUS]: {
				[COL_NAME]: lang(LAB_RESULT_STATUS),
				[COL_SORT]: true,

			},
			[LAB_RESULT_MATCHED_PRICE]: {
				[COL_NAME]: lang(LAB_RESULT_MATCHED_PRICE),
				[COL_SORT]: true,

			},
			[LAB_RESULT_MATCHED_QTY]: {
				[COL_NAME]: lang(LAB_RESULT_MATCHED_QTY),
				[COL_SORT]: true,

			},
			[LAB_RESULT_MATCHED_EMA5]: {
				[COL_NAME]: lang(LAB_RESULT_MATCHED_EMA5),
				[COL_SORT]: true,

			},
			[LAB_RESULT_MATCHED_TIME]: {
				[COL_NAME]: lang(LAB_RESULT_MATCHED_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},

			[LAB_RESULT_SELL_PRICE]: {
				[COL_NAME]: lang(LAB_RESULT_SELL_PRICE),
				[COL_SORT]: true,

			},
			[LAB_RESULT_SELL_TIME]: {
				[COL_NAME]: lang(LAB_RESULT_SELL_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},

			[LAB_RESULT_FIRST_PRICE]: {
				[COL_NAME]: lang(LAB_RESULT_FIRST_PRICE),
				[COL_SORT]: true,

			},
			[LAB_RESULT_LAST_PRICE]: {
				[COL_NAME]: lang(LAB_RESULT_LAST_PRICE),
				[COL_SORT]: true,

			},

			[LAB_RESULT_PENDING]: {
				[COL_NAME]: lang(LAB_RESULT_PENDING),
				[COL_SORT]: true,

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




	async loadOrigin(row) {
		if(!row) return;
		var data = JSON.parse(row);

		var EventModal = new Lab_results();
		var AccountMapping = await EventModal.map();
		this.table.setMapping(AccountMapping['data']);
		this.table.setOrigin(data);


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
								<h4 className="modal-title">Event</h4>
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
export default EventModal
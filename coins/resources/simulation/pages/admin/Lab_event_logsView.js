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

import Lab_event_logs from '../../model/admin/Lab_event_logs'
import ElogProfitModal from '../../components/admin/ElogProfitModal'

class Lab_event_logsView extends Component {

	constructor(props) {
		super(props);

		this.lab_event_logs_struct = {};
		this.lab_event_logs_struct[STRUCT_FILTERS] = {}
		this.lab_event_logs_struct[STRUCT_COLUMNS] = {

			[LAB_ELOG_CAMPAIGN]: {
				[COL_NAME]: lang(LAB_ELOG_CAMPAIGN),
				[COL_SORT]: true,

			},
			[LAB_ELOG_SYMBOL]: {
				[COL_NAME]: lang(LAB_ELOG_SYMBOL),
				[COL_SORT]: true,

			},
			[LAB_ELOG_TIME]: {
				[COL_NAME]: lang(LAB_ELOG_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},
			[LAB_ELOG_CHART]: {
				[COL_NAME]: lang(LAB_ELOG_CHART),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }

			},
			[LAB_ELOG_RESULT]: {
				[COL_NAME]: lang(LAB_ELOG_RESULT),
				[COL_SORT]: true,

			},
			[LAB_ELOG_MAXPROFIT]: {
				[COL_NAME]: lang(LAB_ELOG_MAXPROFIT),
				[COL_SORT]: true,

			},
			[LAB_ELOG_MINPROFIT]: {
				[COL_NAME]: lang(LAB_ELOG_MINPROFIT),
				[COL_SORT]: true,

			},
			[LAB_ELOG_PROFIT]: {
				[COL_NAME]: lang(LAB_ELOG_PROFIT),
				[COL_SORT]: true,

			},
			[LAB_ELOG_BASEPROFIT]: {
				[COL_NAME]: lang(LAB_ELOG_BASEPROFIT),
				[COL_SORT]: true,

			},
			[LAB_ELOG_MATCHED]: {
				[COL_NAME]: lang(LAB_ELOG_MATCHED),
				[COL_SORT]: true,

			},
			[LAB_ELOG_BASE]: {
				[COL_NAME]: lang(LAB_ELOG_BASE),
				[COL_SORT]: true,

			},



		}
		this.lab_event_logs_struct[STRUCT_FILTERS] = {

			[LAB_ELOG_CAMPAIGN]: {
				[FILTER_NAME]: lang(LAB_ELOG_CAMPAIGN),
				[FILTER_TYPE]: 'select',
				[FILTER_ONCHANGE]: (e, input)=>{
					console.log('test');
					this.campaign = input.getValue();
				}
			},
			[LAB_ELOG_SYMBOL]: {
				[FILTER_NAME]: lang(LAB_ELOG_SYMBOL),
				[FILTER_TYPE]: 'select',
			},
			[LAB_ELOG_TIME]: {
				[FILTER_NAME]: lang(LAB_ELOG_TIME),
				[FILTER_TYPE]: 'date',
				[FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },
			},
			[LAB_ELOG_CHART]: {
				[FILTER_NAME]: lang(LAB_ELOG_CHART),
				[FILTER_TYPE]: 'text',
				[FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },
			},
			[LAB_ELOG_RESULT]: {
				[FILTER_NAME]: lang(LAB_ELOG_RESULT),
				[FILTER_TYPE]: 'text',
			},
			[LAB_ELOG_MATCHED]: {
				[FILTER_NAME]: lang(LAB_ELOG_MATCHED),
				[FILTER_TYPE]: 'text',
			},
			[LAB_ELOG_BASE]: {
				[FILTER_NAME]: lang(LAB_ELOG_BASE),
				[FILTER_TYPE]: 'text',
			},


		}

		this.lab_event_logs_struct[STRUCT_EDIT] = {

			[LAB_ELOG_CAMPAIGN]: {
				[EDIT_NAME]: lang(LAB_ELOG_CAMPAIGN),
				[EDIT_TYPE]: 'Number',

			},
			[LAB_ELOG_SYMBOL]: {
				[EDIT_NAME]: lang(LAB_ELOG_SYMBOL),
				[EDIT_TYPE]: 'text',

			},
			[LAB_ELOG_TIME]: {
				[EDIT_NAME]: lang(LAB_ELOG_TIME),
				[EDIT_TYPE]: 'date',

			},
			[LAB_ELOG_CHART]: {
				[EDIT_NAME]: lang(LAB_ELOG_CHART),
				[EDIT_TYPE]: 'text',

			},
			[LAB_ELOG_RESULT]: {
				[EDIT_NAME]: lang(LAB_ELOG_RESULT),
				[EDIT_TYPE]: 'text',

			},
			[LAB_ELOG_MATCHED]: {
				[EDIT_NAME]: lang(LAB_ELOG_MATCHED),
				[EDIT_TYPE]: 'Number',

			},
			[LAB_ELOG_BASE]: {
				[EDIT_NAME]: lang(LAB_ELOG_BASE),
				[EDIT_TYPE]: 'text',

			},


		}

		this.lab_event_logs_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData} />
				</div>
			}
		};
		this.lab_event_logs_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: LAB_EVENT_LOGS_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: { [LAB_ELOG_BASE]: true },
			[DATA_PERMIT_COL]: this.permissionLab_event_logsView(),
			[DATA_KEY]: [LAB_ELOG_ID],
			[DATA_SORT]: { [LAB_ELOG_ID]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Lab_event_logs()

		};


	}

	permissionLab_event_logsView() {
		return Object.assign(
			...Object.keys(this.lab_event_logs_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.lab_event_logs_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.lab_event_logs_struct} autoload={true}>
					<FuncBar
						left={<><FuncHideCol />
						<div className='btn button btn-info btn-sm' onClick={()=>{
							if(!this.campaign || this.campaign == ''){
								showLog('Please select a campain');
								return;
							}

							this.elogProfit.getData(this.campaign);
							this.elogProfit.modal();

						}}>Profit Chart</div>
						</>}
						right={<><FuncAdd /><FuncDel /><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-striped table-resizable'></MainTable>
					<Pagination></Pagination>

				</Table>

				<ElogProfitModal ref ={c => this.elogProfit = c}></ElogProfitModal>


			</div>
		);
	}
}

export default Lab_event_logsView
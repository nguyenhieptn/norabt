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

import Testnet_event_logs from '../../model/admin/Testnet_event_logs'

class Testnet_event_logsView extends Component {

	constructor(props) {
		super(props);

		this.testnet_event_logs_struct = {};
		this.testnet_event_logs_struct[STRUCT_FILTERS] = {}
		this.testnet_event_logs_struct[STRUCT_COLUMNS] = {

			[TESTNET_ELOG_CAMPAIGN]: {
				[COL_NAME]: lang(TESTNET_ELOG_CAMPAIGN),
				[COL_SORT]: true,

			},
			[TESTNET_ELOG_SYMBOL]: {
				[COL_NAME]: lang(TESTNET_ELOG_SYMBOL),
				[COL_SORT]: true,

			},
			[TESTNET_ELOG_TIME]: {
				[COL_NAME]: lang(TESTNET_ELOG_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},
			[TESTNET_ELOG_RESULT]: {
				[COL_NAME]: lang(TESTNET_ELOG_RESULT),
				[COL_SORT]: true,

			},
			[TESTNET_ELOG_MAXPROFIT]: {
				[COL_NAME]: lang(TESTNET_ELOG_MAXPROFIT),
				[COL_SORT]: true,

			},
			[TESTNET_ELOG_MINPROFIT]: {
				[COL_NAME]: lang(TESTNET_ELOG_MINPROFIT),
				[COL_SORT]: true,

			},
			[TESTNET_ELOG_PROFIT]: {
				[COL_NAME]: lang(TESTNET_ELOG_PROFIT),
				[COL_SORT]: true,

			},
			[TESTNET_ELOG_BASEPROFIT]: {
				[COL_NAME]: lang(TESTNET_ELOG_BASEPROFIT),
				[COL_SORT]: true,

			},
			[TESTNET_ELOG_STATUS]: {
				[COL_NAME]: lang(TESTNET_ELOG_STATUS),
				[COL_SORT]: true,

			},
			[TESTNET_ELOG_MATCHED]: {
				[COL_NAME]: lang(TESTNET_ELOG_MATCHED),
				[COL_SORT]: true,

			},
			[TESTNET_ELOG_BASE]: {
				[COL_NAME]: lang(TESTNET_ELOG_BASE),
				[COL_SORT]: true,

			},



		}
		this.testnet_event_logs_struct[STRUCT_FILTERS] = {

			[TESTNET_ELOG_CAMPAIGN]: {
				[FILTER_NAME]: lang(TESTNET_ELOG_CAMPAIGN),
				[FILTER_TYPE]: 'select',
			},
			[TESTNET_ELOG_SYMBOL]: {
				[FILTER_NAME]: lang(TESTNET_ELOG_SYMBOL),
				[FILTER_TYPE]: 'select',
			},
			[TESTNET_ELOG_TIME]: {
				[FILTER_NAME]: lang(TESTNET_ELOG_TIME),
				[FILTER_TYPE]: 'date',
				[FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },
			},
			[TESTNET_ELOG_RESULT]: {
				[FILTER_NAME]: lang(TESTNET_ELOG_RESULT),
				[FILTER_TYPE]: 'text',
			},
			
			[TESTNET_ELOG_STATUS]: {
				[FILTER_NAME]: lang(TESTNET_ELOG_STATUS),
				[FILTER_TYPE]: 'select',
			},
			


		}

		this.testnet_event_logs_struct[STRUCT_EDIT] = {

			
			[TESTNET_ELOG_RESULT]: {
				[EDIT_NAME]: lang(TESTNET_ELOG_RESULT),
				[EDIT_TYPE]: 'text',

			},
			
			[TESTNET_ELOG_BASE]: {
				[EDIT_NAME]: lang(TESTNET_ELOG_BASE),
				[EDIT_TYPE]: 'text',

			},


		}

		this.testnet_event_logs_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData} />
				</div>
			}
		};
		this.testnet_event_logs_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: TESTNET_EVENT_LOGS_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {[TESTNET_ELOG_BASE]: true},
			[DATA_PERMIT_COL]: this.permissionTestnet_event_logsView(),
			[DATA_KEY]: [TESTNET_ELOG_ID],
			[DATA_SORT]: { [TESTNET_ELOG_ID]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Testnet_event_logs()

		};


	}

	permissionTestnet_event_logsView() {
		return Object.assign(
			...Object.keys(this.testnet_event_logs_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.testnet_event_logs_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.testnet_event_logs_struct} autoload={true}>
					<FuncBar
						left={<FuncHideCol />}
						right={<><FuncAdd /><FuncDel /><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-striped table-resizable'></MainTable>
					<Pagination></Pagination>

				</Table>


			</div>
		);
	}
}

export default Testnet_event_logsView
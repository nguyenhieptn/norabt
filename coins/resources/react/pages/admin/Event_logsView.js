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

import Event_logs from '../../model/admin/Event_logs'

class Event_logsView extends Component {

	constructor(props) {
		super(props);

		this.event_logs_struct = {};
		this.event_logs_struct[STRUCT_FILTERS] = {}
		this.event_logs_struct[STRUCT_COLUMNS] = {

			[ELOG_SYMBOL]: {
				[COL_NAME]: lang(ELOG_SYMBOL),
				[COL_SORT]: true,

			},
			[ELOG_TIME]: {
				[COL_NAME]: lang(ELOG_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},
			[ELOG_RESULT]: {
				[COL_NAME]: lang(ELOG_RESULT),
				[COL_SORT]: true,

			},
			[ELOG_MATCHED]: {
				[COL_NAME]: lang(ELOG_MATCHED),
				[COL_SORT]: true,

			},
			[ELOG_BASE]: {
				[COL_NAME]: lang(ELOG_BASE),
				[COL_SORT]: true,

			},



		}
		this.event_logs_struct[STRUCT_FILTERS] = {

			[ELOG_SYMBOL]: {
				[FILTER_NAME]: lang(ELOG_SYMBOL),
				[FILTER_TYPE]: 'text',
			},
			[ELOG_TIME]: {
				[FILTER_NAME]: lang(ELOG_TIME),
				[FILTER_TYPE]: 'date',
				[FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },
			},
			[ELOG_RESULT]: {
				[FILTER_NAME]: lang(ELOG_RESULT),
				[FILTER_TYPE]: 'text',
			},
			[ELOG_MATCHED]: {
				[FILTER_NAME]: lang(ELOG_MATCHED),
				[FILTER_TYPE]: 'select',
			},
			[ELOG_BASE]: {
				[FILTER_NAME]: lang(ELOG_BASE),
				[FILTER_TYPE]: 'text',
			},


		}

		this.event_logs_struct[STRUCT_EDIT] = {


			[ELOG_RESULT]: {
				[EDIT_NAME]: lang(ELOG_RESULT),
				[EDIT_TYPE]: 'text',

			},

			[ELOG_BASE]: {
				[EDIT_NAME]: lang(ELOG_BASE),
				[EDIT_TYPE]: 'text',

			},


		}

		this.event_logs_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData} />
				</div>
			}
		};
		this.event_logs_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: EVENT_LOGS_TABLE,
			[DATA_SPECIAL]: { symbol: App.symbol },
			[DATA_HIDDEN_COL]: { [ELOG_BASE]: true },
			[DATA_PERMIT_COL]: this.permissionEvent_logsView(),
			[DATA_KEY]: [ELOG_ID],
			[DATA_SORT]: { [ELOG_ID]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Event_logs()

		};


	}

	permissionEvent_logsView() {
		return Object.assign(
			...Object.keys(this.event_logs_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.event_logs_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.event_logs_struct} autoload={true}>
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

export default Event_logsView
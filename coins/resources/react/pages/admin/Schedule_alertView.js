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
import FuncClone from '../../components/table/FuncClone'

import Schedule_alert from '../../model/admin/Schedule_alert'

class Schedule_alertView extends Component {

	constructor(props) {
		super(props);

		this.schedule_alert_struct = {};
		this.schedule_alert_struct[STRUCT_FILTERS] = {}
		this.schedule_alert_struct[STRUCT_COLUMNS] = {

			[SCHEDULE_AL_NAME]: {
				[COL_NAME]: lang(SCHEDULE_AL_NAME),
				[COL_SORT]: true,

			},
			
			[SCHEDULE_AL_ICON]: {
				[COL_NAME]: lang(SCHEDULE_AL_ICON),
				[COL_SORT]: false,
				[COL_STYLE]: {textAlign:'center'}

			},
			[SCHEDULE_AL_TIME]: {
				[COL_NAME]: lang(SCHEDULE_AL_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},
			[SCHEDULE_AL_BEFORE]: {
				[COL_NAME]: lang(SCHEDULE_AL_BEFORE),
				[COL_SORT]: true,
				

			},
			[SCHEDULE_AL_CONTENT]: {
				[COL_NAME]: lang(SCHEDULE_AL_CONTENT),
				[COL_SORT]: false,
			},
			
			[SCHEDULE_AL_NOTE]: {
				[COL_NAME]: lang(SCHEDULE_AL_NOTE),
				[COL_SORT]: false,

			},
			[SCHEDULE_AL_DONE]: {
				[COL_NAME]: lang(SCHEDULE_AL_DONE),
				[COL_SORT]: true,
				[COL_STYLE]: {textAlign:'center', fontWeight:'bold'}

			},
			[SCHEDULE_AL_GROUPID]: {
				[COL_NAME]: lang(SCHEDULE_AL_GROUPID),
				[COL_SORT]: false,

			},
			[SCHEDULE_AL_BOTID]: {
				[COL_NAME]: lang(SCHEDULE_AL_BOTID),
				[COL_SORT]: false,

			},



		}
		this.schedule_alert_struct[STRUCT_FILTERS] = {

			[SCHEDULE_AL_NAME]: {
				[FILTER_NAME]: lang(SCHEDULE_AL_NAME),
				[FILTER_TYPE]: 'text',
			},
			[SCHEDULE_AL_DONE]: {
				[FILTER_NAME]: lang(SCHEDULE_AL_DONE),
				[FILTER_TYPE]: 'select',
			},


		}

		this.schedule_alert_struct[STRUCT_EDIT] = {

			[SCHEDULE_AL_NAME]: {
				[EDIT_NAME]: lang(SCHEDULE_AL_NAME),
				[EDIT_TYPE]: 'text',

			},
			[SCHEDULE_AL_GROUPID]: {
				[EDIT_NAME]: lang(SCHEDULE_AL_GROUPID),
				[EDIT_TYPE]: 'text',

			},
			[SCHEDULE_AL_BOTID]: {
				[EDIT_NAME]: lang(SCHEDULE_AL_BOTID),
				[EDIT_TYPE]: 'text',

			},
			[SCHEDULE_AL_ICON]: {
				[EDIT_NAME]: lang(SCHEDULE_AL_ICON),
				[EDIT_TYPE]: 'select',

			},
			[SCHEDULE_AL_TIME]: {
				[EDIT_NAME]: lang(SCHEDULE_AL_TIME),
				[EDIT_TYPE]: 'date',

			},
			[SCHEDULE_AL_BEFORE]: {
				[EDIT_NAME]: lang(SCHEDULE_AL_BEFORE),
				[EDIT_TYPE]: 'Number',
				[EDIT_DEFAULT]: 30,
				[EDIT_DES]: 'The time in minutes before the event occurs'

			},
			[SCHEDULE_AL_CONTENT]: {
				[EDIT_NAME]: lang(SCHEDULE_AL_CONTENT),
				[EDIT_TYPE]: 'textarea',

			},
			
			[SCHEDULE_AL_NOTE]: {
				[EDIT_NAME]: lang(SCHEDULE_AL_NOTE),
				[EDIT_TYPE]: 'textarea',

			},
			[SCHEDULE_AL_DONE]: {
				[EDIT_NAME]: lang(SCHEDULE_AL_DONE),
				[EDIT_TYPE]: 'select',
				[EDIT_DEFAULT]: '0'

			},


		}

		this.schedule_alert_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData} />
				</div>
			}
		};
		this.schedule_alert_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: SCHEDULE_ALERT_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionSchedule_alertView(),
			[DATA_KEY]: [SCHEDULE_AL_ID],
			[DATA_SORT]: { [SCHEDULE_AL_TIME]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Schedule_alert()

		};


	}

	permissionSchedule_alertView() {
		return Object.assign(
			...Object.keys(this.schedule_alert_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.schedule_alert_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.schedule_alert_struct} autoload={true}>
					<FuncBar
						left={<FuncHideCol />}
						right={<><FuncAdd /><FuncClone></FuncClone><FuncDel /><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-striped table-resizable'></MainTable>
					<Pagination></Pagination>

				</Table>


			</div>
		);
	}
}

export default Schedule_alertView
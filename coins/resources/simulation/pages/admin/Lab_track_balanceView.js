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

import Lab_track_balance from '../../model/admin/Lab_track_balance'

class Lab_track_balanceView extends Component {

	constructor(props) {
		super(props);

		this.lab_track_balance_struct = {};
		this.lab_track_balance_struct[STRUCT_FILTERS] = {}
		this.lab_track_balance_struct[STRUCT_COLUMNS] = {

			[LAB_TRACK_BL_ACCOUNT]: {
				[COL_NAME]: lang(LAB_TRACK_BL_ACCOUNT),
				[COL_SORT]: true,

			},
			[LAB_TRACK_BL_TIME]: {
				[COL_NAME]: lang(LAB_TRACK_BL_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},
			[LAB_TRACK_BL_MARGIN_BL]: {
				[COL_NAME]: lang(LAB_TRACK_BL_MARGIN_BL),
				[COL_SORT]: true,

			},
			[LAB_TRACK_BL_INVEST]: {
				[COL_NAME]: lang(LAB_TRACK_BL_INVEST),
				[COL_SORT]: true,

			},
			[LAB_TRACK_BL_UNREALIZE]: {
				[COL_NAME]: lang(LAB_TRACK_BL_UNREALIZE),
				[COL_SORT]: true,

			},
			[LAB_TRACK_BL_BALANCE]: {
				[COL_NAME]: lang(LAB_TRACK_BL_BALANCE),
				[COL_SORT]: true,

			},



		}
		this.lab_track_balance_struct[STRUCT_FILTERS] = {

			[LAB_TRACK_BL_ACCOUNT]: {
				[FILTER_NAME]: lang(LAB_TRACK_BL_ACCOUNT),
				[FILTER_TYPE]: 'text',
			},
			[LAB_TRACK_BL_TIME]: {
				[FILTER_NAME]: lang(LAB_TRACK_BL_TIME),
				[FILTER_TYPE]: 'date',
				[FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },
			},
			[LAB_TRACK_BL_MARGIN_BL]: {
				[FILTER_NAME]: lang(LAB_TRACK_BL_MARGIN_BL),
				[FILTER_TYPE]: 'number',
			},
			[LAB_TRACK_BL_INVEST]: {
				[FILTER_NAME]: lang(LAB_TRACK_BL_INVEST),
				[FILTER_TYPE]: 'number',
			},
			[LAB_TRACK_BL_UNREALIZE]: {
				[FILTER_NAME]: lang(LAB_TRACK_BL_UNREALIZE),
				[FILTER_TYPE]: 'number',
			},
			[LAB_TRACK_BL_BALANCE]: {
				[FILTER_NAME]: lang(LAB_TRACK_BL_BALANCE),
				[FILTER_TYPE]: 'number',
			},


		}

		this.lab_track_balance_struct[STRUCT_EDIT] = {

			[LAB_TRACK_BL_ACCOUNT]: {
				[EDIT_NAME]: lang(LAB_TRACK_BL_ACCOUNT),
				[EDIT_TYPE]: 'Number',

			},
			[LAB_TRACK_BL_TIME]: {
				[EDIT_NAME]: lang(LAB_TRACK_BL_TIME),
				[EDIT_TYPE]: 'date',

			},
			[LAB_TRACK_BL_MARGIN_BL]: {
				[EDIT_NAME]: lang(LAB_TRACK_BL_MARGIN_BL),
				[EDIT_TYPE]: 'number',

			},
			[LAB_TRACK_BL_INVEST]: {
				[EDIT_NAME]: lang(LAB_TRACK_BL_INVEST),
				[EDIT_TYPE]: 'number',

			},
			[LAB_TRACK_BL_UNREALIZE]: {
				[EDIT_NAME]: lang(LAB_TRACK_BL_UNREALIZE),
				[EDIT_TYPE]: 'number',

			},
			[LAB_TRACK_BL_BALANCE]: {
				[EDIT_NAME]: lang(LAB_TRACK_BL_BALANCE),
				[EDIT_TYPE]: 'number',

			},


		}

		this.lab_track_balance_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData} />
				</div>
			}
		};
		this.lab_track_balance_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: LAB_TRACK_BALANCE_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionLab_track_balanceView(),
			[DATA_KEY]: [LAB_TRACK_BL_ID],
			[DATA_SORT]: { [LAB_TRACK_BL_ID]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Lab_track_balance()

		};


	}

	permissionLab_track_balanceView() {
		return Object.assign(
			...Object.keys(this.lab_track_balance_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.lab_track_balance_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.lab_track_balance_struct} autoload={true}>
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

export default Lab_track_balanceView
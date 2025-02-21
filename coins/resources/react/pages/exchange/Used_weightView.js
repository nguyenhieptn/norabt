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

import Used_weight from '../../model/admin/Used_weight'

class Used_weightView extends Component {

	constructor(props) {
		super(props);

		this.used_weight_struct = {};
		this.used_weight_struct[STRUCT_FILTERS] = {}
		this.used_weight_struct[STRUCT_COLUMNS] = {

			[USED_W_DOMAIN]: {
				[COL_NAME]: lang(USED_W_DOMAIN),
				[COL_SORT]: true,

			},
			[USED_W_URL]: {
				[COL_NAME]: lang(USED_W_URL),
				[COL_SORT]: false,

			},
			[USED_W_VALUE]: {
				[COL_NAME]: lang(USED_W_VALUE),
				[COL_SORT]: true,

			},
			[USED_W_TIME]: {
				[COL_NAME]: lang(USED_W_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},



		}
		this.used_weight_struct[STRUCT_FILTERS] = {

			[USED_W_DOMAIN]: {
				[FILTER_NAME]: lang(USED_W_DOMAIN),
				[FILTER_TYPE]: 'text',
			},
			[USED_W_VALUE]: {
				[FILTER_NAME]: lang(USED_W_VALUE),
				[FILTER_TYPE]: 'text',
			},


		}

		this.used_weight_struct[STRUCT_EDIT] = {

			[USED_W_DOMAIN]: {
				[EDIT_NAME]: lang(USED_W_DOMAIN),
				[EDIT_TYPE]: 'text',

			},
			[USED_W_URL]: {
				[EDIT_NAME]: lang(USED_W_URL),
				[EDIT_TYPE]: 'textarea',

			},
			[USED_W_VALUE]: {
				[EDIT_NAME]: lang(USED_W_VALUE),
				[EDIT_TYPE]: 'Number',

			},
			[USED_W_TIME]: {
				[EDIT_NAME]: lang(USED_W_TIME),
				[EDIT_TYPE]: 'date',

			},


		}

		this.used_weight_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData} />
				</div>
			}
		};
		this.used_weight_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: USED_WEIGHT_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionUsed_weightView(),
			[DATA_KEY]: [USED_W_ID],
			[DATA_SORT]: { [USED_W_ID]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: false,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Used_weight()

		};


	}

	permissionUsed_weightView() {
		return Object.assign(
			...Object.keys(this.used_weight_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.used_weight_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.used_weight_struct} autoload={true}>
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

export default Used_weightView
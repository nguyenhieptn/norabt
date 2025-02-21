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

import Tele_group from '../../model/admin/Tele_group'

class Tele_groupView extends Component {

	constructor(props) {
		super(props);

		this.tele_group_struct = {};
		this.tele_group_struct[STRUCT_FILTERS] = {}
		this.tele_group_struct[STRUCT_COLUMNS] = {

			[TELE_GROUP_NAME]: {
				[COL_NAME]: lang(TELE_GROUP_NAME),
				[COL_SORT]: true,

			},
			[TELE_GROUP_CODE]: {
				[COL_NAME]: lang(TELE_GROUP_CODE),
				[COL_SORT]: true,

			},
			[TELE_GROUP_ROLE]: {
				[COL_NAME]: lang(TELE_GROUP_ROLE),
				[COL_SORT]: true,

			},



		}
		this.tele_group_struct[STRUCT_FILTERS] = {

			[TELE_GROUP_NAME]: {
				[FILTER_NAME]: lang(TELE_GROUP_NAME),
				[FILTER_TYPE]: 'text',
			},
			[TELE_GROUP_CODE]: {
				[FILTER_NAME]: lang(TELE_GROUP_CODE),
				[FILTER_TYPE]: 'text',
			},
			[TELE_GROUP_ROLE]: {
				[FILTER_NAME]: lang(TELE_GROUP_ROLE),
				[FILTER_TYPE]: 'select',
			},


		}

		this.tele_group_struct[STRUCT_EDIT] = {

			[TELE_GROUP_NAME]: {
				[EDIT_NAME]: lang(TELE_GROUP_NAME),
				[EDIT_TYPE]: 'text',

			},
			[TELE_GROUP_CODE]: {
				[EDIT_NAME]: lang(TELE_GROUP_CODE),
				[EDIT_TYPE]: 'text',

			},
			[TELE_GROUP_ROLE]: {
				[EDIT_NAME]: lang(TELE_GROUP_ROLE),
				[EDIT_TYPE]: 'select',

			},


		}

		this.tele_group_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData} />
				</div>
			}
		};
		this.tele_group_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: TELE_GROUP_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionTele_groupView(),
			[DATA_KEY]: [TELE_GROUP_ID],
			[DATA_SORT]: { [TELE_GROUP_ID]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Tele_group()

		};


	}

	permissionTele_groupView() {
		return Object.assign(
			...Object.keys(this.tele_group_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.tele_group_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.tele_group_struct} autoload={true}>
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

export default Tele_groupView
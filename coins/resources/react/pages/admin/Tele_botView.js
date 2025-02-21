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

import Tele_bot from '../../model/admin/Tele_bot'

class Tele_botView extends Component {

	constructor(props) {
		super(props);

		this.tele_bot_struct = {};
		this.tele_bot_struct[STRUCT_FILTERS] = {}
		this.tele_bot_struct[STRUCT_COLUMNS] = {

			[TELE_BOT_NAME]: {
				[COL_NAME]: lang(TELE_BOT_NAME),
				[COL_SORT]: true,

			},
			[TELE_BOT_CODE]: {
				[COL_NAME]: lang(TELE_BOT_CODE),
				[COL_SORT]: true,

			},
			[TELE_BOT_ROLE]: {
				[COL_NAME]: lang(TELE_BOT_ROLE),
				[COL_SORT]: true,

			},



		}
		this.tele_bot_struct[STRUCT_FILTERS] = {

			[TELE_BOT_NAME]: {
				[FILTER_NAME]: lang(TELE_BOT_NAME),
				[FILTER_TYPE]: 'text',
			},
			[TELE_BOT_CODE]: {
				[FILTER_NAME]: lang(TELE_BOT_CODE),
				[FILTER_TYPE]: 'text',
			},
			[TELE_BOT_ROLE]: {
				[FILTER_NAME]: lang(TELE_BOT_ROLE),
				[FILTER_TYPE]: 'select',
			},


		}

		this.tele_bot_struct[STRUCT_EDIT] = {

			[TELE_BOT_NAME]: {
				[EDIT_NAME]: lang(TELE_BOT_NAME),
				[EDIT_TYPE]: 'text',

			},
			[TELE_BOT_CODE]: {
				[EDIT_NAME]: lang(TELE_BOT_CODE),
				[EDIT_TYPE]: 'text',

			},
			[TELE_BOT_ROLE]: {
				[EDIT_NAME]: lang(TELE_BOT_ROLE),
				[EDIT_TYPE]: 'select',

			},


		}

		this.tele_bot_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData} />
				</div>
			}
		};
		this.tele_bot_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: TELE_BOT_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionTele_botView(),
			[DATA_KEY]: [TELE_BOT_ID],
			[DATA_SORT]: { [TELE_BOT_ID]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Tele_bot()

		};


	}

	permissionTele_botView() {
		return Object.assign(
			...Object.keys(this.tele_bot_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.tele_bot_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.tele_bot_struct} autoload={true}>
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

export default Tele_botView
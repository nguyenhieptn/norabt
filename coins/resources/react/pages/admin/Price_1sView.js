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

import Price_1s from '../../model/admin/Price_1s'

class Price_1sView extends Component {

	constructor(props) {
		super(props);

		this.price_1s_struct = {};
		this.price_1s_struct[STRUCT_FILTERS] = {}
		this.price_1s_struct[STRUCT_COLUMNS] = {

			[PRICE_1S_ID]: {
				[COL_NAME]: lang(PRICE_1S_ID),
				[COL_SORT]: true,

			},
			[PRICE_1S_SYMBOL]: {
				[COL_NAME]: lang(PRICE_1S_SYMBOL),
				[COL_SORT]: true,

			},
			[PRICE_1S_TIME]: {
				[COL_NAME]: lang(PRICE_1S_TIME),
				[COL_SORT]: true,

			},
			[PRICE_1S_CLOSE]: {
				[COL_NAME]: lang(PRICE_1S_CLOSE),
				[COL_SORT]: true,

			},
			[PRICE_1S_LOW]: {
				[COL_NAME]: lang(PRICE_1S_LOW),
				[COL_SORT]: true,

			},
			[PRICE_1S_HIGH]: {
				[COL_NAME]: lang(PRICE_1S_HIGH),
				[COL_SORT]: true,

			},
			[PRICE_1S_OPEN]: {
				[COL_NAME]: lang(PRICE_1S_OPEN),
				[COL_SORT]: true,

			},
			[PRICE_1S_OPEN_TIME]: {
				[COL_NAME]: lang(PRICE_1S_OPEN_TIME),
				[COL_SORT]: true,

			},
			[PRICE_1S_CLOSE_TIME]: {
				[COL_NAME]: lang(PRICE_1S_CLOSE_TIME),
				[COL_SORT]: true,

			},



		}
		this.price_1s_struct[STRUCT_FILTERS] = {

			[PRICE_1S_ID]: {
				[FILTER_NAME]: lang(PRICE_1S_ID),
				[FILTER_TYPE]: 'text',
			},
			[PRICE_1S_SYMBOL]: {
				[FILTER_NAME]: lang(PRICE_1S_SYMBOL),
				[FILTER_TYPE]: 'text',
			},
			[PRICE_1S_CLOSE]: {
				[FILTER_NAME]: lang(PRICE_1S_CLOSE),
				[FILTER_TYPE]: 'text',
			},
			[PRICE_1S_LOW]: {
				[FILTER_NAME]: lang(PRICE_1S_LOW),
				[FILTER_TYPE]: 'text',
			},
			[PRICE_1S_HIGH]: {
				[FILTER_NAME]: lang(PRICE_1S_HIGH),
				[FILTER_TYPE]: 'text',
			},
			[PRICE_1S_OPEN]: {
				[FILTER_NAME]: lang(PRICE_1S_OPEN),
				[FILTER_TYPE]: 'text',
			},


		}

		this.price_1s_struct[STRUCT_EDIT] = {

			[PRICE_1S_ID]: {
				[EDIT_NAME]: lang(PRICE_1S_ID),
				[EDIT_TYPE]: 'Number',

			},
			[PRICE_1S_SYMBOL]: {
				[EDIT_NAME]: lang(PRICE_1S_SYMBOL),
				[EDIT_TYPE]: 'text',

			},
			[PRICE_1S_TIME]: {
				[EDIT_NAME]: lang(PRICE_1S_TIME),
				[EDIT_TYPE]: 'Number',

			},
			[PRICE_1S_CLOSE]: {
				[EDIT_NAME]: lang(PRICE_1S_CLOSE),
				[EDIT_TYPE]: 'text',

			},
			[PRICE_1S_LOW]: {
				[EDIT_NAME]: lang(PRICE_1S_LOW),
				[EDIT_TYPE]: 'text',

			},
			[PRICE_1S_HIGH]: {
				[EDIT_NAME]: lang(PRICE_1S_HIGH),
				[EDIT_TYPE]: 'text',

			},
			[PRICE_1S_OPEN]: {
				[EDIT_NAME]: lang(PRICE_1S_OPEN),
				[EDIT_TYPE]: 'text',

			},
			[PRICE_1S_OPEN_TIME]: {
				[EDIT_NAME]: lang(PRICE_1S_OPEN_TIME),
				[EDIT_TYPE]: 'Number',

			},
			[PRICE_1S_CLOSE_TIME]: {
				[EDIT_NAME]: lang(PRICE_1S_CLOSE_TIME),
				[EDIT_TYPE]: 'Number',

			},


		}

		this.price_1s_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData} />
				</div>
			}
		};
		this.price_1s_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: PRICE_1S_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionPrice_1sView(),
			[DATA_KEY]: [PRICE_1S_ID],
			[DATA_SORT]: { [PRICE_1S_ID]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Price_1s()

		};


	}

	permissionPrice_1sView() {
		return Object.assign(
			...Object.keys(this.price_1s_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.price_1s_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.price_1s_struct} autoload={true}>
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

export default Price_1sView
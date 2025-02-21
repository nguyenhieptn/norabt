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

import Change_24h from '../../model/admin/Change_24h'

class Change_24hView extends Component {

	constructor(props) {
		super(props);

		this.change_24h_struct = {};
		this.change_24h_struct[STRUCT_FILTERS] = {}
		this.change_24h_struct[STRUCT_COLUMNS] = {

			[CHANGE24H_TIME]: {
				[COL_NAME]: lang(CHANGE24H_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},
			[CHANGE24H_TOTAL]: {
				[COL_NAME]: lang(CHANGE24H_TOTAL),
				[COL_SORT]: true,

			},
			[CHANGE24H_DOWN]: {
				[COL_NAME]: lang(CHANGE24H_DOWN),
				[COL_SORT]: true,

			},
			[CHANGE24H_UP]: {
				[COL_NAME]: lang(CHANGE24H_UP),
				[COL_SORT]: true,

			},
			[CHANGE24H_KEEP]: {
				[COL_NAME]: lang(CHANGE24H_KEEP),
				[COL_SORT]: true,

			},
			[CHANGE24H_BTC_ASC]: {
				[COL_NAME]: lang(CHANGE24H_BTC_ASC),
				[COL_SORT]: true,

			},
			[CHANGE24H_BTC_DESC]: {
				[COL_NAME]: lang(CHANGE24H_BTC_DESC),
				[COL_SORT]: true,

			},
			[CHANGE24H_BTC_KEEP]: {
				[COL_NAME]: lang(CHANGE24H_BTC_KEEP),
				[COL_SORT]: true,

			},
			[CHANGE24H_UP_10]: {
				[COL_NAME]: lang(CHANGE24H_UP_10),
				[COL_SORT]: true,

			},
			[CHANGE24H_UP_7_10]: {
				[COL_NAME]: lang(CHANGE24H_UP_7_10),
				[COL_SORT]: true,

			},
			[CHANGE24H_UP_5_7]: {
				[COL_NAME]: lang(CHANGE24H_UP_5_7),
				[COL_SORT]: true,

			},
			[CHANGE24H_UP_3_5]: {
				[COL_NAME]: lang(CHANGE24H_UP_3_5),
				[COL_SORT]: true,

			},
			[CHANGE24H_UP_0_3]: {
				[COL_NAME]: lang(CHANGE24H_UP_0_3),
				[COL_SORT]: true,

			},
			[CHANGE24H_DOWN_0_3]: {
				[COL_NAME]: lang(CHANGE24H_DOWN_0_3),
				[COL_SORT]: true,

			},
			[CHANGE24H_DOWN_3_5]: {
				[COL_NAME]: lang(CHANGE24H_DOWN_3_5),
				[COL_SORT]: true,

			},
			[CHANGE24H_DOWN_5_7]: {
				[COL_NAME]: lang(CHANGE24H_DOWN_5_7),
				[COL_SORT]: true,

			},
			[CHANGE24H_DOWN_7_10]: {
				[COL_NAME]: lang(CHANGE24H_DOWN_7_10),
				[COL_SORT]: true,

			},
			[CHANGE24H_DOWN_10]: {
				[COL_NAME]: lang(CHANGE24H_DOWN_10),
				[COL_SORT]: true,

			},



		}
		this.change_24h_struct[STRUCT_FILTERS] = {

			[CHANGE24H_TIME]: {
				[FILTER_NAME]: lang(CHANGE24H_TIME),
				[FILTER_TYPE]: 'date',
			},
			[CHANGE24H_DOWN]: {
				[FILTER_NAME]: lang(CHANGE24H_DOWN),
				[FILTER_TYPE]: 'text',
			},
			[CHANGE24H_UP]: {
				[FILTER_NAME]: lang(CHANGE24H_UP),
				[FILTER_TYPE]: 'text',
			},
			[CHANGE24H_KEEP]: {
				[FILTER_NAME]: lang(CHANGE24H_KEEP),
				[FILTER_TYPE]: 'text',
			},
			[CHANGE24H_BTC_ASC]: {
				[FILTER_NAME]: lang(CHANGE24H_BTC_ASC),
				[FILTER_TYPE]: 'text',
			},
			[CHANGE24H_BTC_DESC]: {
				[FILTER_NAME]: lang(CHANGE24H_BTC_DESC),
				[FILTER_TYPE]: 'text',
			},
			[CHANGE24H_BTC_KEEP]: {
				[FILTER_NAME]: lang(CHANGE24H_BTC_KEEP),
				[FILTER_TYPE]: 'text',
			},
			[CHANGE24H_UP_10]: {
				[FILTER_NAME]: lang(CHANGE24H_UP_10),
				[FILTER_TYPE]: 'text',
			},
			[CHANGE24H_UP_7_10]: {
				[FILTER_NAME]: lang(CHANGE24H_UP_7_10),
				[FILTER_TYPE]: 'text',
			},
			[CHANGE24H_UP_5_7]: {
				[FILTER_NAME]: lang(CHANGE24H_UP_5_7),
				[FILTER_TYPE]: 'text',
			},
			[CHANGE24H_UP_3_5]: {
				[FILTER_NAME]: lang(CHANGE24H_UP_3_5),
				[FILTER_TYPE]: 'text',
			},
			[CHANGE24H_UP_0_3]: {
				[FILTER_NAME]: lang(CHANGE24H_UP_0_3),
				[FILTER_TYPE]: 'text',
			},
			[CHANGE24H_DOWN_0_3]: {
				[FILTER_NAME]: lang(CHANGE24H_DOWN_0_3),
				[FILTER_TYPE]: 'text',
			},
			[CHANGE24H_DOWN_3_5]: {
				[FILTER_NAME]: lang(CHANGE24H_DOWN_3_5),
				[FILTER_TYPE]: 'text',
			},
			[CHANGE24H_DOWN_5_7]: {
				[FILTER_NAME]: lang(CHANGE24H_DOWN_5_7),
				[FILTER_TYPE]: 'text',
			},
			[CHANGE24H_DOWN_7_10]: {
				[FILTER_NAME]: lang(CHANGE24H_DOWN_7_10),
				[FILTER_TYPE]: 'text',
			},
			[CHANGE24H_DOWN_10]: {
				[FILTER_NAME]: lang(CHANGE24H_DOWN_10),
				[FILTER_TYPE]: 'text',
			},


		}

		this.change_24h_struct[STRUCT_EDIT] = {

			[CHANGE24H_TIME]: {
				[EDIT_NAME]: lang(CHANGE24H_TIME),
				[EDIT_TYPE]: 'date',

			},
			[CHANGE24H_DOWN]: {
				[EDIT_NAME]: lang(CHANGE24H_DOWN),
				[EDIT_TYPE]: 'Number',

			},
			[CHANGE24H_UP]: {
				[EDIT_NAME]: lang(CHANGE24H_UP),
				[EDIT_TYPE]: 'Number',

			},
			[CHANGE24H_KEEP]: {
				[EDIT_NAME]: lang(CHANGE24H_KEEP),
				[EDIT_TYPE]: 'Number',

			},
			[CHANGE24H_BTC_ASC]: {
				[EDIT_NAME]: lang(CHANGE24H_BTC_ASC),
				[EDIT_TYPE]: 'Number',

			},
			[CHANGE24H_BTC_DESC]: {
				[EDIT_NAME]: lang(CHANGE24H_BTC_DESC),
				[EDIT_TYPE]: 'Number',

			},
			[CHANGE24H_BTC_KEEP]: {
				[EDIT_NAME]: lang(CHANGE24H_BTC_KEEP),
				[EDIT_TYPE]: 'Number',

			},
			[CHANGE24H_UP_10]: {
				[EDIT_NAME]: lang(CHANGE24H_UP_10),
				[EDIT_TYPE]: 'Number',

			},
			[CHANGE24H_UP_7_10]: {
				[EDIT_NAME]: lang(CHANGE24H_UP_7_10),
				[EDIT_TYPE]: 'Number',

			},
			[CHANGE24H_UP_5_7]: {
				[EDIT_NAME]: lang(CHANGE24H_UP_5_7),
				[EDIT_TYPE]: 'Number',

			},
			[CHANGE24H_UP_3_5]: {
				[EDIT_NAME]: lang(CHANGE24H_UP_3_5),
				[EDIT_TYPE]: 'Number',

			},
			[CHANGE24H_UP_0_3]: {
				[EDIT_NAME]: lang(CHANGE24H_UP_0_3),
				[EDIT_TYPE]: 'Number',

			},
			[CHANGE24H_DOWN_0_3]: {
				[EDIT_NAME]: lang(CHANGE24H_DOWN_0_3),
				[EDIT_TYPE]: 'Number',

			},
			[CHANGE24H_DOWN_3_5]: {
				[EDIT_NAME]: lang(CHANGE24H_DOWN_3_5),
				[EDIT_TYPE]: 'Number',

			},
			[CHANGE24H_DOWN_5_7]: {
				[EDIT_NAME]: lang(CHANGE24H_DOWN_5_7),
				[EDIT_TYPE]: 'Number',

			},
			[CHANGE24H_DOWN_7_10]: {
				[EDIT_NAME]: lang(CHANGE24H_DOWN_7_10),
				[EDIT_TYPE]: 'Number',

			},
			[CHANGE24H_DOWN_10]: {
				[EDIT_NAME]: lang(CHANGE24H_DOWN_10),
				[EDIT_TYPE]: 'Number',

			},


		}

		this.change_24h_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData} />
				</div>
			}
		};
		this.change_24h_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: CHANGE_24H_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionChange_24hView(),
			[DATA_KEY]: [CHANGE24H_ID],
			[DATA_SORT]: { [CHANGE24H_ID]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Change_24h()

		};


	}

	permissionChange_24hView() {
		return Object.assign(
			...Object.keys(this.change_24h_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.change_24h_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.change_24h_struct} autoload={true}>
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

export default Change_24hView
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

import System_info from '../../model/admin/System_info'

class System_infoView extends Component {

	constructor(props) {
		super(props);

		this.system_info_struct = {};
		this.system_info_struct[STRUCT_FILTERS] = {}
		this.system_info_struct[STRUCT_COLUMNS] = {


			[SYS_NAME]: {
				[COL_NAME]: lang(SYS_NAME),
				[COL_SORT]: true,


			},
			[SYS_CPU]: {
				[COL_NAME]: lang(SYS_CPU),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {
					return (<span style={data <= 50 ? { color: 'limegreen' } : { color: 'red' }}>{`${data} %`}</span>)
				},

			},
			[SYS_RAM]: {
				[COL_NAME]: lang(SYS_RAM),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {
					return (<span style={data <= 50 ? { color: 'limegreen' } : { color: 'red' }}>{`${data} %`}</span>)
				},

			},
			[SYS_TOTAL_RAM]: {
				[COL_NAME]: lang(SYS_TOTAL_RAM),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {
					var totalRam = Math.round((data / 1000000) * 10) / 10;
					return (`${totalRam} G`)
				},

			},
			[SYS_SWAP]: {
				[COL_NAME]: lang(SYS_SWAP),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {
					return (<span style={data <= 50 ? { color: 'limegreen' } : { color: 'red' }}>{`${data} %`}</span>)
				},

			},
			[SYS_TOTAL_SWAP]: {
				[COL_NAME]: lang(SYS_TOTAL_SWAP),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {
					var totalSwap = Math.round((data / 1000000) * 10) / 10;
					return (`${totalSwap} G`)
				},

			},
			[SYS_DISK]: {
				[COL_NAME]: lang(SYS_DISK),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {
				
					return (<span style={data <= 50 ? { color: 'limegreen' } : { color: 'red' }}>{`${data} %`}</span>)
				},

			},
			
			[SYS_TOTAL_DISK]: {
				[COL_NAME]: lang(SYS_TOTAL_DISK),
				[COL_SORT]: true,

			},
			[SYS_NOTE]: {
				[COL_NAME]: lang(SYS_NOTE),
				[COL_SORT]: false,

			},



		}
		this.system_info_struct[STRUCT_FILTERS] = {

			[SYS_NAME]: {
				[FILTER_NAME]: lang(SYS_NAME),
				[FILTER_TYPE]: 'text',
			},
			[SYS_CPU]: {
				[FILTER_NAME]: lang(SYS_CPU),
				[FILTER_TYPE]: 'text',
			},
			[SYS_RAM]: {
				[FILTER_NAME]: lang(SYS_RAM),
				[FILTER_TYPE]: 'text',
			},
			[SYS_SWAP]: {
				[FILTER_NAME]: lang(SYS_SWAP),
				[FILTER_TYPE]: 'text',
			},
			[SYS_DISK]: {
				[FILTER_NAME]: lang(SYS_DISK),
				[FILTER_TYPE]: 'text',
			},
			[SYS_TOTAL_RAM]: {
				[FILTER_NAME]: lang(SYS_TOTAL_RAM),
				[FILTER_TYPE]: 'text',
			},
			[SYS_TOTAL_SWAP]: {
				[FILTER_NAME]: lang(SYS_TOTAL_SWAP),
				[FILTER_TYPE]: 'text',
			},
			[SYS_TOTAL_DISK]: {
				[FILTER_NAME]: lang(SYS_TOTAL_DISK),
				[FILTER_TYPE]: 'text',
			},
			[SYS_NOTE]: {
				[FILTER_NAME]: lang(SYS_NOTE),
				[FILTER_TYPE]: 'text',
			},


		}

		this.system_info_struct[STRUCT_EDIT] = {

			[SYS_NAME]: {
				[EDIT_NAME]: lang(SYS_NAME),
				[EDIT_TYPE]: 'text',

			},
			[SYS_CPU]: {
				[EDIT_NAME]: lang(SYS_CPU),
				[EDIT_TYPE]: 'Number',

			},
			[SYS_RAM]: {
				[EDIT_NAME]: lang(SYS_RAM),
				[EDIT_TYPE]: 'Number',

			},
			[SYS_SWAP]: {
				[EDIT_NAME]: lang(SYS_SWAP),
				[EDIT_TYPE]: 'Number',

			},
			[SYS_DISK]: {
				[EDIT_NAME]: lang(SYS_DISK),
				[EDIT_TYPE]: 'Number',

			},
			[SYS_TOTAL_RAM]: {
				[EDIT_NAME]: lang(SYS_TOTAL_RAM),
				[EDIT_TYPE]: 'Number',

			},
			[SYS_TOTAL_SWAP]: {
				[EDIT_NAME]: lang(SYS_TOTAL_SWAP),
				[EDIT_TYPE]: 'Number',

			},
			[SYS_TOTAL_DISK]: {
				[EDIT_NAME]: lang(SYS_TOTAL_DISK),
				[EDIT_TYPE]: 'text',

			},
			[SYS_NOTE]: {
				[EDIT_NAME]: lang(SYS_NOTE),
				[EDIT_TYPE]: 'text',

			},


		}

		this.system_info_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData} />
				</div>
			}
		};
		this.system_info_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: SYSTEM_INFO_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionSystem_infoView(),
			[DATA_KEY]: [SYS_ID],
			[DATA_SORT]: { [SYS_ID]: 'asc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new System_info()

		};


	}

	permissionSystem_infoView() {
		return Object.assign(
			...Object.keys(this.system_info_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.system_info_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.system_info_struct} autoload={true}>
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

export default System_infoView
import React, { Component } from 'react'
import Table from '../../components/table/Table'
import FilterBar from '../../components/table/FilterBar'
import MainTable from '../../components/table/MainTable'
import Pagination from '../../components/table/Pagination'
import FuncBar from '../../components/table/FuncBar'

import FuncAdd from '../../components/table/FuncAdd'
import FuncHideCol from '../../components/table/FuncHideCol'
import FuncDel from '../../components/table/FuncDel'
import FuncClear from '../../components/table/FuncClear'
import FuncRefresh from '../../components/table/FuncRefresh'
import FuncExport from '../../components/table/FuncExport'
import Mailer_resultModel from '../../model/mailer/Mailer_resultModel'
import FuncEditRow from '../../components/table/FuncEditRow'

class Mailer_result extends Component {

	constructor(props) {
		super(props);

		this.mailer_result_struct = {};
		this.mailer_result_struct[STRUCT_FILTERS] = {}
		this.mailer_result_struct[STRUCT_COLUMNS] = {

			//[MRESULT_MAILER]: {
			//     [COL_NAME]: lang(MRESULT_MAILER),
			//     [COL_SORT]: true,
			// },
			[MRESULT_CONTENT]: {
				[COL_NAME]: lang(MRESULT_CONTENT),
				[COL_SORT]: false,
				[COL_DECORATOR_IN]: (data) => { return <div dangerouslySetInnerHTML={{ __html: output_secure(HtmlDecode(data)) }}></div> }
			},
			[MRESULT_TO]: {
				[COL_NAME]: lang(MRESULT_TO),
				[COL_SORT]: true,

			},
			[MRESULT_FROM]: {
				[COL_NAME]: lang(MRESULT_FROM),
				[COL_SORT]: true,

			},
			[MRESULT_TIME]: {
				[COL_NAME]: lang(MRESULT_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: function (data) { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }

			},
			[MRESULT_RESULT]: {
				[COL_NAME]: lang(MRESULT_RESULT),
				[COL_SORT]: true,

			},
			[MRESULT_LOG]: {
				[COL_NAME]: lang(MRESULT_LOG),
				[COL_SORT]: false,
				[COL_DECORATOR_IN]: function (data) { return HtmlDecode(data) }
			},



		}
		this.mailer_result_struct[STRUCT_FILTERS] = {

			[MRESULT_MAILER]: {
				[FILTER_NAME]: lang(MRESULT_MAILER),
				[FILTER_TYPE]: 'text',
			},
			[MRESULT_TO]: {
				[FILTER_NAME]: lang(MRESULT_TO),
				[FILTER_TYPE]: 'text',
			},
			[MRESULT_FROM]: {
				[FILTER_NAME]: lang(MRESULT_FROM),
				[FILTER_TYPE]: 'text',
			},
			[MRESULT_TIME]: {
				[FILTER_NAME]: lang(MRESULT_TIME),
				[FILTER_TYPE]: 'date',
			},
			[MRESULT_RESULT]: {
				[FILTER_NAME]: lang(MRESULT_RESULT),
				[FILTER_TYPE]: 'text',
			},


		}

		this.mailer_result_struct[STRUCT_EDIT] = {




		}

		this.mailer_result_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return [
					<FuncEditRow key={1} rowData={rowData} />
				]
			}
		};
		this.mailer_result_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: MAILER_RESULT_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionMailer_result(),
			[DATA_KEY]: [MRESULT_ID],
			[DATA_SORT]: { [MRESULT_ID]: 'desc' },
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,
			model: new Mailer_resultModel()

		};


	}

	permissionMailer_result() {
		return Object.assign(
			...Object.keys(this.mailer_result_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.mailer_result_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	render() {
		return (
			<div>
				<Table table={this.mailer_result_struct} autoload={true}>
					<FuncBar
						left={<FuncHideCol />}
						right={<><FuncAdd /><FuncDel /><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-resizable'></MainTable>
					<Pagination></Pagination>

				</Table>
			</div>
		);
	}
}

export default Mailer_result
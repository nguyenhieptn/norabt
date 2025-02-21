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

import Lab_doc from '../../model/admin/Lab_doc'

class Lab_docView extends Component {

	constructor(props) {
		super(props);

		this.lab_doc_struct = {};
		this.lab_doc_struct[STRUCT_FILTERS] = {}
		this.lab_doc_struct[STRUCT_COLUMNS] = {

			[LAB_DOC_NAME]: {
				[COL_NAME]: lang(LAB_DOC_NAME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (col, row, data) => {
					var rowData = data[row];
					var linkDoc = rowData[LAB_DOC_LINK];
					var docName = rowData[col];
					return <div style={{ cursor: 'pointer', color: 'blue', textDecoration: 'underline' }} onClick={() => window.open(linkDoc)}>
						<b>{docName}</b>
					</div>
				}

			},


			[LAB_DOC_GROUP]: {
				[COL_NAME]: lang(LAB_DOC_GROUP),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' }

			},
			[LAB_DOC_DESC]: {
				[COL_NAME]: lang(LAB_DOC_DESC),
				[COL_SORT]: true,

			},
			[LAB_DOC_USER]: {
				[COL_NAME]: lang(LAB_DOC_USER),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' }

			},



		}
		this.lab_doc_struct[STRUCT_FILTERS] = {

			[LAB_DOC_NAME]: {
				[FILTER_NAME]: lang(LAB_DOC_NAME),
				[FILTER_TYPE]: 'text',
			},
			[LAB_DOC_LINK]: {
				[FILTER_NAME]: lang(LAB_DOC_LINK),
				[FILTER_TYPE]: 'text',
			},
			[LAB_DOC_DESC]: {
				[FILTER_NAME]: lang(LAB_DOC_DESC),
				[FILTER_TYPE]: 'text',
			},
			[LAB_DOC_GROUP]: {
				[FILTER_NAME]: lang(LAB_DOC_GROUP),
				[FILTER_TYPE]: 'select',
			},
			[LAB_DOC_USER]: {
				[FILTER_NAME]: lang(LAB_DOC_USER),
				[FILTER_TYPE]: 'select',
			},


		}

		this.lab_doc_struct[STRUCT_EDIT] = {

			[LAB_DOC_NAME]: {
				[EDIT_NAME]: lang(LAB_DOC_NAME),
				[EDIT_TYPE]: 'text',

			},
			[LAB_DOC_LINK]: {
				[EDIT_NAME]: lang(LAB_DOC_LINK),
				[EDIT_TYPE]: 'text',

			},
			[LAB_DOC_DESC]: {
				[EDIT_NAME]: lang(LAB_DOC_DESC),
				[EDIT_TYPE]: 'text',

			},
			[LAB_DOC_GROUP]: {
				[EDIT_NAME]: lang(LAB_DOC_GROUP),
				[EDIT_TYPE]: 'text',

			},
			[LAB_DOC_USER]: {
				[EDIT_NAME]: lang(LAB_DOC_USER),
				[EDIT_TYPE]: 'select',

			},


		}

		this.lab_doc_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
						<FuncEditRow rowData={rowData} />
					</div>

			}
		};
		this.lab_doc_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: LAB_DOC_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionLab_docView(),
			[DATA_KEY]: [LAB_DOC_ID],
			[DATA_SORT]: { [LAB_DOC_ID]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: App.user[AUTHEN_GROUP] == 0 ? true : false,
			[FLAG_SETTING_ROWS]: App.user[AUTHEN_GROUP] == 0 ? true : false,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Lab_doc()

		};


	}

	permissionLab_docView() {
		return Object.assign(
			...Object.keys(this.lab_doc_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.lab_doc_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
			{ [LAB_DOC_USER]: App.user[AUTHEN_GROUP] == 0 ? 'Write' : 'Read' }
		)
	}

	renderButtonAdd() {
		if (App.user[AUTHEN_GROUP] == 0) {
			return (
				<>
					<FuncAdd />
					<FuncDel />
				</>

			)
		}
	}

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.lab_doc_struct} autoload={true}>
					<FuncBar
						left={<FuncHideCol />}
						right={<>{this.renderButtonAdd()} <FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-striped table-resizable'></MainTable>
					<Pagination></Pagination>

				</Table>


			</div>
		);
	}
}

export default Lab_docView
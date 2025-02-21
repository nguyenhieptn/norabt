import React, { Component } from 'react'



import Table from '../../table/TableStatic'
import MainTable from '../../table/MainTable'
import Pagination from '../../table/Pagination'
import FuncBar from '../../table/FuncBar'

import FuncEditRow from '../../table/FuncEditRow'
import FuncAdd from '../../table/FuncAdd'
import FuncHideCol from '../../table/FuncHideCol'
import FuncDel from '../../table/FuncDel'
import FuncClear from '../../table/FuncClear'
import FuncRefresh from '../../table/FuncRefresh'
import FuncExport from '../../table/FuncExport'

import Lab_account from '../../../model/admin/Lab_account'

class AccountModal extends Component {

	constructor(props) {
		super(props);
		this.id = makeId();


		this.show_db_struct = {};
		this.show_db_struct[STRUCT_FILTERS] = {}
		this.show_db_struct[STRUCT_COLUMNS] = {

			[LAB_ACCOUNT_NAME]: {
				[COL_NAME]: lang(LAB_ACCOUNT_NAME),
				[COL_SORT]: true,

			},
			[LAB_ACCOUNT_RUNNING]: {
				[COL_NAME]: lang(LAB_ACCOUNT_RUNNING),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => {
					return data == 1 ? <b style={{ color: 'limegreen' }}>Running</b> : <b style={{ color: 'red' }}>Stopped</b>
				}

			},
			[LAB_ACCOUNT_BALANCE]: {
				[COL_NAME]: lang(LAB_ACCOUNT_BALANCE),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => Number(data).toFixed(3)

			},
			[LAB_ACCOUNT_RESERVE]: {
				[COL_NAME]: lang(LAB_ACCOUNT_RESERVE),
				[COL_SORT]: true,

			},
			[LAB_ACCOUNT_COMPOUND]: {
				[COL_NAME]: lang(LAB_ACCOUNT_COMPOUND),
				[COL_SORT]: true,

			},
			[LAB_ACCOUNT_MARGIN_TYPE]: {
				[COL_NAME]: lang(LAB_ACCOUNT_MARGIN_TYPE),
				[COL_SORT]: false,

			},
			[LAB_ACCOUNT_TRACK_BALANCE]: {
				[COL_NAME]: lang(LAB_ACCOUNT_TRACK_BALANCE),
				[COL_SORT]: false,

			},
			[LAB_ACCOUNT_SYNC]: {
				[COL_NAME]: lang(LAB_ACCOUNT_SYNC),
				[COL_SORT]: false,

			},
			[LAB_ACCOUNT_NOTE]: {
				[COL_NAME]: lang(LAB_ACCOUNT_NOTE),
				[COL_SORT]: false,

			},
			[LAB_ACCOUNT_LOG]: {
				[COL_NAME]: lang(LAB_ACCOUNT_LOG),
				[COL_SORT]: false,

			},


		}

		this.show_db_struct[STRUCT_EDIT] = {


		}

		this.show_db_struct[STRUCT_FILTERS] = {



		}


		this.show_db_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: '1sss222',
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionAccountDetailView(),
			[DATA_KEY]: [],
			[DATA_SORT]: {},
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: false,
			[FLAG_SETTING_ROWS]: false,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,



		};
	}

	permissionAccountDetailView() {
		return Object.assign(
			...Object.keys(this.show_db_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.show_db_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}




	async loadOrigin(row) {
		var data = JSON.parse(row);

		var AccountModal = new Lab_account();
		var AccountMapping = await AccountModal.map();
		this.table.setMapping(AccountMapping['data']);
		this.table.setOrigin([data]);


	}

	modal(cmd = 'show') {
		if (cmd == 'hide') {
			$("#bladeModal" + this.id).modal('hide');
		} else {
			$("#bladeModal" + this.id).modal();
		}
	}


	render() {

		return (
			<>
				<div className="modal fade" id={"bladeModal" + this.id}>
					<div className="modal-dialog modal-lg modal-dialog-centered" style={{ maxWidth: '98%' }}>
						<div className="modal-content">

							<div className="modal-header">
								<h4 className="modal-title">Account</h4>
								<button type="button" className="close" data-dismiss="modal">&times;</button>
							</div>

							<div className="modal-body" style={{ textAlign: 'initial' }}>


								<Table ref={c => this.table = c} table={this.show_db_struct} autoload={false} loadOrigin={this.loadOrigin.bind(this)}>
									<FuncBar
										left={<>
											<div className='box_flex'>
												<FuncHideCol />
											</div>
										</>}
										right={<><FuncClear></FuncClear><FuncRefresh /><FuncExport /></>}></FuncBar>
									<MainTable className='table table-bordered table-striped table-resizable' minHeight={0}></MainTable>
									<Pagination></Pagination>

								</Table>


							</div>

							<div className="modal-footer">
								<button type="button" className="btn btn-danger" data-dismiss="modal">Close</button>
							</div>

						</div>
					</div>
				</div>

			</>
		)
	}




}
export default AccountModal
import React, { Component } from 'react'
import Accounts from '../../model/admin/Accounts';




import Table from '../../components/table/TableStatic'
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

class AccountFeeModal extends Component {

	constructor(props) {
		super(props);
		this.id = makeId();

		this.state = {
			account: {}
		}

		this.account_detail_struct = {};
		this.account_detail_struct[STRUCT_FILTERS] = {}
		this.account_detail_struct[STRUCT_COLUMNS] = {

			'symbol': {
				[COL_NAME]: lang('symbol'),
				[COL_SORT]: true,

			},

			'income': {
				[COL_NAME]: lang('income'),
				[COL_SORT]: true,
				[COL_SUM] : true

			},

			'time': {
				[COL_NAME]: lang('time'),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' , textAlign : 'center' }

			},





		}


		this.account_detail_struct[STRUCT_EDIT] = {


		}

		this.account_detail_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: '123aqv',
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionAccountDetailView(),
			[DATA_KEY]: ['symbol'],
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
			...Object.keys(this.account_detail_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.account_detail_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	modal(cmd = 'show') {
		if (cmd == 'hide') {
			$("#bladeModal" + this.id).modal('hide');
		} else {
			$("#bladeModal" + this.id).modal();
		}
	}

	async setAccount(id, name) {

		var account = {
			[ACCOUNT_ID]: id,
			[ACCOUNT_NAME]: name,
		}

		this.setState({
			account
		}, () => this.loadOrigin())



	}




	async loadOrigin() {

		var accountModel = new Accounts();

		var incom = await accountModel.getIncom(this.state.account[ACCOUNT_ID] , "FUNDING_FEE");
		if (!incom['result']) {
			error_handle(incom);
			return;
		}
		incom = incom['data'];

		var data = Object.values(incom);
		 data.pop();


		console.log(data)

		this.table.setOrigin(data);


	}



	render() {


		return (
			<>
				<div className="modal fade" id={"bladeModal" + this.id}>
					<div className="modal-dialog modal-lg modal-dialog-centered" style={{ minWidth: '1200px' }}>
						<div className="modal-content">

							<div className="modal-header">
								<h4 className="modal-title">{this.state.account[ACCOUNT_NAME]}</h4>
								<button type="button" className="close" data-dismiss="modal">&times;</button>
							</div>

							<div className="modal-body" style={{ textAlign: 'initial' }}>

								<Table ref={c => this.table = c} table={this.account_detail_struct} autoload={false} loadOrigin={this.loadOrigin.bind(this)}>
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
export default AccountFeeModal
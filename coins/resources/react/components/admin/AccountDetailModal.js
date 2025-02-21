import React, { Component } from 'react'
import Accounts from '../../model/admin/Accounts';


import Input from '../input/Input';

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

class AccountDetailModal extends Component {

	constructor(props) {
		super(props);
		this.id = makeId();

		this.state = {
			account: {}
		}

		this.account_detail_struct = {};
		this.account_detail_struct[STRUCT_FILTERS] = {}
		this.account_detail_struct[STRUCT_COLUMNS] = {

			[POSITION_SYMBOL]: {
				[COL_NAME]: lang( [POSITION_SYMBOL]),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {  
					
					return <b>{data}</b>;
				},

			},

			[POSITION_UNREALIZED_PROFIT]: {
				[COL_NAME]: lang( [POSITION_UNREALIZED_PROFIT]),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign : 'center' },
				[COL_DECORATOR_IN]: (data) => {  
					
					return Number(data).toFixed(3);
				},

			},
			[POSITION_MARGIN]: {
				[COL_NAME]: lang( [POSITION_MARGIN]),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign : 'center' }
				

			},
			[POSITION_ISOLATED]: {
				[COL_NAME]: lang( [POSITION_ISOLATED]),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {  
					if(data) return 'Isolate';
					return 'Cross';
				},
				[COL_STYLE]: { textAlign : 'center' }

			},
			[POSITION_ENTRYPRICE]: {
				[COL_NAME]: lang( [POSITION_ENTRYPRICE]),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign : 'center' },
				[COL_DECORATOR_IN]: (data) => {  
					
					// var data = data.toFixed(3);
					return Number(data).toFixed(3);
				},

			},
			'Type': {
				[COL_NAME]: lang('Type'),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign : 'center' },
				[COL_DECORATOR_IN]: (colId, rowId, tbdata) => {
					var qty = tbdata[rowId][POSITION_POSITIONATM];
					if(qty > 0) return "LONG";
					return "SHORT";
				}

			},
			[POSITION_POSITIONATM]: {
				[COL_NAME]: lang( [POSITION_POSITIONATM]),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign : 'center' }

			},
			[POSITION_UPDATE_TIME]: {
				[COL_NAME]: lang( [POSITION_UPDATE_TIME]),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }

			}
		}
		this.account_detail_struct[STRUCT_FILTERS] = {

			[POSITION_SYMBOL]: {
				[FILTER_NAME]: lang(POSITION_SYMBOL),
				[FILTER_TYPE]: 'text',
			},
			[POSITION_UPDATE_TIME]: {
				[FILTER_NAME]: lang(POSITION_UPDATE_TIME),
				[FILTER_TYPE]: 'date',
				[FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },
			},
			[POSITION_ISOLATED]: {
				[FILTER_NAME]: lang(POSITION_ISOLATED),
				[FILTER_TYPE]: 'select',
				[FILTER_OPTION] : {
					'' : 'All', 
					[true] : 'Isolate',
					[false] : 'Cross'
				} 
			},


		}
	

		this.account_detail_struct[STRUCT_EDIT] = {


		}

		// this.account_detail_struct[STRUCT_ROWS] = {
		//     [ROW_FUNCS]: (rowData) => {
		//         return <div className='box_flex' style={{ justifyContent: 'center' }}>
		//             <FuncEditRow rowData={rowData} />
		//         </div>
		//     }
		// };
		this.account_detail_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: '1',
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

		this.accountModel = new Accounts();
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
		},() => this.loadOrigin())



	}




	async loadOrigin() {

		var positions = await this.accountModel.getPositions(this.state.account[ACCOUNT_ID]);
		if (!positions['result']) {
			error_handle(positions);
			return;
		}
		positions = positions['data']['positions'];
	

		 this.table.setOrigin(positions);


	}



	render() {


		return (
			<>
				<div className="modal fade" id={"bladeModal" + this.id}>
					<div className="modal-dialog modal-lg modal-dialog-centered" style={{ minWidth : '1200px'}}>
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



	async saveData() {
		var trades = this.state.traceList;

		for (let i in trades) {
			if (trades[i][TRADE_SYMBOL] != '')
				if (trades[i][TRADE_ID]) {

					var result = await this.traceModel.edit(
						{
							[TRADE_ACCOUNT]: this.state.account[ACCOUNT_ID],
							[TRADE_SYMBOL]: trades[i][TRADE_SYMBOL]
						},
						{
							[TRADE_SYMBOL]: trades[i][TRADE_SYMBOL],
							[TRADE_BUDGET]: trades[i][TRADE_BUDGET],
							[TRADE_ACTION_BUDGET]: trades[i][TRADE_ACTION_BUDGET],
							[TRADE_STRATEGY]: trades[i][TRADE_STRATEGY],
						}
					)

					if (!result['result']) {
						error_handle(result);
						return result;
					}

				} else {

					var result = await this.traceModel.add(
						{
							[TRADE_ACCOUNT]: this.state.account[ACCOUNT_ID],
							[TRADE_SYMBOL]: trades[i][TRADE_SYMBOL],
							[TRADE_BUDGET]: trades[i][TRADE_BUDGET],
							[TRADE_ACTION_BUDGET]: trades[i][TRADE_ACTION_BUDGET],
							[TRADE_STRATEGY]: trades[i][TRADE_STRATEGY],
						}
					)

					if (!result['result']) {
						error_handle(result);
						return result;
					}

				}
		}
		this.modal('hide');
		this.getTraceList();
		return { result: true };
	}

}
export default AccountDetailModal
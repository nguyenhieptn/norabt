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

import Account_summary from '../../model/admin/Account_summary'
import TradeList from '../../components/admin/TradeList'
import AccountDetailModal from '../../components/admin/AccountDetailModal'
import AccountFeeModal from '../../components/admin/AccountFeeModal'
import Actions from '../../model/admin/Actions'

class Account_summaryView extends Component {

	constructor(props) {
		super(props);

		this.account_summary_struct = {};
		this.account_summary_struct[STRUCT_FILTERS] = {}
		this.account_summary_struct[STRUCT_COLUMNS] = {

			index: {
				[COL_NAME]: <i className=" button fa fa-refresh" onClick={() => {
					var model = new Account_summary();
					model.calculate().then(res => {
						if (res['result']) {
							this.table.filter();
						} else {
							error_handle(res);
						}
					})
				}}></i>,
				[COL_STYLE]: { fontWeight: 'bold', textAlign: 'center' }
			},

			[AC_SUM_ACCOUNT]: {
				[COL_NAME]: lang(AC_SUM_ACCOUNT),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => {
					return <b style={{ cursor: 'pointer' }} onClick={() => {
						this.props.onClickAccount && this.props.onClickAccount(data);
					}}>{this.table.mapping[AC_SUM_ACCOUNT] && this.table.mapping[AC_SUM_ACCOUNT][data]}</b>
				}

			},
			[AC_SUM_BALLANCE]: {
				[COL_NAME]: 'Wallet Balance',
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var rowData = data[rowId];
					var data = rowData[colId];
					if (!data) return '';
					var style = { fontWeight: 'bold', textAlign: 'center' };


					return <div style={style}>{(data != null && data != "") ? formatNumber(Math.round(data * 100) / 100) + " USDT" : ""}</div>
				},
				[COL_SUM]: true,


			},
			[AC_SUM_USED]: {
				[COL_NAME]: lang(AC_SUM_USED),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var rowData = data[rowId];
					var data = rowData[colId];
					if (!data) return '';
					var style = { fontWeight: 'bold', textAlign: 'center' };


					return <div style={style}>{(data != null && data != "") ? formatNumber(Math.round(data * 100) / 100) + " USDT" : ""}</div>
				},
				[COL_SUM]: true,

			},
			[AC_SUM_FREE]: {
				[COL_NAME]: lang(AC_SUM_FREE),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var rowData = data[rowId];
					var data = rowData[colId];
					if (!data) return '';
					var style = { fontWeight: 'bold', textAlign: 'center' };
					return <div style={style}>{(data != null && data != "") ? formatNumber(Math.round(data * 100) / 100) + " USDT" : ""}</div>
				},
				[COL_SUM]: true,

			},

			[AC_SUM_INVESTING]: {
				[COL_NAME]: lang(AC_SUM_INVESTING),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var rowData = data[rowId];
					var data = rowData[colId];
					if (!data) return '';
					var style = { fontWeight: 'bold', textAlign: 'center' };

					return <div style={style}>{(data != null && data != "") ? formatNumber(Math.round(data * 100) / 100) + " USDT" : ""}</div>
				},
				[COL_SUM]: true,

			},

			'invest': {
				[COL_NAME]: lang('Invest'),
				[COL_SORT]: false,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var rowData = data[rowId];
					var data = rowData[AC_SUM_ACCOUNT];
					if (!data) return '';
					var invest = this.actionInvest[data];
					return <div style={{ fontWeight: 'bold', textAlign: 'center' }}>{formatNumber(Math.round(invest * 1000) / 1000)}</div>
				},
				[COL_SUM]: (data) => {
					if(!data) return
					 
					var result =0 ;
					Object.values(this.actionInvest).map(item => {
						result += item;
					});
					return formatNumber(result.toFixed(3))

				},

			},

			[AC_SUM_TRADING]: {
				[COL_NAME]: lang(AC_SUM_TRADING),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center', fontWeight: 'bold' },


			},

			[AC_SUM_UNREALIZED_PROFIT]: {
				[COL_NAME]: lang(AC_SUM_UNREALIZED_PROFIT),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var rowData = data[rowId];
					var data = rowData[colId];
					if (!data) return '';
					var style = { fontWeight: 'bold', textAlign: 'center' };
					if (data >= 0) style['color'] = 'limegreen';
					if (data < 0) style['color'] = 'red';

					return <div style={style}>{(data != null && data != "") ? formatNumber(Math.round(data * 100) / 100) + " USDT" : ""}</div>
				},
				[COL_SUM]: true,

			},

			[AC_SUM_TODAYPROFIT]: {
				[COL_NAME]: lang(AC_SUM_TODAYPROFIT),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var rowData = data[rowId];
					var data = rowData[colId];
					if (!data) return '';
					var style = { fontWeight: 'bold', textAlign: 'center' };
					if (data >= 0) style['color'] = 'limegreen';
					if (data < 0) style['color'] = 'red';

					return <div style={style}>{(data != null && data != "") ? formatNumber(Math.round(data * 100) / 100) + " USDT" : ""}</div>
				},
				[COL_SUM]: true,

			},

			[AC_SUM_MONTHPROFIT]: {
				[COL_NAME]: lang(AC_SUM_MONTHPROFIT),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var rowData = data[rowId];
					var data = rowData[colId];
					if (!data) return '';
					var style = { fontWeight: 'bold', textAlign: 'center' };
					if (data >= 0) style['color'] = 'limegreen';
					if (data < 0) style['color'] = 'red';

					return <div style={style}>{(data != null && data != "") ? formatNumber(Math.round(data * 100) / 100) + " USDT" : ""}</div>
				},
				[COL_SUM]: true,

			},
			[AC_SUM_TOTALPROFIT]: {
				[COL_NAME]: lang(AC_SUM_TOTALPROFIT),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var rowData = data[rowId];
					var data = rowData[colId];
					if (!data) return '';
					var style = { fontWeight: 'bold', textAlign: 'center' };
					if (data >= 0) style['color'] = 'limegreen';
					if (data < 0) style['color'] = 'red';

					return <div style={style}>{(data != null && data != "") ? formatNumber(Math.round(data * 100) / 100) + " USDT" : ""}</div>
				},
				[COL_SUM]: true,

			},
			[AC_SUM_FUNDING_FEE]: {
				[COL_NAME]: lang(AC_SUM_FUNDING_FEE),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center', fontWeight: 'bold' },
				[COL_DECORATOR_IN]: (data) => {
					return formatNumber(Math.round(data * 1000) / 1000);
				},

			},
			[AC_SUM_COMMISSION]: {
				[COL_NAME]: lang(AC_SUM_COMMISSION),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center', fontWeight: 'bold' },
				[COL_DECORATOR_IN]: (data) => {
					return formatNumber(Math.round(data * 1000) / 1000);
				},

			},
			[AC_SUM_REFERAL]: {
				[COL_NAME]: lang(AC_SUM_REFERAL),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center', fontWeight: 'bold' },
				[COL_DECORATOR_IN]: (data) => {
					if (!data) return
					return formatNumber(Math.round(data * 1000) / 1000);
				},

			},
			[AC_SUM_MAINT_MARGIN]: {
				[COL_NAME]: lang(AC_SUM_MAINT_MARGIN),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center', fontWeight: 'bold' },
				[COL_DECORATOR_IN]: (data) => {
					return formatNumber(Math.round(data * 1000) / 1000);
				},
				[COL_SUM]: true,

			},
			[AC_SUM_INITIAL_MARGIN]: {
				[COL_NAME]: lang(AC_SUM_INITIAL_MARGIN),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center', fontWeight: 'bold' },
				[COL_DECORATOR_IN]: (data) => {
					return formatNumber(Math.round(data * 1000) / 1000);
				},
				[COL_SUM]: true,

			},
			[AC_SUM_MARGIN_BALANCE]: {
				[COL_NAME]: lang(AC_SUM_MARGIN_BALANCE),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center', fontWeight: 'bold' },
				[COL_DECORATOR_IN]: (data) => {
					return formatNumber(Math.round(data * 1000) / 1000);
				},
				[COL_SUM]: true,

			},
			[AC_SUM_MARGIN_RATIO]: {
				[COL_NAME]: lang(AC_SUM_MARGIN_RATIO),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center', fontWeight: 'bold' },
				[COL_SUM]: true,

			},
			[AC_SUM_AVAILABLE]: {
				[COL_NAME]: lang(AC_SUM_AVAILABLE),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center', fontWeight: 'bold' },
				[COL_DECORATOR_IN]: (data) => {
					return formatNumber(Math.round(data * 1000) / 1000);
				},

			},



			action: {
				[COL_NAME]: lang('Action'),
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var rowData = data[rowId];
					return <div className='box_flex' style={{ justifyContent: 'center' }}>
						<div className='button btn btn-warning btn-sm' style={{ fontSize: 10 }} onClick={() => {
							this.tradelist.setAccount(rowData[AC_SUM_ACCOUNT], this.table.mapping[AC_SUM_ACCOUNT][rowData[AC_SUM_ACCOUNT]]);
							this.tradelist.modal();
						}}>Trades</div>
						<div className='button btn btn-info btn-sm' style={{ fontSize: 10 }} onClick={() => {
							this.AccountDetailModal.setAccount(rowData[AC_SUM_ACCOUNT], this.table.mapping[AC_SUM_ACCOUNT][rowData[AC_SUM_ACCOUNT]]);
							this.AccountDetailModal.modal();
							// window.open(App.link('/admin/dashboard/view?account=' + rowData[AC_SUM_ACCOUNT]), '_blank');
						}}>Detail</div>
						{/* <div className='button btn btn-info btn-sm' style={{ fontSize: 10 }} onClick={() => {
							 	this.AccountFeeModal.setAccount(rowData[AC_SUM_ACCOUNT], this.table.mapping[AC_SUM_ACCOUNT][rowData[AC_SUM_ACCOUNT]]);
								this.AccountFeeModal.modal();
						}}>Funding Fee</div> */}
					</div>
				},
				[COL_STYLE]: { textAlign: 'center', display: (this.props.isDashboard ? 'none' : '') }

			}




		}
		this.account_summary_struct[STRUCT_FILTERS] = {

			[AC_SUM_ACCOUNT]: {
				[FILTER_NAME]: lang(AC_SUM_ACCOUNT),
				[FILTER_TYPE]: 'select',
			}
		}

		this.account_summary_struct[STRUCT_EDIT] = {

			[AC_SUM_ACCOUNT]: {
				[EDIT_NAME]: lang(AC_SUM_ACCOUNT),
				[EDIT_TYPE]: 'Number',

			},
			[AC_SUM_BALLANCE]: {
				[EDIT_NAME]: lang(AC_SUM_BALLANCE),
				[EDIT_TYPE]: 'text',

			},
			[AC_SUM_USED]: {
				[EDIT_NAME]: lang(AC_SUM_USED),
				[EDIT_TYPE]: 'text',

			},
			[AC_SUM_FREE]: {
				[EDIT_NAME]: lang(AC_SUM_FREE),
				[EDIT_TYPE]: 'text',

			},
			[AC_SUM_INVESTING]: {
				[EDIT_NAME]: lang(AC_SUM_INVESTING),
				[EDIT_TYPE]: 'text',

			},
			[AC_SUM_TOTALPROFIT]: {
				[EDIT_NAME]: lang(AC_SUM_TOTALPROFIT),
				[EDIT_TYPE]: 'text',

			},
			[AC_SUM_TODAYPROFIT]: {
				[EDIT_NAME]: lang(AC_SUM_TODAYPROFIT),
				[EDIT_TYPE]: 'text',

			},
			[AC_SUM_MONTHPROFIT]: {
				[EDIT_NAME]: lang(AC_SUM_MONTHPROFIT),
				[EDIT_TYPE]: 'text',

			},
			[AC_SUM_TRADING]: {
				[EDIT_NAME]: lang(AC_SUM_TRADING),
				[EDIT_TYPE]: 'Number',

			},


		}

		this.account_summary_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData} />
				</div>
			}
		};
		this.account_summary_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: ACCOUNT_SUMMARY_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {
				[AC_SUM_BALLANCE]: true,
				[AC_SUM_USED]: true,
				[AC_SUM_FREE]: true,
				[AC_SUM_INVESTING]: true,
				[AC_SUM_TRADING]: true,
				[AC_SUM_MONTHPROFIT]: true,
				action: true
			},
			[DATA_PERMIT_COL]: this.permissionAccount_summaryView(),
			[DATA_KEY]: [AC_SUM_ID],
			[DATA_SORT]: { [AC_SUM_ID]: 'desc' },
			[FLAG_FILTER]: false,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: false,
			[FLAG_SETTING_ROWS]: false,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,
			[PAGE_QUANTITY]: 1000,

			model: new Account_summary()


		};

		this.actionInvest = {};


	}

	permissionAccount_summaryView() {
		return Object.assign(
			...Object.keys(this.account_summary_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.account_summary_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	render() {
		return (
			<div className=''>
				<Table ref={c => this.table = c} table={this.account_summary_struct} autoload={true} >
					<FuncBar
						left={<>
							<div className='box_flex'>
								<FuncHideCol />


							</div>
						</>}
						name={'Account tracking'}
						right={<></>}></FuncBar>
					<MainTable className='table table-bordered table-resizable' minHeight={0}></MainTable>
				</Table>

				<style>{`
					#account_summary{
						margin-bottom: 0px
					}
				`}</style>
				<AccountDetailModal ref={c => this.AccountDetailModal = c}></AccountDetailModal>
				<TradeList ref={c => this.tradelist = c}></TradeList>
				<AccountFeeModal ref={c => this.AccountFeeModal = c}></AccountFeeModal>
			</div>
		);
	}

	componentDidMount() {
		var actionModel = new Actions();
		actionModel.read({ action_pending: 1 }).then(res => {
			if (res['result']) {
				res = res['data'];
				res.map(item => {
					var matched = Number(item[ACTION_MATCHED_PRICE]);
					var quantity = Number(item[ACTION_MATCHED_QTY]);
					var invest = matched * quantity;

					if (isset(this.actionInvest[item[ACTION_ACCOUNT]])) {
						this.actionInvest[item[ACTION_ACCOUNT]] += invest
					} else {
						this.actionInvest[item[ACTION_ACCOUNT]] = invest
					}
				})

				this.table.filter()

				
			} else {
				error_handle(res)
			}
		})
		this.intervalUpdate = setInterval(() => {
			this.table.filter(false);
		}, 600000);
	}

	componentWillUnmount() {
		if (this.intervalUpdate) {
			clearInterval(this.intervalUpdate);
		}
	}
}

export default Account_summaryView
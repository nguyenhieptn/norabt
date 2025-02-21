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

import Actions from '../../model/admin/Actions'
import OrderModal from '../../components/admin/OrderModal'
import OrderBinanceModal from '../../components/admin/OrderBinanceModal'
import Watchlist from '../../model/admin/Watchlist'
class ActionsView extends Component {

	constructor(props) {
		super(props);

		this.actions_struct = {};
		this.actions_struct[STRUCT_FILTERS] = {}
		this.actions_struct[STRUCT_COLUMNS] = {

			[ACTION_BINANCE]: {
				[COL_NAME]: lang(ACTION_BINANCE),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var rowData = data[rowId];
					return <div className='box_flex'>
						<div className='button btn btn-info btn-sm' style={{ fontSize: 10 }} onClick={() => {
							this.orderModal.loadData(rowData);
							this.orderModal.modal();
						}}>Orders</div>
						<div className='button btn btn-primary btn-sm' style={{ fontSize: 10 }} onClick={() => {
							this.gotoNextPhase(rowData[ACTION_ID], rowData[ACTION_SYMBOL])
						}}>Next Phase</div>
						<div className='button btn btn-danger btn-sm' style={{ fontSize: 10 }} onClick={() => {
							this.closeAction(rowData[ACTION_ID], rowData[ACTION_SYMBOL])
						}}>Close</div>

					</div>
				},
				[COL_STYLE]: { textAlign: 'center' }


			},

			binace_order: {
				[COL_NAME]: 'Binance Order',
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var rowData = data[rowId];
					return 	<div className='box_flex'>
						<div className='button btn btn-info btn-sm' style={{ fontSize: 10, }} 
						onClick={() => {
							this.getBinanceAllOrder(rowData);
						}}
						>Orders</div>

						<div className='button btn btn-sm btn-danger' style={{ fontSize: 10, }} 
						onClick={() => {
							this.syncPostion(rowData[ACTION_ID], rowData[ACTION_SYMBOL]);
						}}
						>Synchronize</div>
						</div>
				}
			},

			[ACTION_SYMBOL]: {
				[COL_NAME]: lang(ACTION_SYMBOL),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var rowData = data[rowId];
					var data = rowData[colId];
					return <div style={{ cursor: 'pointer' }} onClick={() => {
						window.open(App.link('/admin/tradechart/single?symbol=' + rowData[ACTION_SYMBOL]), '_blank');
					}}><b>
						<img style={{ width: '20px', height: '20px', marginRight: '10px' }} src={this.watchlistIcon[data]}></img>
						{rowData[ACTION_SYMBOL]}
					</b></div>
				}


			},

			[ACTION_ACCOUNT]: {
				[COL_NAME]: lang(ACTION_ACCOUNT),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => {
					return <b >{this.table.mapping[ACTION_ACCOUNT] && this.table.mapping[ACTION_ACCOUNT][data]}</b>
				}

			},
		
			[ACTION_CONTAINER]: {
				[COL_NAME]: lang(ACTION_CONTAINER),
				[COL_SORT]: true,
			},

			[ACTION_STRATEGY]: {
				[COL_NAME]: lang(ACTION_STRATEGY),
				[COL_SORT]: true,
			},

			[ACTION_FLOW]: {
				[COL_NAME]: lang(ACTION_FLOW),
				[COL_SORT]: true,
			},

			'inveted': {
				[COL_NAME]: lang('Invest'),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: (colId, rowId, data) => {

					var rowData = data[rowId];
					var matched = Number(rowData[ACTION_MATCHED_PRICE]);
					var quantity = Number(rowData[ACTION_MATCHED_QTY]);
					var margin = Number(rowData[ACTION_MARGIN]);
					if(margin <= 0) margin = 1;
					return (matched * quantity/margin).toFixed(3) + "";

				}
			},

			[ACTION_BUDGET]: {
				[COL_NAME]: lang(ACTION_BUDGET),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: (data) => (data != null && data != "") ? data.toFixed(3) + "" : ""
			},
			[ACTION_BUDGET_ACTIVE]: {
				[COL_NAME]: lang(ACTION_BUDGET_ACTIVE),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: (data) => (data != null && data != "") ? data.toFixed(3) + "" : ""
			},
			[ACTION_BUDGET_USED]: {
				[COL_NAME]: lang(ACTION_BUDGET_USED),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: (data) => (data != null && data != "") ? data.toFixed(3) + "" : ""
			},

			base_profit_margin: {
				[COL_NAME]: lang('Target Profit'),
				[COL_SORT]: false,
				[COL_STYLE]: { textAlign: 'center', fontWeight: 'bold' },
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var rowData = data[rowId];
					var baseProfit = Number(rowData[ACTION_BASEPROFIT]);
					var margin = Number(rowData[ACTION_MARGIN]);
					var matchedPrice = Number(rowData[ACTION_MATCHED_PRICE]);
					var matchedQty = Number(rowData[ACTION_MATCHED_QTY]);
					var targetProfit = baseProfit * margin;
					return (matchedQty * baseProfit * matchedPrice / 100).toFixed(3) + " (" + (targetProfit).toFixed(3) + "%)";
				}
			},

			target_price: {
				[COL_NAME]: lang('Target Price'),
				[COL_SORT]: false,
				[COL_STYLE]: { textAlign: 'center', fontWeight: 'bold' },
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var rowData = data[rowId];
					var baseProfit = Number(rowData[ACTION_BASEPROFIT]);
					var margin = Number(rowData[ACTION_MARGIN]);
					var matchedPrice = Number(rowData[ACTION_MATCHED_PRICE]);
					var matchedQty = Number(rowData[ACTION_MATCHED_QTY]);
					var targetProfit = baseProfit * margin;
					return (matchedPrice + baseProfit * matchedPrice / 100).toFixed(3);
				}
			},

			[ACTION_MARGIN]: {
				[COL_NAME]: lang(ACTION_MARGIN),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' }
			},

			[ACTION_CHART]: {
				[COL_NAME]: lang(ACTION_CHART),
				[COL_SORT]: true,
				// [COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' },
				[COL_DECORATOR_IN]: (colId, rowId, data) => {

					var rowData = data[rowId];
					var data = rowData[colId];
					if (!data) return '';
					return <div style={{ cursor: 'pointer' }} onClick={() => {
						// window.open(App.link('/admin/dashboard/view?symbol=' + rowData[ACTION_SYMBOL]) + "&start=" + (Math.floor(rowData[ACTION_CHART] / 1000) - 300) * 1000 + "&stop=" + (Math.floor(rowData[ACTION_CHART] / 1000) + 3000) * 1000, '_blank');
						this.props.onSelectTime && this.props.onSelectTime(rowData[ACTION_SYMBOL], (Math.floor(rowData[ACTION_CHART] / 1000) - 300) * 1000, (Math.floor(rowData[ACTION_CHART] / 1000) + 3000) * 1000);
					}}><b>{moment(data, 'x').format(DATE_FORMAT)}</b></div>
				}
			},

			[ACTION_REALPROFIT]: {
				[COL_NAME]: lang(ACTION_REALPROFIT) + '(%)',
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var rowData = data[rowId];
					var data = rowData[colId];
					if (!data) return '';
					var style = { fontWeight: 'bold' };
					if (data >= 0) style['color'] = 'limegreen';
					if (data < 0) style['color'] = 'red';
					if (rowData[ACTION_PENDING] == 0) style['color'] = 'black';

					return <div style={style}>{(data != null && data != "") ? data.toFixed(3) + "%" : ""}</div>
				}

			},

			[ACTION_PROFIT]: {
				[COL_NAME]: lang(ACTION_PROFIT) + '(%)',
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var rowData = data[rowId];
					var data = rowData[colId];
					if (!data) return '';
					var style = { fontWeight: 'bold' };
					if (data >= 0) style['color'] = 'limegreen';
					if (data < 0) style['color'] = 'red';
					if (rowData[ACTION_PENDING] == 0) style['color'] = 'black';

					return <div style={style}>{(data != null && data != "") ? data.toFixed(3) + "%" : ""}</div>
				}

			},

			[ACTION_EVENTPROFIT]: {
				[COL_NAME]: lang(ACTION_EVENTPROFIT),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var rowData = data[rowId];
					var data = rowData[colId];
					if (!data) return '';
					var style = { fontWeight: 'bold' };
					if (data >= 0) style['color'] = 'limegreen';
					if (data < 0) style['color'] = 'red';
					if (rowData[ACTION_PENDING] == 0) style['color'] = 'black';
					var matched = Number(rowData[ACTION_MATCHED_PRICE]);
					var quantity = Number(rowData[ACTION_MATCHED_QTY]);
					var money = matched * quantity * data / 100;
					if (data == null || data == "") return '';

					return <div style={style}>{`${money.toFixed(3)} (${data.toFixed(3)}%)`}</div>
				}

			},

			'event_current_profit': {
				[COL_NAME]: lang('Current Profit'),
				[COL_SORT]: false,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var rowData = data[rowId];
					var eventProfit = Number(rowData[ACTION_EVENTPROFIT]);
					var profit = Number(rowData[ACTION_PROFIT]);
					if (rowData[ACTION_PENDING] == 1) {
						var data = profit + eventProfit;
					} else {
						var data = eventProfit;
					}
					if (!data) return '';
					var style = { fontWeight: 'bold' };
					if (data >= 0) style['color'] = 'limegreen';
					if (data < 0) style['color'] = 'red';
					if (rowData[ACTION_PENDING] == 0) style['color'] = 'black';

					var matched = Number(rowData[ACTION_MATCHED_PRICE]);
					var quantity = Number(rowData[ACTION_MATCHED_QTY]);
					var money = matched * quantity * data / 100;
					if (data == null || data == "") return '';

					return <div style={style}>{`${money.toFixed(3)} (${data.toFixed(3)}%)`}</div>
				}
			},

			[ACTION_LAST_PRICE]: {
				[COL_NAME]: lang(ACTION_LAST_PRICE),
				[COL_SORT]: true,

			},

			pricechange: {
				[COL_NAME]: lang('Price Change'),
				[COL_SORT]: false,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var rowData = data[rowId];
					var lastPrice = Number(rowData[ACTION_LAST_PRICE]);
					if (lastPrice <= 0) return '';
					var profit = Number(rowData[ACTION_PROFIT]);
					var matchedPrice = Number(rowData[ACTION_MATCHED_PRICE]);
					var type = Number(rowData[ACTION_TYPE]);
					if (type == ACTION_TYPE_LONG) {
						var price = matchedPrice + profit * matchedPrice / 100;
					} else {
						var price = matchedPrice - profit * matchedPrice / 100;
					}

					var change = (price - lastPrice) * 100 / lastPrice;

					var style = { fontWeight: 'bold' };
					return <div style={style}>{(change).toFixed(3)}%</div>;
				}
			},

			profit_margin: {
				[COL_NAME]: lang('Margin Profit'),
				[COL_SORT]: false,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var rowData = data[rowId];
					var profit = Number(rowData[ACTION_PROFIT]);
					var margin = Number(rowData[ACTION_MARGIN]);
					var matchedQty = Number(rowData[ACTION_MATCHED_QTY]);
					var matchedPrice = Number(rowData[ACTION_MATCHED_PRICE]);
					var marginProfit = profit * margin;

					var style = { fontWeight: 'bold' };
					if (marginProfit >= 0) style['color'] = 'limegreen';
					if (marginProfit < 0) style['color'] = 'red';
					if (rowData[ACTION_PENDING] == 0) style['color'] = 'black';

					return <div style={style}>{(profit * matchedPrice * matchedQty / 100).toFixed(3) + " (" + (marginProfit).toFixed(3) + "%)"}</div>;
				}
			},

			[ACTION_PHASE]: {
				[COL_NAME]: lang(ACTION_PHASE),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' }
			},

			[ACTION_PHASE_NOTE]: {
				[COL_NAME]: lang(ACTION_PHASE_NOTE),
				[COL_SORT]: false,
				[COL_DECORATOR_IN]: data => {
					var style = { textAlign: 'center', color: 'red', fontWeight: 'bold' };
					return <div style={style}>{data}</div>
				}
			},
			[ACTION_NEXTPHASE_NOTE]: {
				[COL_NAME]: lang(ACTION_NEXTPHASE_NOTE),
				[COL_SORT]: false,
				[COL_DECORATOR_IN]: data => {
					var style = { textAlign: 'center', color: 'red', fontWeight: 'bold' };
					return <div style={style}>{data}</div>
				}
			},

			[ACTION_LIQUIDATION]: {
				[COL_NAME]: lang(ACTION_LIQUIDATION),
				[COL_SORT]: true,
			},

			[ACTION_BASEPROFIT]: {
				[COL_NAME]: lang(ACTION_BASEPROFIT) + '(%)',
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: (data) => (data != null && data != "") ? data.toFixed(3) + "%" : ""

			},



			[ACTION_TOTALPROFIT]: {
				[COL_NAME]: lang(ACTION_TOTALPROFIT) + '(%)',
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: (data) => (data != null && data != "") ? data.toFixed(3) + "%" : ""

			},



			[ACTION_TYPE]: {
				[COL_NAME]: lang(ACTION_TYPE),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' }

			},
			[ACTION_STATUS]: {
				[COL_NAME]: lang(ACTION_STATUS),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' }

			},



			[ACTION_PENDING]: {
				[COL_NAME]: lang(ACTION_PENDING),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' }

			},

			[ACTION_START_REASON]: {
				[COL_NAME]: lang(ACTION_START_REASON),
				[COL_SORT]: false,

			},
			[ACTION_STOP_REASON]: {
				[COL_NAME]: lang(ACTION_STOP_REASON),
				[COL_SORT]: false,

			},

			[ACTION_LOG]: {
				[COL_NAME]: lang(ACTION_LOG),
				[COL_SORT]: false,

			},




			'USDT Profit': {
				[COL_NAME]: lang('Real Profit (USDT)'),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var rowData = data[rowId];

					var pnl = Number(rowData[ACTION_PNL]);
					if (pnl == 0) return;
					var commit = rowData[ACTION_COMMIT];
					return (pnl - commit).toFixed(3) + "";
				}

			},

			[ACTION_PNL]: {
				[COL_NAME]: lang(ACTION_PNL),
				[COL_SORT]: true,
				[COL_SUM]: true,
				[COL_DECORATOR_IN]: (data) => (data != null && data != "") ? data.toFixed(3) + "" : ""

			},

			[ACTION_COMMIT]: {
				[COL_NAME]: lang(ACTION_COMMIT),
				[COL_SORT]: true,
				[COL_SUM]: true,
				[COL_DECORATOR_IN]: (data) => (data != null && data != "") ? data.toFixed(3) + "" : ""

			},

			[ACTION_EVENT_DATA]: {
				[COL_NAME]: lang(ACTION_EVENT_DATA),
				[COL_SORT]: false,

			},

			[ACTION_ENTER_TIME]: {
				[COL_NAME]: lang(ACTION_ENTER_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},

			[ACTION_ENTER_PRICE]: {
				[COL_NAME]: lang(ACTION_ENTER_PRICE),
				[COL_SORT]: true,

			},

			[ACTION_ENTER_QTY]: {
				[COL_NAME]: lang(ACTION_ENTER_QTY),
				[COL_SORT]: true,

			},

			[ACTION_MATCHED_PRICE]: {
				[COL_NAME]: lang(ACTION_MATCHED_PRICE),
				[COL_SORT]: true,

			},

			[ACTION_MATCHED_QTY]: {
				[COL_NAME]: lang(ACTION_MATCHED_QTY),
				[COL_SORT]: true,

			},
			[ACTION_MATCHED_TIME]: {
				[COL_NAME]: lang(ACTION_MATCHED_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },

			},

			[ACTION_FIRST_PRICE]: {
				[COL_NAME]: lang(ACTION_FIRST_PRICE),
				[COL_SORT]: true,
			},

			[ACTION_MATCHED_EMA5]: {
				[COL_NAME]: lang(ACTION_MATCHED_EMA5),
				[COL_SORT]: true,

			},
			[ACTION_SELL_PRICE]: {
				[COL_NAME]: lang(ACTION_SELL_PRICE),
				[COL_SORT]: true,

			},
			[ACTION_SELL_TIME]: {
				[COL_NAME]: lang(ACTION_SELL_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {

					var rowData = data[rowId];
					var data = rowData[colId];
					if (!data) return '';
					return <div style={{ cursor: 'pointer' }} onClick={() => {
						this.props.onSelectTime && this.props.onSelectTime(rowData[ACTION_SYMBOL], (Math.floor(rowData[ACTION_CHART] / 1000) - 300) * 1000, (Math.floor(rowData[ACTION_CHART] / 1000) + 3000) * 1000);
					}}><b>{moment(data, 'x').format(DATE_FORMAT)}</b></div>
				}

			},




		}
		this.actions_struct[STRUCT_FILTERS] = {


			[ACTION_SYMBOL]: {
				[FILTER_NAME]: lang(ACTION_SYMBOL),
				[FILTER_TYPE]: 'select',
			},
			[ACTION_ACCOUNT]: {
				[FILTER_NAME]: lang(ACTION_ACCOUNT),
				[FILTER_TYPE]: 'check',
				[FILTER_OPERATION]: 'or',
			},
			[ACTION_CONTAINER]: {
				[FILTER_NAME]: lang(ACTION_CONTAINER),
				[FILTER_TYPE]: 'select',
			},
			[ACTION_STRATEGY]: {
				[FILTER_NAME]: lang(ACTION_STRATEGY),
				[FILTER_TYPE]: 'select',
			},
			[ACTION_FLOW]: {
				[FILTER_NAME]: lang(ACTION_FLOW),
				[FILTER_TYPE]: 'select',
			},
			[ACTION_CHART]: {
				[FILTER_NAME]: lang(ACTION_CHART),
				[FILTER_TYPE]: 'date',
				[FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },
			},
			[ACTION_ENTER_TIME]: {
				[FILTER_NAME]: lang(ACTION_ENTER_TIME),
				[FILTER_TYPE]: 'date',
				[FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },
			},
			[ACTION_ENTER_PRICE]: {
				[FILTER_NAME]: lang(ACTION_ENTER_PRICE),
				[FILTER_TYPE]: 'text',
			},
			[ACTION_ENTER_QTY]: {
				[FILTER_NAME]: lang(ACTION_ENTER_QTY),
				[FILTER_TYPE]: 'text',
			},
			[ACTION_TYPE]: {
				[FILTER_NAME]: lang(ACTION_TYPE),
				[FILTER_TYPE]: 'select',
			},
			[ACTION_STATUS]: {
				[FILTER_NAME]: lang(ACTION_STATUS),
				[FILTER_TYPE]: 'select',
			},

			[ACTION_PHASE]: {
				[FILTER_NAME]: lang(ACTION_PHASE),
				[FILTER_TYPE]: 'select',
			},

			[ACTION_PHASE_NOTE]: {
				[FILTER_NAME]: lang(ACTION_PHASE_NOTE),
				[FILTER_TYPE]: 'text',

			},
			[ACTION_NEXTPHASE_NOTE]: {
				[FILTER_NAME]: lang(ACTION_NEXTPHASE_NOTE),
				[FILTER_TYPE]: 'text',

			},

			[ACTION_MATCHED_TIME]: {
				[FILTER_NAME]: lang(ACTION_MATCHED_TIME),
				[FILTER_TYPE]: 'date',
				[FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },
			},
			[ACTION_SELL_PRICE]: {
				[FILTER_NAME]: lang(ACTION_SELL_PRICE),
				[FILTER_TYPE]: 'text',
			},
			[ACTION_SELL_TIME]: {
				[FILTER_NAME]: lang(ACTION_SELL_TIME),
				[FILTER_TYPE]: 'date',
				[FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },
			},


			[ACTION_PENDING]: {
				[FILTER_NAME]: lang(ACTION_PENDING),
				[FILTER_TYPE]: 'select',
			},



		}

		this.actions_struct[STRUCT_EDIT] = {

			[ACTION_BINANCE]: {
				[EDIT_NAME]: lang(ACTION_BINANCE),
				[EDIT_TYPE]: 'text',

			},
			[ACTION_SYMBOL]: {
				[EDIT_NAME]: lang(ACTION_SYMBOL),
				[EDIT_TYPE]: 'select',

			},
			[ACTION_ACCOUNT]: {
				[EDIT_NAME]: lang(ACTION_ACCOUNT),
				[EDIT_TYPE]: 'select',

			},

			[ACTION_CONTAINER]: {
				[EDIT_NAME]: lang(ACTION_CONTAINER),
				[EDIT_TYPE]: 'select',
			},
			[ACTION_STRATEGY]: {
				[EDIT_NAME]: lang(ACTION_STRATEGY),
				[EDIT_TYPE]: 'select',
			},
			[ACTION_FLOW]: {
				[EDIT_NAME]: lang(ACTION_FLOW),
				[EDIT_TYPE]: 'text',
			},

			[ACTION_CHART]: {
				[EDIT_NAME]: lang(ACTION_CHART),
				[EDIT_TYPE]: 'date',
				[EDIT_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[EDIT_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },

			},
			[ACTION_ENTER_PRICE]: {
				[EDIT_NAME]: lang(ACTION_ENTER_PRICE),
				[EDIT_TYPE]: 'text',

			},
			[ACTION_TYPE]: {
				[EDIT_NAME]: lang(ACTION_TYPE),
				[EDIT_TYPE]: 'select',

			},

			[ACTION_MARGIN]: {
				[EDIT_NAME]: lang(ACTION_MARGIN),
				[EDIT_TYPE]: 'number',

			},

			[ACTION_BUDGET]: {
				[EDIT_NAME]: lang(ACTION_BUDGET),
				[EDIT_TYPE]: 'number',

			},

			[ACTION_BUDGET_ACTIVE]: {
				[EDIT_NAME]: lang(ACTION_BUDGET_ACTIVE),
				[EDIT_TYPE]: 'number',

			},

			[ACTION_BUDGET_USED]: {
				[EDIT_NAME]: lang(ACTION_BUDGET_USED),
				[EDIT_TYPE]: 'number',

			},
			[ACTION_PHASE]: {
				[EDIT_NAME]: lang(ACTION_PHASE),
				[EDIT_TYPE]: 'select',

			},

			[ACTION_PHASE_NOTE]: {
				[EDIT_NAME]: lang(ACTION_PHASE_NOTE),
				[EDIT_TYPE]: 'textarea',

			},

			[ACTION_NEXTPHASE_NOTE]: {
				[EDIT_NAME]: lang(ACTION_NEXTPHASE_NOTE),
				[EDIT_TYPE]: 'textarea',

			},

			[ACTION_EVENT_DATA]: {
				[EDIT_NAME]: lang(ACTION_EVENT_DATA),
				[EDIT_TYPE]: 'textarea',

			},
			[ACTION_STOP_REASON]: {
				[EDIT_NAME]: lang(ACTION_STOP_REASON),
				[EDIT_TYPE]: 'textarea',

			},
			[ACTION_MATCHED_PRICE]: {
				[EDIT_NAME]: lang(ACTION_MATCHED_PRICE),
				[EDIT_TYPE]: 'number',

			},
			[ACTION_MATCHED_QTY]: {
				[EDIT_NAME]: lang(ACTION_MATCHED_QTY),
				[EDIT_TYPE]: 'number',

			},
			[ACTION_MATCHED_TIME]: {
				[EDIT_NAME]: lang(ACTION_MATCHED_TIME),
				[EDIT_TYPE]: 'date',
				[EDIT_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[EDIT_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },

			},

			[ACTION_FIRST_PRICE]: {
				[EDIT_NAME]: lang(ACTION_FIRST_PRICE),
				[EDIT_TYPE]: 'number',

			},

			[ACTION_LAST_PRICE]: {
				[EDIT_NAME]: lang(ACTION_LAST_PRICE),
				[EDIT_TYPE]: 'number',

			},

			[ACTION_SELL_PRICE]: {
				[EDIT_NAME]: lang(ACTION_SELL_PRICE),
				[EDIT_TYPE]: 'number',

			},

			[ACTION_SELL_TIME]: {
				[EDIT_NAME]: lang(ACTION_SELL_TIME),
				[EDIT_TYPE]: 'date',
				[EDIT_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[EDIT_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },

			},
			[ACTION_PROFIT]: {
				[EDIT_NAME]: lang(ACTION_PROFIT),
				[EDIT_TYPE]: 'number',

			},
			[ACTION_EVENTPROFIT]: {
				[EDIT_NAME]: lang(ACTION_EVENTPROFIT),
				[EDIT_TYPE]: 'number',

			},
			[ACTION_TOTALPROFIT]: {
				[EDIT_NAME]: lang(ACTION_TOTALPROFIT),
				[EDIT_TYPE]: 'number',

			},
			[ACTION_BASEPROFIT]: {
				[EDIT_NAME]: lang(ACTION_BASEPROFIT),
				[EDIT_TYPE]: 'number',

			},
			[ACTION_REALPROFIT]: {
				[EDIT_NAME]: lang(ACTION_REALPROFIT),
				[EDIT_TYPE]: 'number',

			},
			[ACTION_STATUS]: {
				[EDIT_NAME]: lang(ACTION_STATUS),
				[EDIT_TYPE]: 'select',

			},
			[ACTION_PENDING]: {
				[EDIT_NAME]: lang(ACTION_PENDING),
				[EDIT_TYPE]: 'select',

			},

			[ACTION_LIQUIDATION]: {
				[EDIT_NAME]: lang(ACTION_LIQUIDATION),
				[EDIT_TYPE]: 'number',
			},

			[ACTION_LOG]: {
				[EDIT_NAME]: lang(ACTION_LOG),
				[EDIT_TYPE]: 'textarea',

			},



		}


		this.actions_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData} />
				</div>
			},

			// [ROW_FOOTER]: (datas, visibleColumns) => {

			// 	var totalRealProfit = 0;
			// 	var totalProfit = 0;
			// 	var totalPNL = 0;
			// 	var totalCommit = 0;
			// 	for (let i in datas) {
			// 		var data = datas[i];
			// 		if (data[ACTION_PENDING] == 0) {
			// 			totalProfit += Number(data[ACTION_PROFIT]);
			// 			totalRealProfit += Number(data[ACTION_REALPROFIT]);
			// 			totalPNL += Number(data[ACTION_PNL]);
			// 			totalCommit += Number(data[ACTION_COMMIT]);

			// 		}
			// 	}

			// 	return <tr>
			// 		{/* <td colSpan={4}></td> */}

			// 		<td colSpan={4} style={{ fontWeight: 'bold', color: (totalRealProfit > 0 ? "green" : "red"), textAlign: 'right' }}>Real Profit: {Math.round(totalRealProfit * 1000) / 1000}%</td>
			// 		<td colSpan={1} style={{ fontWeight: 'bold', color: (totalRealProfit > 0 ? "green" : "red"), textAlign: 'right' }}>Total Profit: {Math.round(totalProfit * 1000) / 1000}%</td>

			// 		<td colSpan={1} style={{ fontWeight: 'bold', color: (totalRealProfit > 0 ? "green" : "red"), textAlign: 'right' }}>Money: {Math.round((totalPNL - totalCommit) * 100) / 100} USDT</td>
			// 		<td colSpan={1} style={{ fontWeight: 'bold', color: (totalRealProfit > 0 ? "green" : "red"), textAlign: 'right' }}>Total PNL: {Math.round(totalPNL * 100) / 100} USDT</td>
			// 		<td colSpan={1}></td>
			// 		<td colSpan={1} style={{ fontWeight: 'bold', color: (totalRealProfit > 0 ? "green" : "red"), textAlign: 'right' }}>Commit: {Math.round(totalCommit * 100) / 100} USDT</td>



			// 		<td colSpan={visibleColumns.length - 9}></td>
			// 	</tr>

			// },

			[ROW_STYLE]: (rowID, tableData) => {
				var rowData = tableData[rowID];
				var profit = rowData[ACTION_PROFIT];
				var style = {};
				if (profit <= 0) style['color'] = 'red'
				if (profit > 0) style['color'] = 'limegreen'
				if (rowData[ACTION_PENDING] == 0) style['color'] = 'black';
				return style;
			}
		};
		this.actions_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: ACTIONS_TABLE,
			[DATA_FILTERS]: {
				"action_account": {
					"logic": "and",
					"data": {
						"=": "2"
					}
				}
			},
			[DATA_HIDDEN_COL]: {

				'inveted': true,
				[ACTION_BUDGET]: true,
				[ACTION_BUDGET_ACTIVE]: true,
				[ACTION_BUDGET_USED]: true,
				[ACTION_CHART]: true,
				[ACTION_REALPROFIT]: true,

				[ACTION_EVENTPROFIT]: true,
				'event_current_profit': true,
				[ACTION_LAST_PRICE]: true,

				[ACTION_PHASE_NOTE]: true,
				[ACTION_TOTALPROFIT]: true,

				[ACTION_START_REASON]: true,
				[ACTION_STOP_REASON]: true,
				[ACTION_LOG]: true,
				[ACTION_REALPROFIT]: true,
				[ACTION_PNL]: true,
				[ACTION_COMMIT]: true,
				[ACTION_EVENT_DATA]: true,
				[ACTION_ENTER_TIME]: true,
				[ACTION_ENTER_QTY]: true,
				[ACTION_ENTER_PRICE]: true,
				[ACTION_MATCHED_PRICE]: true,
				[ACTION_MATCHED_EMA5]: true,
				[ACTION_MATCHED_QTY]: true,
				[ACTION_MATCHED_TIME]: true,
				[ACTION_FIRST_PRICE]: true,
				[ACTION_SELL_PRICE]: true,
				[ACTION_SELL_TIME]: true,



			},
			[DATA_PERMIT_COL]: this.permissionActionsView(),
			[DATA_KEY]: [ACTION_ID, ACTION_SYMBOL],
			[DATA_SORT]: { [ACTION_PENDING]: 'desc', [ACTION_CHART]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,


			model: new Actions()

		};

		this.updateQty = 0;
		this.watchlistIcon = {};


	}

	getIcon() {
		var watchlist = new Watchlist();

		return watchlist.getIcon();

	}

	permissionActionsView() {
		return Object.assign(
			...Object.keys(this.actions_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.actions_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.actions_struct} autoload={false}>
					<FuncBar
						left={<><FuncHideCol />
							<div className='button btn btn-danger btn-sm' style={{ fontSize: 12 }} onClick={() => {
								this.stopActions();
							}}>Finish Action</div>
						</>}
						right={<><FuncAdd /><FuncDel /><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-striped table-resizable'></MainTable>
					<Pagination></Pagination>


				</Table>

				<OrderModal ref={c => this.orderModal = c}></OrderModal>
				<OrderBinanceModal ref={c => this.OrderBinanceModal = c}></OrderBinanceModal>

			</div>
		);
	}

	componentDidMount() {
		this.refrestInterval = setInterval(() => {
			this.updateData()
		}, 5000);
		this.table.map();

		this.getIcon().then((res) => {
			this.watchlistIcon = res;
			this.table.setFilter({
				"action_account": {
					"logic": "and",
					"data": {
						"=": App.accountSelector.selected()
					}
				}
			});
	
	
		})

		if (App.accountSelector) {
			App.accountSelector.register('action_view', () => {
				this.table.map();
				this.table.setFilter({
					"action_account": {
						"logic": "and",
						"data": {
							"=": App.accountSelector.selected()
						}
					}
				});
				this.updateData();
			});
		}
	}

	updateData() {
		var model = new Actions();
		model.getUpdateData().then(res => {
			var updateLeng = Object.keys(res).length;

			if (this.updateQty != updateLeng) {
				this.updateQty = updateLeng;
				this.table.filter(false);
				return;
			}

			if (updateLeng == 0) return;

			var tableData = this.table[STRUCT_TABLE][DATA_TABLE];
			for (let i in tableData) {
				var index = tableData[i][ACTION_ID];
				if (isset(res[index])) {
					for (let j in res[index]) {
						tableData[i][j] = res[index][j];
					}
				}
			}
			this.table.reload();
		})
	}

	componentWillUnmount() {
		clearInterval(this.refrestInterval);
		App.accountSelector.unregister('action_view');
	}


	async stopActions() {


		var dataSelect = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];
		var wl = [];
		for (let i in dataSelect) {
			wl.push(dataSelect[i][ACTION_SYMBOL]);
		}

		if (wl.length == 0) {
			showLog('Please select a symbol');
			return;
		}

		var confirm = await makeQuestion('Do you want to Close Actions: ' + wl.join(', ') + '? All Postions on Binance will be Closed');
		if (!confirm) return;
		App.loading(true)
		for (let i in dataSelect) {
			await this.stopAction(dataSelect[i][ACTION_ID], false);
		}
		App.loading(false);

	}

	async closeAction(id, symbol) {
		var confirm = await makeQuestion('Do you want to Close Actions: ' + symbol + '? Postion on Binance will be Closed');
		if (!confirm) return;
		await this.stopAction(id);
	}


	stopAction(id, loading = true) {
		if (loading) App.loading(true)
		return axios.request({
			url: `/admin/actions/closePosition`,
			method: 'POST',
			data: {
				id, id
			}
		})

			.then(response => {
				if (loading) App.loading(false);
				response = response['data'];
				if (response['result']) {
					this.table.filter(loading);
				}
				else {
					error_handle(response);
				}
			})

			.catch((error) => {
				if (loading) App.loading(false);
				error_handle(error)
				return false;
			})
	}


	async gotoNextPhase(id, symbol) {

		var isConfirm = await makeQuestion('Do you want to make the next phase ' + symbol + "?");
		if (isConfirm) {
			App.loading(true);
			return axios.request({
				url: '/admin/actions/gotoNextPhase',
				method: 'POST',
				data: {
					id: id
				}
			})

				.then(response => {
					App.loading(false);
					response = response['data'];
					if (!response['result']) {
						error_handle(response)
					}
				})

				.catch((error) => {
					App.loading(false);
					error_handle(error)
					return false;
				})
		}
	}


	async getBinanceAllOrder(data){

		var account_id = data[ACTION_ACCOUNT];
		var symbol = data[ACTION_SYMBOL];
		var startTime = data[ACTION_CHART];
		var endTime = data[ACTION_SELL_TIME] ;
		var AccountsModle = new Accounts();
		var result = await AccountsModle.getTrade(account_id,symbol,startTime,endTime);
		
		this.OrderBinanceModal.modal();
		this.OrderBinanceModal.loadOrigin(Object.values(result.data));
	}

	async syncPostion(id, symbol, loading = true) {

		var confirm = await makeQuestion('Do you want to sync postion: ' + symbol + '?');
		if (!confirm) return;

		if (loading) App.loading(true)
		return axios.request({
			url: `/admin/actions/syncPosition`,
			method: 'POST',
			data: {
				id: id
			}
		})

			.then(response => {
				if (loading) App.loading(false);
				response = response['data'];
				if (response['result']) {
					this.table.filter(loading);
				}
				else {
					error_handle(response);
				}
			})

			.catch((error) => {
				if (loading) App.loading(false);
				error_handle(error)
				return false;
			})
	}
}

export default ActionsView
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

import Testnet_results from '../../model/admin/Testnet_results'
import Change_24h from '../../model/admin/Change_24h'
import TestnetOrderModal from '../../components/admin/TestnetOrderModal'
import Watchlist from '../../model/admin/Watchlist'
import FuncEdit from '../../../simulation/components/table/FuncEdit'
class Testnet_resultsView extends Component {

	constructor(props) {
		super(props);

		this.state = {
			change24h: {}
		}

		this.testnet_results_struct = {};
		this.testnet_results_struct[STRUCT_FILTERS] = {}
		this.testnet_results_struct[STRUCT_COLUMNS] = {

			[TESTNET_RESULT_SYMBOL]: {
				[COL_NAME]: lang(TESTNET_RESULT_SYMBOL),
				[COL_SORT]: true,
				// [COL_DECORATOR_IN]: (data) => {

				// 	return <b>
				// 		<img style={{ width: '20px', height: '20px', marginRight: '10px' }} src={this.watchlistIcon[data]}></img>
				// 		{data}
				// 	</b>
				// }
				[COL_DECORATOR_IN]: (col, row, data) => {
					var rowData = data[row];
					var symbol = rowData[TESTNET_RESULT_SYMBOL];
					var account = rowData[TESTNET_RESULT_ACCOUNT];
					var time = Math.floor(Number(rowData[TESTNET_RESULT_CHART]) / 1000) - 300;
					return <b style={{cursor : 'pointer'}} onClick={
						() => window.open(App.link(`/admin/testnet_chart/flex?account=${account}&symbol=${symbol}&time=${time}` ))}>
							
							<img style={{ width: '20px', height: '20px', marginRight: '10px' }} src={this.watchlistIcon[symbol]}></img>
							{symbol}
					</b>
				}

			},

			[TESTNET_RESULT_INTERVAL]: {
				[COL_NAME]: lang(TESTNET_RESULT_INTERVAL),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var interval = data[rowId][colId];
					var result;
					if (!interval) {
						var resultChart = data[rowId][TESTNET_RESULT_CHART];
						result = Number(moment().format('x')) - Number(resultChart);
					} else {
						result = interval;
					}
					result = Math.round(result / 1000);
					var d = Math.floor(result / (3600 * 24));
					var h = Math.floor(result % (3600 * 24) / 3600);
					var m = Math.floor(result % 3600 / 60);

					var dDisplay = d > 0 ? d + 'd ' : "";
					var hDisplay = h > 0 ? h + 'h ' : "";
					var mDisplay = m > 0 ? m + 'm' : 0;
					var color = '';
					if (h > 0 || d > 0) color = 'red'
					var date = dDisplay + hDisplay + mDisplay;
					return <b style={{ color: color }}>{date}</b>;

				},
			},

			[TESTNET_RESULT_CAMPAIGN]: {
				[COL_NAME]: lang(TESTNET_RESULT_CAMPAIGN),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {

					var rowData = data[rowId];
					var data = rowData[colId];
					return <div style={{ cursor: 'pointer' }} onClick={() => {
						window.open(App.link('/admin/testnetchart/single?campaign=' + rowData[TESTNET_RESULT_CAMPAIGN] + '&symbol=' + rowData[TESTNET_RESULT_SYMBOL]), '_blank');
					}}><b>{this.table.mapping[TESTNET_RESULT_CAMPAIGN][data]}</b></div>
				},



			},

			[TESTNET_RESULT_CHART]: {
				[COL_NAME]: lang(TESTNET_RESULT_CHART),
				[COL_SORT]: true,
				// [COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' },
				[COL_DECORATOR_IN]: (colId, rowId, data) => {

					var rowData = data[rowId];
					var data = rowData[colId];
					if (!data) return '';
					return <div style={{ cursor: 'pointer' }} onClick={() => {
						window.open(App.link('/admin/testnet/view?campaign=' + rowData[TESTNET_RESULT_CAMPAIGN] + '&symbol=' + rowData[TESTNET_RESULT_SYMBOL]) + "&start=" + (Math.floor(rowData[TESTNET_RESULT_CHART] / 1000) - 300) * 1000 + "&stop=" + (Math.floor(rowData[TESTNET_RESULT_CHART] / 1000) + 3000) * 1000, '_blank');
					}}><b>{moment(data, 'x').format(DATE_FORMAT)}</b></div>
				}
			},

			[TESTNET_RESULT_ACCOUNT]: {
				[COL_NAME]: lang(TESTNET_RESULT_ACCOUNT),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
			},

			[TESTNET_RESULT_CONTAINER]: {
				[COL_NAME]: lang(TESTNET_RESULT_CONTAINER),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
			},

			[TESTNET_RESULT_STRATEGY]: {
				[COL_NAME]: lang(TESTNET_RESULT_STRATEGY),
				[COL_SORT]: true,

			},

			[TESTNET_RESULT_FLOW]: {
				[COL_NAME]: lang(TESTNET_RESULT_FLOW),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
			},

			[TESTNET_RESULT_BUDGET]: {
				[COL_NAME]: lang(TESTNET_RESULT_BUDGET),
				[COL_SORT]: true,
				[COL_STYLE]: { whiteSpace: 'nowrap' },
				[COL_DECORATOR_IN]: data => data != null ? data.toFixed(3) + ' USDT' : ''
			},

			[TESTNET_RESULT_REAL_PROFIT]: {
				[COL_NAME]: lang(TESTNET_RESULT_REAL_PROFIT)  + '(%)',
				[COL_SORT]: true,
				[COL_SUM]: true,
				[COL_DECORATOR_IN]: data => data != null ? data.toFixed(3)  : ''
			},

			[TESTNET_RESULT_REAL_PNL]: {
				[COL_NAME]: lang(TESTNET_RESULT_REAL_PNL),
				[COL_SORT]: true,
				[COL_SUM]: true,
				[COL_DECORATOR_IN]: data => data != null ? data.toFixed(3) + ' USDT' : ''

			},

			[TESTNET_RESULT_EVENT_PROFIT]: {
				[COL_NAME]: lang(TESTNET_RESULT_EVENT_PROFIT)  + '(%)' ,
				[COL_SORT]: true,
				[COL_SUM]: true,
				[COL_DECORATOR_IN]: data => data != null ? data.toFixed(3)  : ''
			},
			[TESTNET_RESULT_MARGIN]: {
				[COL_NAME]: lang(TESTNET_RESULT_MARGIN),
				[COL_SORT]: true,
			},


			[TESTNET_RESULT_PROFIT]: {
				[COL_NAME]: lang(TESTNET_RESULT_PROFIT) + '(%)',
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var rowData = data[rowId];
					var data = rowData[colId];
					if (!data) return '';
					var style = { fontWeight: 'bold' };
					if (data >= 0) style['color'] = 'limegreen';
					if (data < 0) style['color'] = 'red';
					if (rowData[TESTNET_RESULT_PENDING] == 0) style['color'] = 'black';

					return <div style={style}>{(data != null && data != "") ? data.toFixed(3)  : ""}</div>
				}

			},

			'event_current_profit': {
				[COL_NAME]: lang('Current Profit') + '(%)',
				[COL_SORT]: false,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var rowData = data[rowId];
					var eventProfit = Number(rowData[TESTNET_RESULT_EVENT_PROFIT]);
					var profit = Number(rowData[TESTNET_RESULT_PROFIT]);
					if (rowData[TESTNET_RESULT_PENDING] == 1) {
						var data = profit + eventProfit;
					} else {
						var data = eventProfit;
					}

					if (!data) return '';
					var style = { fontWeight: 'bold' };
					if (data >= 0) style['color'] = 'limegreen';
					if (data < 0) style['color'] = 'red';
					if (rowData[TESTNET_RESULT_PENDING] == 0) style['color'] = 'black';
					return <div style={style}>{(data != null && data != "") ? data.toFixed(3) : ""}</div>
				}
			},

			[TESTNET_RESULT_LAST_PRICE]: {
				[COL_NAME]: lang(TESTNET_RESULT_LAST_PRICE),
				[COL_SORT]: true,

			},

			pricechange: {
				[COL_NAME]: lang('Price Change') + '(%)',
				[COL_SORT]: false,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var rowData = data[rowId];
					var profit = Number(rowData[TESTNET_RESULT_PROFIT]);
					var matchedPrice = Number(rowData[TESTNET_RESULT_MATCHED_PRICE]);
					var type = Number(rowData[TESTNET_RESULT_TYPE]);
					if (type == TESTNET_RESULT_TYPE_LONG) {
						var price = matchedPrice + profit * matchedPrice / 100;
					} else {
						var price = matchedPrice - profit * matchedPrice / 100;
					}

					var lastPrice = Number(rowData[TESTNET_RESULT_LAST_PRICE]);
					if (!lastPrice) return '';
					var change = (price - lastPrice) * 100 / lastPrice;

					var style = { fontWeight: 'bold' };
					return <div style={style}>{(change).toFixed(3)}</div>;
				}
			},



			[TESTNET_RESULT_PHASE]: {
				[COL_NAME]: lang(TESTNET_RESULT_PHASE),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
			},

			[TESTNET_RESULT_PHASE_NOTE]: {
				[COL_NAME]: lang(TESTNET_RESULT_PHASE_NOTE),
				[COL_SORT]: false,
			},
			[TESTNET_RESULT_NEXTPHASE_NOTE]: {
				[COL_NAME]: lang(TESTNET_RESULT_NEXTPHASE_NOTE),
				[COL_SORT]: false,
				[COL_DECORATOR_IN]: (data) => {
					var style = { textAlign: 'center', color: 'red', fontWeight: 'bold' };
					return <div style={style}>{data}</div>
				}
			},
			[TESTNET_RESULT_BASEPROFIT]: {
				[COL_NAME]: lang(TESTNET_RESULT_BASEPROFIT) + '(%)',
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: (data) => (data != null && data != "") ? <div style={{ color: 'blue' }}> <b>{data.toFixed(3) }</b></div> : ""
			},
			[TESTNET_RESULT_START_REASON]: {
				[COL_NAME]: lang(TESTNET_RESULT_START_REASON),
				[COL_SORT]: false,

			},
			[TESTNET_RESULT_PARAMS]: {
				[COL_NAME]: lang(TESTNET_RESULT_PARAMS),
				[COL_SORT]: false,

			},
			[TESTNET_RESULT_ENTER_PRICE]: {
				[COL_NAME]: lang(TESTNET_RESULT_ENTER_PRICE),
				[COL_SORT]: true,

			},
			[TESTNET_RESULT_HIGH]: {
				[COL_NAME]: lang(TESTNET_RESULT_HIGH),
				[COL_SORT]: true,

			},
			[TESTNET_RESULT_LOW]: {
				[COL_NAME]: lang(TESTNET_RESULT_LOW),
				[COL_SORT]: true,

			},

			[TESTNET_RESULT_TYPE]: {
				[COL_NAME]: lang(TESTNET_RESULT_TYPE),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },

			},
			[TESTNET_RESULT_BASE]: {
				[COL_NAME]: lang(TESTNET_RESULT_BASE),
				[COL_SORT]: true,

			},

			[TESTNET_RESULT_STATUS]: {
				[COL_NAME]: lang(TESTNET_RESULT_STATUS),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },

			},



			[TESTNET_RESULT_MATCHED_PRICE]: {
				[COL_NAME]: lang(TESTNET_RESULT_MATCHED_PRICE),
				[COL_SORT]: true,

			},
			[TESTNET_RESULT_MATCHED_EMA5]: {
				[COL_NAME]: lang(TESTNET_RESULT_MATCHED_EMA5),
				[COL_SORT]: true,

			},
			[TESTNET_RESULT_MATCHED_TIME]: {
				[COL_NAME]: lang(TESTNET_RESULT_MATCHED_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }

			},
			[TESTNET_RESULT_MATCHED_QTY]: {
				[COL_NAME]: lang(TESTNET_RESULT_MATCHED_QTY),
				[COL_SORT]: true,

			},
			[TESTNET_RESULT_FIRST_PRICE]: {
				[COL_NAME]: lang(TESTNET_RESULT_FIRST_PRICE),
				[COL_SORT]: true,

			},
			[TESTNET_RESULT_LAST_PRICE]: {
				[COL_NAME]: lang(TESTNET_RESULT_LAST_PRICE),
				[COL_SORT]: true,

			},

			[TESTNET_RESULT_SELL_PRICE]: {
				[COL_NAME]: lang(TESTNET_RESULT_SELL_PRICE),
				[COL_SORT]: true,

			},
			[TESTNET_RESULT_SELL_TIME]: {
				[COL_NAME]: lang(TESTNET_RESULT_SELL_TIME),
				[COL_SORT]: true,
				// [COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' },
				[COL_DECORATOR_IN]: (colId, rowId, data) => {

					var rowData = data[rowId];
					var data = rowData[colId];
					if (!data) return '';
					return <div style={{ cursor: 'pointer' }} onClick={() => {
						window.open(App.link('/admin/testnet/view?campaign=' + rowData[TESTNET_RESULT_CAMPAIGN] + '&symbol=' + rowData[TESTNET_RESULT_SYMBOL]) + "&start=" + (Math.floor(rowData[TESTNET_RESULT_SELL_TIME] / 1000) - 3000) * 1000 + "&stop=" + (Math.floor(rowData[TESTNET_RESULT_SELL_TIME] / 1000) + 300) * 1000, '_blank');
					}}><b>{moment(data, 'x').format(DATE_FORMAT)}</b></div>
				}
			},

			[TESTNET_RESULT_PENDING]: {
				[COL_NAME]: lang(TESTNET_RESULT_PENDING),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },

			},

			// 'altsup': {
			// 	[COL_NAME]: 'Alts Up',
			// 	[COL_SORT]: false,
			// 	[COL_DECORATOR_IN]: (colId, rowId, data)=>{
			// 		var time = Number(data[rowId][TESTNET_RESULT_ENTER_TIME]);
			// 		var rowData = data[rowId];
			// 		var round1m = Math.floor(time/60000) * 60000;
			// 		var round5m = Math.floor(time/300000) * 300000;
			// 		var data = '';
			// 		if(isset(this.state.change24h[round1m])) data = this.state.change24h[round1m][CHANGE24H_UP]
			// 		else if(isset(this.state.change24h[round5m])) data = this.state.change24h[round5m][CHANGE24H_UP]

			// 		return <div style={{ cursor: 'pointer' }} onClick={() => {
			// 			window.open(App.link('/admin/testnetchart/view?campaign=' + rowData[TESTNET_RESULT_CAMPAIGN] + '&symbol=' + rowData[TESTNET_RESULT_SYMBOL] + '&max=' + (time + 15*60*1000) + '&min=' + (time - 15*60*1000)), '_blank');
			// 		}}><b>{data}</b></div>
			// 	}
			// },

			// 'ema5913': {
			// 	[COL_NAME]: 'EMA5 > 9 > 13',
			// 	[COL_SORT]: false,
			// 	[COL_DECORATOR_IN]: (colId, rowId, data)=>{
			// 		var time = Number(data[rowId][TESTNET_RESULT_ENTER_TIME]);
			// 		var round1m = Math.floor(time/60000) * 60000;
			// 		var round5m = Math.floor(time/300000) * 300000;
			// 		var data = null;
			// 		if(isset(this.state.change24h[round1m])){
			// 			data = this.state.change24h[round1m]
			// 		}else if(isset(this.state.change24h[round5m])) data = this.state.change24h[round5m]
			// 		if(data == null) return '';
			// 		if(data[CHANGE24H_UP_EMA5] > data[CHANGE24H_UP_EMA9] && data[CHANGE24H_UP_EMA9] > data[CHANGE24H_UP_EMA13]) return 'Yes';
			// 		return 'No';
			// 	}
			// },

			// 'ema1393': {
			// 	[COL_NAME]: 'EMA5 < 9 < 13',
			// 	[COL_SORT]: false,
			// 	[COL_DECORATOR_IN]: (colId, rowId, data)=>{
			// 		var time = Number(data[rowId][TESTNET_RESULT_ENTER_TIME]);
			// 		var round1m = Math.floor(time/60000) * 60000;
			// 		var round5m = Math.floor(time/300000) * 300000;
			// 		var data = null;
			// 		if(isset(this.state.change24h[round1m])){
			// 			data = this.state.change24h[round1m]
			// 		}else if(isset(this.state.change24h[round5m])) data = this.state.change24h[round5m]
			// 		if(data == null) return '';
			// 		if(data[CHANGE24H_UP_EMA5] < data[CHANGE24H_UP_EMA9] && data[CHANGE24H_UP_EMA9] < data[CHANGE24H_UP_EMA13]) return 'Yes';
			// 		return 'No';
			// 	}
			// },


			// 'upchange': {
			// 	[COL_NAME]: 'Xu hương 1h tăng',
			// 	[COL_SORT]: false,
			// 	[COL_DECORATOR_IN]: (colId, rowId, data)=>{
			// 		var time = Number(data[rowId][TESTNET_RESULT_ENTER_TIME]);
			// 		var round1m = Math.floor(time/60000) * 60000;
			// 		var round5m = Math.floor(time/300000) * 300000;
			// 		var data = null;

			// 		if(isset(this.state.change24h[round5m])) data = this.state.change24h[round5m]
			// 		if(data == null) return '';
			// 		var time = Number(data[CHANGE24H_TIME]);
			// 		var before1h = time - 60 * 60 *1000;
			// 		if(isset(this.state.change24h[before1h])){
			// 			if(data[CHANGE24H_UP] > this.state.change24h[before1h][CHANGE24H_UP]) return 'Yes';
			// 			return 'No'
			// 		}
			// 		return '';
			// 	}
			// },

			// 'tuyentinh': {
			// 	[COL_NAME]: 'Tuyến tính',
			// 	[COL_SORT]: false,
			// 	[COL_DECORATOR_IN]: (colId, rowId, data)=>{
			// 		var time = Number(data[rowId][TESTNET_RESULT_ENTER_TIME]);
			// 		var round1m = Math.floor(time/60000) * 60000;
			// 		var round5m = Math.floor(time/300000) * 300000;
			// 		var data = null;

			// 		if(isset(this.state.change24h[round5m])) data = this.state.change24h[round5m]
			// 		if(data == null) return '';
			// 		var time = Number(data[CHANGE24H_TIME]);
			// 		var before15m = time - 15 * 60 *1000;
			// 		var before30m = time - 30 * 60 *1000;
			// 		var before45m = time - 45 * 60 *1000;
			// 		if(isset(this.state.change24h[before15m]) && isset(this.state.change24h[before30m]) && isset(this.state.change24h[before45m])){
			// 			if(data[CHANGE24H_UP] > this.state.change24h[before15m][CHANGE24H_UP] 
			// 			&& this.state.change24h[before15m][CHANGE24H_UP] > this.state.change24h[before30m][CHANGE24H_UP]
			// 			&& this.state.change24h[before30m][CHANGE24H_UP] > this.state.change24h[before45m][CHANGE24H_UP]
			// 				) return 'Yes';
			// 			return 'No'
			// 		}
			// 		return '';
			// 	}
			// }









		}
		this.testnet_results_struct[STRUCT_FILTERS] = {

			[TESTNET_RESULT_CAMPAIGN]: {
				[FILTER_NAME]: lang(TESTNET_RESULT_CAMPAIGN),
				[FILTER_TYPE]: 'select',
			},
			[TESTNET_RESULT_STRATEGY]: {
				[FILTER_NAME]: lang(TESTNET_RESULT_STRATEGY),
				[FILTER_TYPE]: 'select',
			},
			[TESTNET_RESULT_FLOW]: {
				[FILTER_NAME]: lang(TESTNET_RESULT_FLOW),
				[FILTER_TYPE]: 'select',
			},
			[TESTNET_RESULT_ACCOUNT]: {
				[FILTER_NAME]: lang(TESTNET_RESULT_ACCOUNT),
				[FILTER_TYPE]: 'select',
			},
			[TESTNET_RESULT_CONTAINER]: {
				[FILTER_NAME]: lang(TESTNET_RESULT_CONTAINER),
				[FILTER_TYPE]: 'select',
			},
			[TESTNET_RESULT_SYMBOL]: {
				[FILTER_NAME]: lang(TESTNET_RESULT_SYMBOL),
				[FILTER_TYPE]: 'select',
			},

			[TESTNET_RESULT_TYPE]: {
				[FILTER_NAME]: lang(TESTNET_RESULT_TYPE),
				[FILTER_TYPE]: 'select',
			},
			[TESTNET_RESULT_BASE]: {
				[FILTER_NAME]: lang(TESTNET_RESULT_BASE),
				[FILTER_TYPE]: 'text',
			},
			[TESTNET_RESULT_STATUS]: {
				[FILTER_NAME]: lang(TESTNET_RESULT_STATUS),
				[FILTER_TYPE]: 'check',
				[FILTER_OPERATION]: 'or',
			},
			[TESTNET_RESULT_PHASE]: {
				[FILTER_NAME]: lang(TESTNET_RESULT_PHASE),
				[FILTER_TYPE]: 'select',
			},
			[TESTNET_RESULT_PHASE_NOTE]: {
				[FILTER_NAME]: lang(TESTNET_RESULT_PHASE_NOTE),
				[FILTER_TYPE]: 'text',
			},
			[TESTNET_RESULT_NEXTPHASE_NOTE]: {
				[FILTER_NAME]: lang(TESTNET_RESULT_NEXTPHASE_NOTE),
				[FILTER_TYPE]: 'text',
			},

			[TESTNET_RESULT_CHART]: {
				[FILTER_NAME]: lang(TESTNET_RESULT_MATCHED_TIME),
				[FILTER_TYPE]: 'date',
				[FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },
			},
			[TESTNET_RESULT_ENTER_TIME]: {
				[FILTER_NAME]: lang(TESTNET_RESULT_ENTER_TIME),
				[FILTER_TYPE]: 'date',
				[FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },
			},
			[TESTNET_RESULT_SELL_PRICE]: {
				[FILTER_NAME]: lang(TESTNET_RESULT_SELL_PRICE),
				[FILTER_TYPE]: 'text',
			},
			[TESTNET_RESULT_SELL_TIME]: {
				[FILTER_NAME]: lang(TESTNET_RESULT_SELL_TIME),
				[FILTER_TYPE]: 'date',
				[FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },
			},

			[TESTNET_RESULT_PENDING]: {
				[FILTER_NAME]: lang(TESTNET_RESULT_PENDING),
				[FILTER_TYPE]: 'select',
			},


		}

		this.testnet_results_struct[STRUCT_EDIT] = {

			[TESTNET_RESULT_CAMPAIGN]: {
				[EDIT_NAME]: lang(TESTNET_RESULT_CAMPAIGN),
				[EDIT_TYPE]: 'select',

			},
			[TESTNET_RESULT_ACCOUNT]: {
				[EDIT_NAME]: lang(TESTNET_RESULT_ACCOUNT),
				[EDIT_TYPE]: 'select',

			},
			[TESTNET_RESULT_CONTAINER]: {
				[EDIT_NAME]: lang(TESTNET_RESULT_CONTAINER),
				[EDIT_TYPE]: 'select',

			},
			[TESTNET_RESULT_STRATEGY]: {
				[EDIT_NAME]: lang(TESTNET_RESULT_STRATEGY),
				[EDIT_TYPE]: 'select',

			},

			[TESTNET_RESULT_FLOW]: {
				[EDIT_NAME]: lang(TESTNET_RESULT_FLOW),
				[EDIT_TYPE]: 'text',

			},
			[TESTNET_RESULT_SYMBOL]: {
				[EDIT_NAME]: lang(TESTNET_RESULT_SYMBOL),
				[EDIT_TYPE]: 'text',

			},

			[TESTNET_RESULT_CHART]: {
				[EDIT_NAME]: lang(TESTNET_RESULT_CHART),
				[EDIT_TYPE]: 'date',
				[EDIT_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[EDIT_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },

			},

			[TESTNET_RESULT_ENTER_PRICE]: {
				[EDIT_NAME]: lang(TESTNET_RESULT_ENTER_PRICE),
				[EDIT_TYPE]: 'text',

			},
			[TESTNET_RESULT_HIGH]: {
				[EDIT_NAME]: lang(TESTNET_RESULT_HIGH),
				[EDIT_TYPE]: 'text',

			},
			[TESTNET_RESULT_LOW]: {
				[EDIT_NAME]: lang(TESTNET_RESULT_LOW),
				[EDIT_TYPE]: 'text',

			},
			[TESTNET_RESULT_TYPE]: {
				[EDIT_NAME]: lang(TESTNET_RESULT_TYPE),
				[EDIT_TYPE]: 'Number',

			},
			[TESTNET_RESULT_BASE]: {
				[EDIT_NAME]: lang(TESTNET_RESULT_BASE),
				[EDIT_TYPE]: 'text',

			},
			[TESTNET_RESULT_PARAMS]: {
				[EDIT_NAME]: lang(TESTNET_RESULT_PARAMS),
				[EDIT_TYPE]: 'textarea',

			},
			[TESTNET_RESULT_STATUS]: {
				[EDIT_NAME]: lang(TESTNET_RESULT_STATUS),
				[EDIT_TYPE]: 'select',

			},

			[TESTNET_RESULT_PHASE]: {
				[EDIT_NAME]: lang(TESTNET_RESULT_PHASE),
				[EDIT_TYPE]: 'select',

			},

			[TESTNET_RESULT_PHASE_NOTE]: {
				[EDIT_NAME]: lang(TESTNET_RESULT_PHASE_NOTE),
				[EDIT_TYPE]: 'textarea',

			},
			[TESTNET_RESULT_NEXTPHASE_NOTE]: {
				[EDIT_NAME]: lang(TESTNET_RESULT_NEXTPHASE_NOTE),
				[EDIT_TYPE]: 'textarea',

			},

			[TESTNET_RESULT_MATCHED_PRICE]: {
				[EDIT_NAME]: lang(TESTNET_RESULT_MATCHED_PRICE),
				[EDIT_TYPE]: 'number',

			},
			[TESTNET_RESULT_MATCHED_TIME]: {
				[EDIT_NAME]: lang(TESTNET_RESULT_MATCHED_TIME),
				[EDIT_TYPE]: 'date',
				[EDIT_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[EDIT_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },

			},
			[TESTNET_RESULT_FIRST_PRICE]: {
				[EDIT_NAME]: lang(TESTNET_RESULT_FIRST_PRICE),
				[EDIT_TYPE]: 'number',

			},

			[TESTNET_RESULT_LAST_PRICE]: {
				[EDIT_NAME]: lang(TESTNET_RESULT_LAST_PRICE),
				[EDIT_TYPE]: 'number',

			},
			[TESTNET_RESULT_SELL_PRICE]: {
				[EDIT_NAME]: lang(TESTNET_RESULT_SELL_PRICE),
				[EDIT_TYPE]: 'text',

			},
			[TESTNET_RESULT_SELL_TIME]: {
				[EDIT_NAME]: lang(TESTNET_RESULT_SELL_TIME),
				[EDIT_TYPE]: 'date',
				[EDIT_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[EDIT_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },

			},

			[TESTNET_RESULT_PROFIT]: {
				[EDIT_NAME]: lang(TESTNET_RESULT_PROFIT),
				[EDIT_TYPE]: 'number',

			},

			[TESTNET_RESULT_EVENT_PROFIT]: {
				[EDIT_NAME]: lang(TESTNET_RESULT_EVENT_PROFIT),
				[EDIT_TYPE]: 'number',

			},



			[TESTNET_RESULT_REAL_PROFIT]: {
				[EDIT_NAME]: lang(TESTNET_RESULT_REAL_PROFIT),
				[EDIT_TYPE]: 'number',

			},
			[TESTNET_RESULT_PENDING]: {
				[EDIT_NAME]: lang(TESTNET_RESULT_PENDING),
				[EDIT_TYPE]: 'Number',

			},


		}

		this.testnet_results_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData} ><div className='button btn btn-sm btn-info' style={{ fontSize: 12 }}>Edit</div></FuncEditRow>
					<div className='button btn btn-sm btn-info' style={{ fontSize: 12 }} onClick={c => {
						this.labOrder.modal();
						this.labOrder.loadData(rowData);
					}}>Orders</div>
					<div className='button btn btn-danger btn-sm' style={{ fontSize: 10 }} onClick={() => {
						this.closeAction(rowData[TESTNET_RESULT_ID], rowData[TESTNET_RESULT_SYMBOL])
					}}>Close</div>
				</div>
			},
			[ROW_FOOTER]: (datas, visibleColumns) => {

				var totalRealProfit = 0;

				for (let i in datas) {
					var data = datas[i];
					if (data[TESTNET_RESULT_PENDING] == 0 && data[TESTNET_RESULT_STATUS] != TESTNET_RESULT_STATUS_CANCLE) {
						totalRealProfit += Number(data[TESTNET_RESULT_REAL_PROFIT]);
					}
				}
				return <tr>
					<td colSpan={7}></td>

					<td colSpan={1} style={{ fontWeight: 'bold', color: (totalRealProfit > 0 ? "green" : "red"), textAlign: 'right' }}>Total Real Profit: {totalRealProfit}%</td>

					<td colSpan={visibleColumns.length - 8}></td>
				</tr>

			}
		};
		this.testnet_results_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: TESTNET_RESULTS_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {
				[TESTNET_RESULT_CHART]: true,
				[TESTNET_RESULT_REAL_PROFIT]: true,
				[TESTNET_RESULT_EVENT_PROFIT]: true,
				'event_current_profit': true,
				[TESTNET_RESULT_LAST_PRICE]: true,
				[TESTNET_RESULT_FIRST_PRICE]: true,
				pricechange: true,
				[TESTNET_RESULT_PHASE_NOTE]: true,
				[TESTNET_RESULT_PARAMS]: true,
				[TESTNET_RESULT_START_REASON]: true,
				[TESTNET_RESULT_ENTER_PRICE]: true,
				[TESTNET_RESULT_HIGH]: true,
				[TESTNET_RESULT_LOW]: true,
				[TESTNET_RESULT_BASE]: true,
				[TESTNET_RESULT_MATCHED_EMA5]: true,
				[TESTNET_RESULT_MATCHED_PRICE]: true,
				[TESTNET_RESULT_MATCHED_TIME]: true,
				[TESTNET_RESULT_MATCHED_QTY]: true,
				[TESTNET_RESULT_SELL_PRICE]: true,
				[TESTNET_RESULT_SELL_TIME]: true
			},
			[DATA_PERMIT_COL]: this.permissionTestnet_resultsView(),
			[DATA_KEY]: [TESTNET_RESULT_ID],
			[DATA_SORT]: { [TESTNET_RESULT_ID]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Testnet_results()

		};

		this.updateQty = 0;
		this.watchlistIcon = {};


	}
	getIcon() {
		var watchlist = new Watchlist();

		return watchlist.getIcon();

	}

	permissionTestnet_resultsView() {
		return Object.assign(
			...Object.keys(this.testnet_results_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.testnet_results_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.testnet_results_struct} autoload={false}>
					<FuncBar
						left={<FuncHideCol />}
						right={<><FuncAdd /><FuncDel /><FuncEdit></FuncEdit><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-striped table-resizable'></MainTable>
					<Pagination></Pagination>

				</Table>

				<TestnetOrderModal ref={c => this.labOrder = c}></TestnetOrderModal>


			</div>
		);
	}

	updateData() {
		var model = new Testnet_results();
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
				var index = tableData[i][TESTNET_RESULT_ID];
				if (isset(res[index])) {
					for (let j in res[index]) {
						tableData[i][j] = res[index][j];
					}
				}
			}
			this.table.reload();
		})
	}

	componentDidMount() {
		if (App.accountSelectorTestnet) {
			App.accountSelectorTestnet.register('testnet_results_view', () => {
				this.table.setFilter({
					[TESTNET_RESULT_ACCOUNT]: {
						"logic": "and",
						"data": {
							"=": App.accountSelectorTestnet ? App.accountSelectorTestnet.selected() : ''
						}
					},
					[TESTNET_RESULT_PENDING]: {
						"logic": "and",
						"data": {
							"=": 1
						}
					}
				});
				this.table.filter();
			});



		}
		this.refrestInterval = setInterval(() => {
			this.updateData();
		}, 5000);
		this.table.map();

		this.getIcon().then((res) => {
			this.watchlistIcon = res;
			this.table.setFilter({
				[TESTNET_RESULT_ACCOUNT]: {
					"logic": "and",
					"data": {
						"=": App.accountSelectorTestnet ? App.accountSelectorTestnet.selected() : ''
					}
				},
				[TESTNET_RESULT_PENDING]: {
					"logic": "and",
					"data": {
						"=": 1
					}
				}
			});

		})




		this.getChange24h();
	}

	componentWillUnmount() {
		clearInterval(this.refrestInterval);
	}

	getChange24h() {
		var model = new Change_24h();
		var data = model.get([], {
			'selected': [CHANGE24H_ID, CHANGE24H_TIME, CHANGE24H_UP, CHANGE24H_1H_UP, CHANGE24H_15M_UP, CHANGE24H_UP_EMA5, CHANGE24H_UP_EMA9, CHANGE24H_UP_EMA13,],
			'limit': 5000,
		}).then(res => {
			if (res['result']) {
				var datas = res['data'];
				var dataIndex = {};
				for (let i in datas) {
					var data = datas[i];
					var id = Math.floor(Number(data[CHANGE24H_TIME]) / 60000) * 60000;
					dataIndex[id] = data;
				}

				this.setState({ change24h: dataIndex })
			}
		});

	}

	async stopActions() {


		var dataSelect = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];
		var wl = [];
		for (let i in dataSelect) {
			wl.push(dataSelect[i][TESTNET_RESULT_SYMBOL]);
		}

		if (wl.length == 0) {
			showLog('Please select a symbol');
			return;
		}

		var confirm = await makeQuestion('Do you want to Close Actions: ' + wl.join(', ') + '? All Postions on Binance will be Closed');
		if (!confirm) return;
		App.loading(true)
		for (let i in dataSelect) {
			await this.stopAction(dataSelect[i][TESTNET_RESULT_ID], false);
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
			url: `/admin/testnet_results/closePosition`,
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
}

export default Testnet_resultsView
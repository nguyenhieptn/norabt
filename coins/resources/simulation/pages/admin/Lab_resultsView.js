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

import Lab_results from '../../model/admin/Lab_results'
import LabOrderModal from '../../components/admin/LabOrderModal'

import Lab_candle_1m from '../../model/admin/Lab_candle_1m'

import Coinmarket from '../../../react/model/admin/Coinmarket'
class Lab_resultsView extends Component {

	constructor(props) {
		super(props);

		this.state = {
			mapVolume: {}
		}

		this.lab_results_struct = {};
		this.lab_results_struct[STRUCT_FILTERS] = {}
		this.lab_results_struct[STRUCT_COLUMNS] = {


			[LAB_RESULT_SYMBOL]: {
				[COL_NAME]: lang(LAB_RESULT_SYMBOL),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (col, row, data) => {
					var rowData = data[row];
					var symbol = rowData[LAB_RESULT_SYMBOL];
					var account = rowData[LAB_RESULT_ACCOUNT];
					var time = Math.floor(Number(rowData[LAB_RESULT_CHART]) / 1000) - 300;
					var rankData = (symbol == '1000SHIBUSDT' ? 'SHIBUSDT' : symbol);
					return <b style={{ cursor: 'pointer' }} onClick={
						() => window.open(App.link(`/admin/chart/flex?account=${account}&symbol=${symbol}&time=${time}`))}>
						{symbol}
						<span style={{ color: 'blue', fontWeight: 'normal' }}> [{get(this.coinMarketData[rankData], '')}]</span>
					</b>
				}

			},

			[LAB_RESULT_INTERVAL]: {
				// [COL_NAME]: lang(LAB_RESULT_INTERVAL),
				[COL_NAME]: 'Interval',
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: (data) => {
					// data = Math.round(data/60000);
					// if(data > 60)  	return <b style={{color : 'red'}} >{data}</b>;
					// return <b  >{data}</b>;

					data = Math.round(data / 1000);
					var d = Math.floor(data / (3600 * 24));
					var h = Math.floor(data % (3600 * 24) / 3600);
					var m = Math.floor(data % 3600 / 60);

					var dDisplay = d > 0 ? d + 'd ' : "";
					var hDisplay = h > 0 ? h + 'h ' : "";
					var mDisplay = m > 0 ? m + 'm' : 0;
					var color = '';
					if (h > 0 || d > 0) color = 'red'
					var date = dDisplay + hDisplay + mDisplay;
					return <b style={{ color: color }}>{date}</b>;
				},
			},

			[LAB_RESULT_CAMPAIGN]: {
				[COL_NAME]: lang(LAB_RESULT_CAMPAIGN),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {

					var rowData = data[rowId];
					var data = rowData[colId];
					return <div style={{ cursor: 'pointer' }} onClick={() => {
						window.open(App.link('/admin/chart/view?campaign=' + rowData[LAB_RESULT_CAMPAIGN] + '&symbol=' + rowData[LAB_RESULT_SYMBOL]) + "&min=" + (Math.round(rowData[LAB_RESULT_CHART] / 1000)) + "&max=" + (Math.round(rowData[LAB_RESULT_SELL_TIME] / 1000)), '_blank');
					}}><b>{this.table.mapping[LAB_RESULT_CAMPAIGN][data]}</b></div>
				}

			},
			[LAB_RESULT_ACCOUNT]: {
				[COL_NAME]: lang(LAB_RESULT_ACCOUNT),
				[COL_SORT]: true,

			},
			[LAB_RESULT_CONTAINER]: {
				[COL_NAME]: lang(LAB_RESULT_CONTAINER),
				[COL_SORT]: true,

			},
			[LAB_RESULT_STRATEGY]: {
				[COL_NAME]: lang(LAB_RESULT_STRATEGY),
				[COL_SORT]: true,

			},

			[LAB_RESULT_FLOW]: {
				[COL_NAME]: lang(LAB_RESULT_FLOW),
				[COL_SORT]: true,

			},

			[LAB_RESULT_CHART]: {
				[COL_NAME]: lang(LAB_RESULT_CHART),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},

			[LAB_RESULT_ENTER_TIME]: {
				[COL_NAME]: lang(LAB_RESULT_ENTER_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},
			[LAB_RESULT_ENTER_PRICE]: {
				[COL_NAME]: lang(LAB_RESULT_ENTER_PRICE),
				[COL_SORT]: true,
				[COL_STYLE]: { whiteSpace: 'nowrap' },
				[COL_DECORATOR_IN]: data => data != null ? formatNumber(data.toFixed(3)) : ''
			},

			[LAB_RESULT_ORDER_TIME]: {
				[COL_NAME]: lang(LAB_RESULT_ORDER_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},
			[LAB_RESULT_ORDER_PRICE]: {
				[COL_NAME]: lang(LAB_RESULT_ORDER_PRICE),
				[COL_SORT]: true,
				[COL_STYLE]: { whiteSpace: 'nowrap' },
				[COL_DECORATOR_IN]: data => data != null ? formatNumber(data.toFixed(3)) : ''
			},

			[LAB_RESULT_BUDGET]: {
				[COL_NAME]: lang(LAB_RESULT_BUDGET),
				[COL_SORT]: true,
				[COL_STYLE]: { whiteSpace: 'nowrap' },
				[COL_DECORATOR_IN]: data => data != null ? formatNumber(data.toFixed(3))  : ''
			},

			[LAB_RESULT_PROFIT_INVEST]: {
				[COL_NAME]: lang(LAB_RESULT_PROFIT_INVEST) + '(%)',
		
				[COL_SORT]: true,
				[COL_STYLE]: { whiteSpace: 'nowrap' },
				[COL_DECORATOR_IN]: data => data != null ? formatNumber(data.toFixed(3))   : ''
			},
			

			[LAB_RESULT_WALLET_BALANCE]: {
				[COL_NAME]: lang(LAB_RESULT_WALLET_BALANCE),
		
				[COL_SORT]: true,
				[COL_STYLE]: { whiteSpace: 'nowrap' },
				[COL_DECORATOR_IN]: data => data != null ? formatNumber(data.toFixed(3))  : ''
			},
			[LAB_RESULT_MARGIN]: {
				[COL_NAME]: lang(LAB_RESULT_MARGIN),
				[COL_SORT]: true,
			},

			[LAB_RESULT_REAL_PROFIT]: {
				[COL_NAME]: lang(LAB_RESULT_REAL_PROFIT) + '(%)',
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => data != null ? formatNumber(data.toFixed(3)) : '',
				[COL_SUM]: true
			},

			[LAB_RESULT_REAL_PNL]: {
				[COL_NAME]: lang(LAB_RESULT_REAL_PNL),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => data != null ? formatNumber(data.toFixed(3))  : '',
				[COL_SUM]: true
			},

			[LAB_RESULT_EVENT_PROFIT]: {
				[COL_NAME]: lang(LAB_RESULT_EVENT_PROFIT) + '(%)',
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => data != null ? data.toFixed(3)  : ''

			},

			[LAB_RESULT_PROFIT]: {
				[COL_NAME]: lang(LAB_RESULT_PROFIT) + '(%)',
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var rowData = data[rowId];
					var data = rowData[colId];
					if (!data) return '';
					var style = { fontWeight: 'bold' };
					if (data >= 0) style['color'] = 'limegreen';
					if (data < 0) style['color'] = 'red';
					if (rowData[LAB_RESULT_PENDING] == 0) style['color'] = 'black';

					// return <div style={style}>{(data != null && data != "") ? data.toFixed(3) + "%" : ""}</div>
					return <div style={style}>{(data != null && data != "") ? data.toFixed(3) : ""}</div>
				}

			},
			[LAB_RESULT_BASEPROFIT]: {
				[COL_NAME]: lang(LAB_RESULT_BASEPROFIT) + '(%)',
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: (data) => (data != null && data != "") ? <div style={{ color: 'blue' }}> <b>{data.toFixed(3) }</b></div> : ""

			},

			[LAB_RESULT_PHASE]: {
				[COL_NAME]: lang(LAB_RESULT_PHASE),
				[COL_SORT]: true,
			},

			[LAB_RESULT_ORDER_PRICE]: {
				[COL_NAME]: lang(LAB_RESULT_ORDER_PRICE),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => data != null ? formatNumber(data.toFixed(3)) : ''

			},
			[LAB_RESULT_HIGH]: {
				[COL_NAME]: lang(LAB_RESULT_HIGH),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => data != null ? formatNumber(data.toFixed(3)) : ''

			},
			[LAB_RESULT_LOW]: {
				[COL_NAME]: lang(LAB_RESULT_LOW),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => data != null ? formatNumber(data.toFixed(3)) : ''

			},

			[LAB_RESULT_TYPE]: {
				[COL_NAME]: lang(LAB_RESULT_TYPE),
				[COL_SORT]: true,

			},
			[LAB_RESULT_BASE]: {
				[COL_NAME]: lang(LAB_RESULT_BASE),
				[COL_SORT]: true,
			},

			[LAB_RESULT_BTC_WMA45_1D]: {
				[COL_NAME]: lang(LAB_RESULT_BTC_WMA45_1D),
				[COL_SORT]: true,
			},

			[LAB_RESULT_BTC_WMA45_1W]: {
				[COL_NAME]: lang(LAB_RESULT_BTC_WMA45_1W),
				[COL_SORT]: true,
			},

			[LAB_RESULT_LOG]: {
				[COL_NAME]: lang(LAB_RESULT_LOG),
				[COL_SORT]: true,

			},

			[LAB_RESULT_START_REASON]: {
				[COL_NAME]: lang(LAB_RESULT_START_REASON),
				[COL_SORT]: false,

			},
			[LAB_RESULT_PARAMS]: {
				[COL_NAME]: lang(LAB_RESULT_PARAMS),
				[COL_SORT]: false,

			},
			[LAB_RESULT_STATUS]: {
				[COL_NAME]: lang(LAB_RESULT_STATUS),
				[COL_SORT]: true,

			},
			[LAB_RESULT_MATCHED_PRICE]: {
				[COL_NAME]: lang(LAB_RESULT_MATCHED_PRICE),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => data != null ? formatNumber(data.toFixed(3)) : ''

			},
			[LAB_RESULT_MATCHED_QTY]: {
				[COL_NAME]: lang(LAB_RESULT_MATCHED_QTY),
				[COL_SORT]: true,
				// [COL_DECORATOR_IN]: data => data != null ? formatNumber(data.toFixed(3)) : ''
				[COL_DECORATOR_IN]: (col, row, data) => {
					var rowData = data[row];
					let matchedQTY = formatNumber(rowData[LAB_RESULT_MATCHED_QTY].toFixed(3))
					let volume = rowData['lab_volume_1m']

					if (rowData[LAB_RESULT_MATCHED_QTY] - volume > 0) {
						return <span style={{ color: 'red' }}>{matchedQTY}</span>
					} else {
						return matchedQTY
					}


				}

			},
			'lab_volume_1m': {
				[COL_NAME]: 'Volume 1M',
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => data != null ? formatNumber(Number(data).toFixed(3)) : ''
			},
			[LAB_RESULT_MATCHED_EMA5]: {
				[COL_NAME]: lang(LAB_RESULT_MATCHED_EMA5),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => data != null ? formatNumber(data.toFixed(3)) : ''

			},
			[LAB_RESULT_MATCHED_TIME]: {
				[COL_NAME]: lang(LAB_RESULT_MATCHED_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},

			[LAB_RESULT_SELL_PRICE]: {
				[COL_NAME]: lang(LAB_RESULT_SELL_PRICE),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => data != null ? formatNumber(data.toFixed(3)) : ''

			},
			[LAB_RESULT_SELL_TIME]: {
				[COL_NAME]: lang(LAB_RESULT_SELL_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},

			[LAB_RESULT_FIRST_PRICE]: {
				[COL_NAME]: lang(LAB_RESULT_FIRST_PRICE),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => data != null ? formatNumber(data.toFixed(3)) : ''

			},
			[LAB_RESULT_LAST_PRICE]: {
				[COL_NAME]: lang(LAB_RESULT_LAST_PRICE),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => data != null ? formatNumber(data.toFixed(3)) : ''

			},

			[LAB_RESULT_PENDING]: {
				[COL_NAME]: lang(LAB_RESULT_PENDING),
				[COL_SORT]: true,

			},

			[LAB_RESULT_1D_RSI_14]: {
				[COL_NAME]: lang(LAB_RESULT_1D_RSI_14),
				[COL_SORT]: true,

			},
			[LAB_RESULT_1D_RSI_EMA9]: {
				[COL_NAME]: lang(LAB_RESULT_1D_RSI_EMA9),
				[COL_SORT]: true,

			},
			[LAB_RESULT_1D_RSI_WMA]: {
				[COL_NAME]: lang(LAB_RESULT_1D_RSI_WMA),
				[COL_SORT]: true,

			},



		}
		this.lab_results_struct[STRUCT_FILTERS] = {
			[LAB_RESULT_INTERVAL]: {
				[FILTER_NAME]: lang(LAB_RESULT_INTERVAL),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<='],

				[FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; let outData = data / 1000 / 60; return outData },
				[FILTER_DECORATOR_OUT]: (data) => { let outData = data * 60 * 1000; return outData },
			},

			[LAB_RESULT_CAMPAIGN]: {
				[FILTER_NAME]: lang(LAB_RESULT_CAMPAIGN),
				[FILTER_TYPE]: 'select',
			},
			[LAB_RESULT_SYMBOL]: {
				[FILTER_NAME]: lang(LAB_RESULT_SYMBOL),
				[FILTER_TYPE]: 'select',
			},
			[LAB_RESULT_CONTAINER]: {
				[FILTER_NAME]: lang(LAB_RESULT_CONTAINER),
				[FILTER_TYPE]: 'select',
			},
			[LAB_RESULT_ACCOUNT]: {
				[FILTER_NAME]: lang(LAB_RESULT_ACCOUNT),
				[FILTER_TYPE]: 'select_unsort',
			},
			[LAB_RESULT_STRATEGY]: {
				[FILTER_NAME]: lang(LAB_RESULT_STRATEGY),
				[FILTER_TYPE]: 'select_unsort',
			},
			[LAB_RESULT_FLOW]: {
				[FILTER_NAME]: lang(LAB_RESULT_FLOW),
				[FILTER_TYPE]: 'select',
			},
			[LAB_RESULT_CHART]: {
				[FILTER_NAME]: lang(LAB_RESULT_CHART),
				[FILTER_TYPE]: 'date',
				[FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },
			},
			[LAB_RESULT_ORDER_TIME]: {
				[FILTER_NAME]: lang(LAB_RESULT_ORDER_TIME),
				[FILTER_TYPE]: 'date',
				[FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },
			},

			[LAB_RESULT_PHASE]: {
				[FILTER_NAME]: lang(LAB_RESULT_PHASE),
				[FILTER_TYPE]: 'select',
			},
			[LAB_RESULT_TYPE]: {
				[FILTER_NAME]: lang(LAB_RESULT_TYPE),
				[FILTER_TYPE]: 'select',
			},
			[LAB_RESULT_BASE]: {
				[FILTER_NAME]: lang(LAB_RESULT_BASE),
				[FILTER_TYPE]: 'text',
			},
			[LAB_RESULT_STATUS]: {
				[FILTER_NAME]: lang(LAB_RESULT_STATUS),
				[FILTER_TYPE]: 'check',
				[FILTER_OPERATION]: 'or',
			},

			[LAB_RESULT_MATCHED_TIME]: {
				[FILTER_NAME]: lang(LAB_RESULT_MATCHED_TIME),
				[FILTER_TYPE]: 'date',
				[FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },
			},
			[LAB_RESULT_SELL_PRICE]: {
				[FILTER_NAME]: lang(LAB_RESULT_SELL_PRICE),
				[FILTER_TYPE]: 'text',
			},
			[LAB_RESULT_SELL_TIME]: {
				[FILTER_NAME]: lang(LAB_RESULT_SELL_TIME),
				[FILTER_TYPE]: 'date',
				[FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },
			},

			[LAB_RESULT_PENDING]: {
				[FILTER_NAME]: lang(LAB_RESULT_PENDING),
				[FILTER_TYPE]: 'select',
			},
			[LAB_RESULT_BTC_WMA45_1D]: {
				[FILTER_NAME]: lang(LAB_RESULT_BTC_WMA45_1D),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<='],
			},
			[LAB_RESULT_BTC_WMA45_1W]: {
				[FILTER_NAME]: lang(LAB_RESULT_BTC_WMA45_1W),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<='],
			},

			[LAB_RESULT_1D_RSI_14]: {
				[FILTER_NAME]: lang(LAB_RESULT_1D_RSI_14),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<='],
			},
			[LAB_RESULT_1D_RSI_EMA9]: {
				[FILTER_NAME]: lang(LAB_RESULT_1D_RSI_EMA9),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<='],
			},
			[LAB_RESULT_1D_RSI_WMA]: {
				[FILTER_NAME]: lang(LAB_RESULT_1D_RSI_WMA),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<='],
			},


		}

		this.lab_results_struct[STRUCT_EDIT] = {

			[LAB_RESULT_CAMPAIGN]: {
				[EDIT_NAME]: lang(LAB_RESULT_CAMPAIGN),
				[EDIT_TYPE]: 'select',

			},
			[LAB_RESULT_SYMBOL]: {
				[EDIT_NAME]: lang(LAB_RESULT_SYMBOL),
				[EDIT_TYPE]: 'select',

			},
			[LAB_RESULT_STRATEGY]: {
				[EDIT_NAME]: lang(LAB_RESULT_STRATEGY),
				[EDIT_TYPE]: 'select',

			},

			[LAB_RESULT_FLOW]: {
				[EDIT_NAME]: lang(LAB_RESULT_FLOW),
				[EDIT_TYPE]: 'text',
			},

			[LAB_RESULT_CHART]: {
				[EDIT_NAME]: lang(LAB_RESULT_CHART),
				[EDIT_TYPE]: 'date',

			},
			[LAB_RESULT_ORDER_PRICE]: {
				[EDIT_NAME]: lang(LAB_RESULT_ORDER_PRICE),
				[EDIT_TYPE]: 'text',

			},
			[LAB_RESULT_HIGH]: {
				[EDIT_NAME]: lang(LAB_RESULT_HIGH),
				[EDIT_TYPE]: 'text',

			},
			[LAB_RESULT_LOW]: {
				[EDIT_NAME]: lang(LAB_RESULT_LOW),
				[EDIT_TYPE]: 'text',

			},
			[LAB_RESULT_TYPE]: {
				[EDIT_NAME]: lang(LAB_RESULT_TYPE),
				[EDIT_TYPE]: 'select',

			},
			[LAB_RESULT_BASE]: {
				[EDIT_NAME]: lang(LAB_RESULT_BASE),
				[EDIT_TYPE]: 'textarea',

			},
			[LAB_RESULT_PARAMS]: {
				[EDIT_NAME]: lang(LAB_RESULT_PARAMS),
				[EDIT_TYPE]: 'textarea',

			},
			[LAB_RESULT_STATUS]: {
				[EDIT_NAME]: lang(LAB_RESULT_STATUS),
				[EDIT_TYPE]: 'Number',

			},
			[LAB_RESULT_MATCHED_PRICE]: {
				[EDIT_NAME]: lang(LAB_RESULT_MATCHED_PRICE),
				[EDIT_TYPE]: 'text',

			},
			[LAB_RESULT_MATCHED_TIME]: {
				[EDIT_NAME]: lang(LAB_RESULT_MATCHED_TIME),
				[EDIT_TYPE]: 'date',

			},
			[LAB_RESULT_SELL_PRICE]: {
				[EDIT_NAME]: lang(LAB_RESULT_SELL_PRICE),
				[EDIT_TYPE]: 'text',

			},
			[LAB_RESULT_SELL_TIME]: {
				[EDIT_NAME]: lang(LAB_RESULT_SELL_TIME),
				[EDIT_TYPE]: 'date',

			},
			[LAB_RESULT_PROFIT]: {
				[EDIT_NAME]: lang(LAB_RESULT_PROFIT),
				[EDIT_TYPE]: 'text',

			},
			[LAB_RESULT_PENDING]: {
				[EDIT_NAME]: lang(LAB_RESULT_PENDING),
				[EDIT_TYPE]: 'Number',

			},


		}

		this.lab_results_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData} ><div className='button btn btn-sm btn-info' style={{ fontSize: 12 }}>Edit</div></FuncEditRow>
					<div className='button btn btn-sm btn-info' style={{ fontSize: 12 }} onClick={c => {
						this.labOrder.modal();
						this.labOrder.loadData(rowData);
					}}>Orders</div>
				</div>
			},
			[ROW_FOOTER]: (datas, visibleColumns) => {

				var totalRealProfit = 0;

				for (let i in datas) {
					var data = datas[i];
					totalRealProfit += Number(data[LAB_RESULT_REAL_PROFIT]);
				}
				return <tr>
					<td colSpan={7}></td>

					<td colSpan={1} style={{ fontWeight: 'bold', color: (totalRealProfit > 0 ? "green" : "red"), textAlign: 'right' }}>Total Real Profit: {totalRealProfit}%</td>

					<td colSpan={visibleColumns.length - 8}></td>
				</tr>

			}
		};
		this.lab_results_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: LAB_RESULTS_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {


				[LAB_RESULT_ENTER_PRICE]: true,
				[LAB_RESULT_ENTER_TIME]: true,
				[LAB_RESULT_ORDER_TIME]: true,
				[LAB_RESULT_ORDER_PRICE]: true,
				[LAB_RESULT_REAL_PROFIT]: true,
				[LAB_RESULT_EVENT_PROFIT]: true,
				[LAB_RESULT_BASEPROFIT]: true,
				[LAB_RESULT_HIGH]: true,
				[LAB_RESULT_LOW]: true,
				[LAB_RESULT_BASE]: true,
				[LAB_RESULT_START_REASON]: true,
				[LAB_RESULT_MATCHED_PRICE]: true,
				[LAB_RESULT_MATCHED_TIME]: true,
				[LAB_RESULT_MATCHED_QTY]: true,

				[LAB_RESULT_MATCHED_EMA5]: true,

				[LAB_RESULT_LAST_PRICE]: true,
				[LAB_RESULT_FIRST_PRICE]: true,
				[LAB_RESULT_PENDING]: true,

				[LAB_RESULT_SELL_PRICE]: true,
				[LAB_RESULT_SELL_TIME]: true,


			},
			[DATA_PERMIT_COL]: this.permissionLab_resultsView(),
			[DATA_KEY]: [LAB_RESULT_ID],
			[DATA_SORT]: { [LAB_RESULT_ID]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Lab_results()

		};

		this.coinMarketData = {}


	}

	permissionLab_resultsView() {
		return Object.assign(
			...Object.keys(this.lab_results_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.lab_results_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	getRankCoinMarket() {
		var model = new Coinmarket();
		return model.getRank()
	}

	updateData() {

		let nameAccount = App.accountSelectorLab.accountIndex[App.accountSelectorLab.selected()][LAB_ACCOUNT_NAME]
		makeQuestion(`Do you want update 1d RSI, 1d RSI Ema9 and 1d RSI WMA for account ${nameAccount} `).then(res => {
			if (res) {
				let model = new Lab_results();


				model.updateIndicator({ 'account_id': App.accountSelectorLab.selected() }).then(res => {

					if (res['result']) {
						this.table.filter()
					}


				})
			}
		})
	}

	updateWalletBalance(){

		let nameAccount = App.accountSelectorLab.accountIndex[ App.accountSelectorLab.selected()][LAB_ACCOUNT_NAME]
		makeQuestion(`Do you want update  Wallet Balance  for account ${nameAccount} `).then(res => {
			if(res){
				let model = new Lab_results();


				model.updateWalletBalance({'account_id' : App.accountSelectorLab.selected()}).then(res => {

					if(res['result']){
						this.table.filter()
					}

					
				})
			}
		})
	}

	updateProfitInvest(){

		let nameAccount = App.accountSelectorLab.accountIndex[ App.accountSelectorLab.selected()][LAB_ACCOUNT_NAME]
		makeQuestion(`Do you want update  Profit Invest  for account ${nameAccount} `).then(res => {
			if(res){

				let model = new Lab_results();


				model.updateProfitInvest({'account_id' : App.accountSelectorLab.selected()}).then(res => {

					if(res['result']){
						this.table.filter()
					}

					
				})
			}
		})
	}


	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.lab_results_struct} autoload={false} >
					<FuncBar
						left={<>
							<FuncHideCol />
							<button type="button" className="button btn btn-sm btn-primary" onClick={() => this.updateData()}>Update Data</button>
							<button type="button" className="button btn btn-sm btn-primary" onClick={() => this.updateWalletBalance()}>Update Wallet Balance</button>
							<button type="button" className="button btn btn-sm btn-primary" onClick={() => this.updateProfitInvest()}>Update Profit Invest</button>
						</>}
						right={<><FuncAdd /><FuncDel /><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-striped table-resizable'></MainTable>
					<Pagination></Pagination>

				</Table>

				<LabOrderModal ref={c => this.labOrder = c}></LabOrderModal>


			</div>
		);
	}

	async componentDidMount() {
		this.coinMarketData = await this.getRankCoinMarket()
		this.table.map().then(res => {

			if (App.accountSelectorLab) {
				App.accountSelectorLab.register('lab_results_view', () => {
					this.table.setFilter({
						[LAB_RESULT_ACCOUNT]: {
							"logic": "and",
							"data": {
								"=": App.accountSelectorLab ? App.accountSelectorLab.selected() : ''
							}
						}
					})
					this.table.filter();
				});

				this.table.setFilter({
					[LAB_RESULT_ACCOUNT]: {
						"logic": "and",
						"data": {
							"=": App.accountSelectorLab ? App.accountSelectorLab.selected() : ''
						}
					}
				});

				this.table.filter();
			}
		})

	}

	componentWillUnmount() {
		if (App.accountSelectorLab) {
			App.accountSelectorLab.unregister('lab_results_view')
		}
	}
}

export default Lab_resultsView
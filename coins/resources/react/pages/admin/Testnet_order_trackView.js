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

import Order_track from '../../model/admin/Order_track'
import ExchangeChartLine from '../../components/admin/ExchangeChartLine'
import ExchangePosition from '../../components/admin/ExchangePosition'
import TrackAlertModal from '../../components/admin/TrackAlertModal'
import Account_summaryView from './Account_summaryView'
import FearChartLine from '../../components/admin/FearChartLine'
import Volume24hView from './Volume24hView'
import FluctuationView from './FluctuationView'
import OrderTracking from '../../components/admin/OrderTracking'
import MakeOrderModal from '../../components/admin/MakeOrderModal'
import Finance from '../../components/admin/Finance'
import VolatilityView from './VolatilityView'
import Input from '../../components/input/Input'
import Volatility_historyView from './Volatility_historyView'
import CoinMarketTable from '../../components/admin/CoinMarketTable'
import Trades from '../../model/admin/Trades'
import Coinmarket from '../../model/admin/Coinmarket'
import Finance24hView from './Finance24hView'
import SystemInfo from '../../components/admin/SystemInfo'
import WMAChartLine from '../../components/admin/WMAChartLine'

import Watchlist from '../../model/admin/Watchlist'
import WMA24hView from './WMA24hView'
import Chart_BTC from '../../components/admin/Chart_BTC'
import Chart_CandleVolume from '../../components/admin/Chart_CandleVolume'
import CandleVolumeTable from '../../components/admin/CandleVolumeTable'
import CandleVolumeTableW from '../../components/admin/CandleVolumeTableW'
import Chart_Liquidation from '../../components/admin/Chart_Liquidation'
import TableMaxPain from '../../components/admin/TableMaxPain'
import Chart_BTC_Votility from '../../components/admin/Chart_BTC_Votility'
import Chart_WMA_Gauge from '../../components/admin/Chart_WMA_Gauge'
import Chart_WMA_Gauge_Copy from '../../components/admin/Chart_WMA_Gauge_Copy'
import Candle_24h from '../../model/admin/Candle_24h'
class Testnet_order_trackView extends Component {

	constructor(props) {
		super(props);

		this.order_track_struct = {};
		this.order_track_struct[STRUCT_FILTERS] = {}
		this.order_track_struct[STRUCT_COLUMNS] = {

			[ORDER_TRACK_SYMBOL]: {
				[COL_NAME]: lang(ORDER_TRACK_SYMBOL),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {
					var rankData = (data == '1000SHIBUSDT' ? 'SHIBUSDT' : data);
					var style = { cursor: 'pointer', fontWeight: 'bold', color: 'darkgray' };
					if (isset(this.userTradeIndex[data])) style.color = 'black';
					return <div style={style} onClick={() => {
						this.exchangeChart.selectSymbol(data);
						this.exchangeChart.setTimeRange('', '');
						this.exchangeChart.getData(true);
						this.exchangeChart.startUpdate();

					}}>
						<img style={{ width: '20px', height: '20px', marginRight: '10px' }} src={this.watchlistIcon[data]}></img>
						<span>{data}
							<span style={{ color: 'blue', fontWeight: 'normal' }}> [{get(this.coinMarketData[rankData], '')}]</span>
						</span>
					</div>
				}

			},

			'volumn24h': {
				[COL_NAME]: 'Volumn 24h',
				[COL_SORT]: true,

				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					var symbol = data[rowId][ORDER_TRACK_SYMBOL];
					let out = formatNumber(Math.round(this.volumn24h[symbol]))
					return out
	
				}

			},


			// [ORDER_TRACK_CHANGE]: {
			// 	[COL_NAME]: lang(ORDER_TRACK_CHANGE),
			// 	[COL_SORT]: true,
			// 	[COL_DECORATOR_IN]: data => data + '%'

			// },

			[ORDER_TRACK_1D_DOWN]: {
				[COL_NAME]: '1D LONG',
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: data => {
					if (data === null) return '';

					if (App.accountSelector.selected() == 6) {
						if (data <= -8) return <b style={{ color: 'violet' }}>{data + '%'}</b>
						if (data <= -6) return <b style={{ color: 'red' }}>{data + '%'}</b>
						if (data <= -4) return <b style={{ color: 'orangered' }}>{data + '%'}</b>
						if (data <= -2) return <b style={{ color: 'orange' }}>{data + '%'}</b>
						if (data <= 0) return <b style={{ color: 'limegreen' }}>{data + '%'}</b>
						return <b>{data + '%'}</b>
					}

					if (data <= -5) return <b style={{ color: 'red' }}>{data + '%'}</b>
					if (data <= -4) return <b style={{ color: 'limegreen' }}>{data + '%'}</b>
					return <b>{data + '%'}</b>


				}


			},
			[ORDER_TRACK_1D_UP]: {
				[COL_NAME]: '1D SHORT',
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: data => {
					if (data === null) return '';

					if (App.accountSelector.selected() == 6) {
						if (data >= 8) return <b style={{ color: 'violet' }}>{data + '%'}</b>
						if (data >= 6) return <b style={{ color: 'red' }}>{data + '%'}</b>
						if (data >= 4) return <b style={{ color: 'orangered' }}>{data + '%'}</b>
						if (data >= 2) return <b style={{ color: 'orange' }}>{data + '%'}</b>
						if (data >= 0) return <b style={{ color: 'limegreen' }}>{data + '%'}</b>
						return <b>{data + '%'}</b>
					}

					if (data >= 5) return <b style={{ color: 'red' }}>{data + '%'}</b>
					if (data >= 4) return <b style={{ color: 'limegreen' }}>{data + '%'}</b>
					return <b>{data + '%'}</b>


				}

			},

			[ORDER_TRACK_DOWN]: {
				[COL_NAME]: '4H LONG',
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: data => {
					if (data === null) return '';

					if (App.accountSelector.selected() == 6) {
						if (data <= -5) return <b style={{ color: 'violet' }}>{data + '%'}</b>
						if (data <= -4) return <b style={{ color: 'red' }}>{data + '%'}</b>
						if (data <= -3) return <b style={{ color: 'orangered' }}>{data + '%'}</b>
						if (data <= -2) return <b style={{ color: 'orange' }}>{data + '%'}</b>
						if (data <= 0) return <b style={{ color: 'limegreen' }}>{data + '%'}</b>
						return <b>{data + '%'}</b>
					}

					if (data <= -2) return <b style={{ color: 'red' }}>{data + '%'}</b>
					if (data <= -1) return <b style={{ color: 'limegreen' }}>{data + '%'}</b>
					return <b>{data + '%'}</b>


				}


			},
			[ORDER_TRACK_UP]: {
				[COL_NAME]: '4H SHORT',
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: data => {
					if (data === null) return '';

					if (App.accountSelector.selected() == 6) {
						if (data >= 5) return <b style={{ color: 'violet' }}>{data + '%'}</b>
						if (data >= 4) return <b style={{ color: 'red' }}>{data + '%'}</b>
						if (data >= 3) return <b style={{ color: 'orangered' }}>{data + '%'}</b>
						if (data >= 2) return <b style={{ color: 'orange' }}>{data + '%'}</b>
						if (data >= 0) return <b style={{ color: 'limegreen' }}>{data + '%'}</b>
						return <b>{data + '%'}</b>
					}

					if (data >= 5) return <b style={{ color: 'red' }}>{data + '%'}</b>
					if (data >= 4) return <b style={{ color: 'limegreen' }}>{data + '%'}</b>
					return <b>{data + '%'}</b>


				}

			},

			[ORDER_TRACK_RSI_EMA9]: {
				[COL_NAME]: lang(ORDER_TRACK_RSI_EMA9),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: data => {
					if (data === null) return '';
					if (!data) return '';
					if (data >= 69) return <b style={{ color: 'red' }}>{data.toFixed(2)}</b>
					if (data <= 31) return <b style={{ color: 'red' }}>{data.toFixed(2)}</b>
					return <b>{data.toFixed(2)}</b>
				}
			},

			[ORDER_TRACK_RSI4H_0]: {
				[COL_NAME]: lang(ORDER_TRACK_RSI4H_0),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: data => {
					if (data === null) return '';
					if (!data) return '';
					if (data > 65) return <b style={{ color: 'red' }}>{data.toFixed(2)}</b>
					if (data <= 31) return <b style={{ color: 'red' }}>{data.toFixed(2)}</b>
					return <b>{data.toFixed(2)}</b>
				}

			},

			[ORDER_TRACK_RSI4H_1]: {
				[COL_NAME]: lang(ORDER_TRACK_RSI4H_1),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: data => {
					if (data === null) return '';
					if (!data) return '';
					if (data > 65) return <b style={{ color: 'red' }}>{data.toFixed(2)}</b>
					if (data <= 31) return <b style={{ color: 'red' }}>{data.toFixed(2)}</b>
					return <b>{data.toFixed(2)}</b>
				}
			},

			[ORDER_TRACK_RSI1H_0]: {
				[COL_NAME]: lang(ORDER_TRACK_RSI1H_0),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: data => {
					if (data === null) return '';
					if (!data) return '';
					if (data > 65) return <b style={{ color: 'red' }}>{data.toFixed(2)}</b>
					if (data <= 31) return <b style={{ color: 'red' }}>{data.toFixed(2)}</b>
					return <b>{data.toFixed(2)}</b>
				}

			},

			[ORDER_TRACK_RSI1H_1]: {
				[COL_NAME]: lang(ORDER_TRACK_RSI1H_1),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: data => {
					if (data === null) return '';
					if (!data) return '';
					if (data > 65) return <b style={{ color: 'red' }}>{data.toFixed(2)}</b>
					if (data <= 31) return <b style={{ color: 'red' }}>{data.toFixed(2)}</b>
					return <b>{data.toFixed(2)}</b>
				}
			},

			[ORDER_TRACK_1D_RSI_WMA]: {
				[COL_NAME]: lang(ORDER_TRACK_1D_RSI_WMA),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: data => {
					if (data === null) return '';
					if (!data) return '';
					if (data >= 69) return <b style={{ color: 'red' }}>{data.toFixed(2)}</b>
					if (data <= 31) return <b style={{ color: 'red' }}>{data.toFixed(2)}</b>
					return <b>{data.toFixed(2)}</b>
				}
			},

			[ORDER_TRACK_1W_RSI_WMA]: {
				[COL_NAME]: lang(ORDER_TRACK_1W_RSI_WMA),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: data => {
					if (data === null) return '';
					if (!data) return '';
					if (data >= 69) return <b style={{ color: 'red' }}>{data.toFixed(2)}</b>
					if (data <= 31) return <b style={{ color: 'red' }}>{data.toFixed(2)}</b>
					return <b>{data.toFixed(2)}</b>
				}
			},



			[ORDER_TRACK_1H_DOWN]: {
				[COL_NAME]: '1H LONG',
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: data => {
					if (data === null) return '';

					if (data <= -5) return <b style={{ color: 'violet' }}>{data + '%'}</b>
					if (data <= -4) return <b style={{ color: 'red' }}>{data + '%'}</b>
					if (data <= -3) return <b style={{ color: 'orangered' }}>{data + '%'}</b>
					if (data <= -2) return <b style={{ color: 'orange' }}>{data + '%'}</b>
					if (data <= 0) return <b style={{ color: 'limegreen' }}>{data + '%'}</b>

					return <b>{data + '%'}</b>
				}


			},

			[ORDER_TRACK_1H_UP]: {
				[COL_NAME]: '1H SHORT',
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: data => {
					if (data === null) return '';
					if (data >= 5) return <b style={{ color: 'violet' }}>{data + '%'}</b>
					if (data >= 4) return <b style={{ color: 'red' }}>{data + '%'}</b>
					if (data >= 3) return <b style={{ color: 'orangered' }}>{data + '%'}</b>
					if (data >= 2) return <b style={{ color: 'orange' }}>{data + '%'}</b>
					if (data >= 0) return <b style={{ color: 'limegreen' }}>{data + '%'}</b>
					return <b>{data + '%'}</b>
				}

			},
			[ORDER_TRACK_15M_DOWN]: {
				[COL_NAME]: '15M LONG',
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: data => {
					if (data === null) return '';

					if (data <= -5) return <b style={{ color: 'violet' }}>{data + '%'}</b>
					if (data <= -4) return <b style={{ color: 'red' }}>{data + '%'}</b>
					if (data <= -3) return <b style={{ color: 'orangered' }}>{data + '%'}</b>
					if (data <= -2) return <b style={{ color: 'orange' }}>{data + '%'}</b>
					if (data <= 0) return <b style={{ color: 'limegreen' }}>{data + '%'}</b>

					return <b>{data + '%'}</b>
				}


			},

			[ORDER_TRACK_15M_UP]: {
				[COL_NAME]: '15M SHORT',
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: data => {
					if (data === null) return '';
					if (data >= 5) return <b style={{ color: 'violet' }}>{data + '%'}</b>
					if (data >= 4) return <b style={{ color: 'red' }}>{data + '%'}</b>
					if (data >= 3) return <b style={{ color: 'orangered' }}>{data + '%'}</b>
					if (data >= 2) return <b style={{ color: 'orange' }}>{data + '%'}</b>
					if (data >= 0) return <b style={{ color: 'limegreen' }}>{data + '%'}</b>
					return <b>{data + '%'}</b>
				}

			},
			[ORDER_TRACK_3M_DOWN]: {
				[COL_NAME]: '3M LONG',
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: data => {
					if (data === null) return '';

					if (data <= -5) return <b style={{ color: 'violet' }}>{data + '%'}</b>
					if (data <= -4) return <b style={{ color: 'red' }}>{data + '%'}</b>
					if (data <= -3) return <b style={{ color: 'orangered' }}>{data + '%'}</b>
					if (data <= -2) return <b style={{ color: 'orange' }}>{data + '%'}</b>
					if (data <= 0) return <b style={{ color: 'limegreen' }}>{data + '%'}</b>

					return <b>{data + '%'}</b>
				}


			},

			[ORDER_TRACK_3M_UP]: {
				[COL_NAME]: '3M SHORT',
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: data => {
					if (data === null) return '';
					if (data >= 5) return <b style={{ color: 'violet' }}>{data + '%'}</b>
					if (data >= 4) return <b style={{ color: 'red' }}>{data + '%'}</b>
					if (data >= 3) return <b style={{ color: 'orangered' }}>{data + '%'}</b>
					if (data >= 2) return <b style={{ color: 'orange' }}>{data + '%'}</b>
					if (data >= 0) return <b style={{ color: 'limegreen' }}>{data + '%'}</b>
					return <b>{data + '%'}</b>
				}

			},

			[ORDER_TRACK_PRICE]: {
				[COL_NAME]: lang(ORDER_TRACK_PRICE),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },

			},
			[ORDER_TRACK_CLOSE]: {
				[COL_NAME]: lang(ORDER_TRACK_CLOSE),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },

			},
			[ORDER_TRACK_LOW]: {
				[COL_NAME]: lang(ORDER_TRACK_LOW),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },

			},
			[ORDER_TRACK_HIGH]: {
				[COL_NAME]: lang(ORDER_TRACK_HIGH),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },

			},
			action: {
				[COL_NAME]: lang('Action'),
				[COL_SORT]: false,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {

					var rowData = data[rowId];
					var data = rowData[colId];
					return <div className='box_flex' style={{ justifyContent: 'center' }}>
						<div className='button btn btn-sm btn-primary' style={{ fontSize: 10, width: 100 }} onClick={() => this.makePosition(ACTION_TYPE_LONG, rowData)}>Long {rowData[ORDER_TRACK_SYMBOL]}</div>
						<div className='button btn btn-sm btn-danger' style={{ fontSize: 10, width: 100 }} onClick={() => this.makePosition(ACTION_TYPE_SHORT, rowData)}>Short {rowData[ORDER_TRACK_SYMBOL]}</div>
					</div>
				}
			}




		}
		this.order_track_struct[STRUCT_FILTERS] = {

			[ORDER_TRACK_SYMBOL]: {
				[FILTER_NAME]: lang(ORDER_TRACK_SYMBOL),
				[FILTER_TYPE]: 'text',
			},
			// [ORDER_TRACK_PRICE]: {
			// 	[FILTER_NAME]: lang(ORDER_TRACK_PRICE),
			// 	[FILTER_TYPE]: 'number',
			// },
			// [ORDER_TRACK_LOW]: {
			// 	[FILTER_NAME]: lang(ORDER_TRACK_LOW),
			// 	[FILTER_TYPE]: 'number',
			// },
			// [ORDER_TRACK_HIGH]: {
			// 	[FILTER_NAME]: lang(ORDER_TRACK_HIGH),
			// 	[FILTER_TYPE]: 'number',
			// },
			// [ORDER_TRACK_UP]: {
			// 	[FILTER_NAME]: lang(ORDER_TRACK_UP),
			// 	[FILTER_TYPE]: 'number',
			// },
			// [ORDER_TRACK_DOWN]: {
			// 	[FILTER_NAME]: lang(ORDER_TRACK_DOWN),
			// 	[FILTER_TYPE]: 'number',
			// },


		}

		this.order_track_struct[STRUCT_EDIT] = {

			[ORDER_TRACK_SYMBOL]: {
				[EDIT_NAME]: lang(ORDER_TRACK_SYMBOL),
				[EDIT_TYPE]: 'text',

			},
			[ORDER_TRACK_PRICE]: {
				[EDIT_NAME]: lang(ORDER_TRACK_PRICE),
				[EDIT_TYPE]: 'number',

			},
			[ORDER_TRACK_LOW]: {
				[EDIT_NAME]: lang(ORDER_TRACK_LOW),
				[EDIT_TYPE]: 'number',

			},
			[ORDER_TRACK_HIGH]: {
				[EDIT_NAME]: lang(ORDER_TRACK_HIGH),
				[EDIT_TYPE]: 'number',

			},
			[ORDER_TRACK_UP]: {
				[EDIT_NAME]: lang(ORDER_TRACK_UP),
				[EDIT_TYPE]: 'number',

			},
			[ORDER_TRACK_DOWN]: {
				[EDIT_NAME]: lang(ORDER_TRACK_DOWN),
				[EDIT_TYPE]: 'number',

			},


		}

		this.order_track_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<div className='button btn btn-primary' style={{ fontSize: 10 }} onClick={() => this.makePosition(ACTION_TYPE_LONG, rowData[ORDER_TRACK_SYMBOL])}>Long</div>
					<div className='button btn btn-danger' style={{ fontSize: 10 }} onClick={() => this.makePosition(ACTION_TYPE_SHORT, rowData[ORDER_TRACK_SYMBOL])}>Short</div>
				</div>
			},
			// [ROW_STYLE]: (rowID, tableData)=>{
			// 	var rowData = tableData[rowID];
			// 	var symbol = rowData[ORDER_TRACK_SYMBOL];
			// 	if(isset(this.userTradeIndex[symbol])) return {background:'red'};
			// 	return {};
			// }
		};
		this.order_track_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: ORDER_TRACK_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {
				[ORDER_TRACK_1H_DOWN]: true,
				[ORDER_TRACK_1H_UP]: true,
				[ORDER_TRACK_PRICE]: true,
				[ORDER_TRACK_CLOSE]: true,
				[ORDER_TRACK_LOW]: true,
				[ORDER_TRACK_HIGH]: true,
				[ORDER_TRACK_15M_DOWN]: true,
				[ORDER_TRACK_15M_UP]: true,
				[ORDER_TRACK_3M_DOWN]: true,
				[ORDER_TRACK_3M_UP]: true,
				[ORDER_TRACK_PRICE]: true,
				[ORDER_TRACK_1D_RSI_WMA]: true,
				[ORDER_TRACK_RSI1H_1]: true,
				[ORDER_TRACK_RSI1H_0]: true,
				[ORDER_TRACK_RSI4H_0]: true,
				[ORDER_TRACK_RSI4H_1]: true,
				[ORDER_TRACK_RSI_EMA9]: true,
				action: true,
			},
			[DATA_PERMIT_COL]: this.permissionOrder_trackView(),
			[DATA_KEY]: [ORDER_TRACK_ID],
			[DATA_SORT]: { [ORDER_TRACK_DOWN]: 'asc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: false,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,
			[PAGE_QUANTITY]: 10,

			model: new Order_track()

		};


		this.userTradeIndex = {};


		this.coinMarketModel = new Coinmarket();
		this.coinMarketData = {};
		this.watchlistIcon = {};
		this.volumn24h = {}


	}

	permissionOrder_trackView() {
		return Object.assign(
			...Object.keys(this.order_track_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.order_track_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	render() {
		return (
			<div>
				{/* bbb */}
				{/* {SERVER_LOCATION != 'google' && <Chart_WMA_Gauge_Copy ref={c => this.Chart_WMA_Gauge_Copy = c} ></Chart_WMA_Gauge_Copy>} */}
				{/* <WMAChartLine  setFear={(data) => this.Chart_WMA_Gauge_Copy.setFear(data)}></WMAChartLine> */}
		
				{/* <OrderTracking ref={c => this.OrderTracking = c} ></OrderTracking> */}
				{/* {SERVER_LOCATION != 'google' && <Finance></Finance>} */}
				{/* <SystemInfo></SystemInfo> */}

				{/* bbb */}
				{
				
				// SERVER_LOCATION != 'google' && <><WMA24hView></WMA24hView> 

				// {/* <Finance24hView></Finance24hView> */}
				// </>
				}

				{
					App.user[AUTHEN_GROUP] != 4 && 
						<Table ref={c => this.table = c} table={this.order_track_struct} autoload={false} 
						// onFilterSuccess={(data) => {
						// 	this.OrderTracking.setDataCoin(data)
						// }}
						>
							<FuncBar
								left={<><FuncHideCol /><div className='button btn btn-sm btn-warning' onClick={() => {
									this.trackAlertModal.modal()
								}}><i className="fa fa-bell-o"></i>&nbsp;Alert</div></>}
								name={'Order tracking'}
								right={<><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
							<MainTable className='table table-bordered table-resizable'></MainTable>
							<Pagination></Pagination>
		
						</Table>
				}


				



				{/* <ExchangePosition onSelectSym={sym => {
					this.exchangeChart.selectSymbol(sym, false);
					this.exchangeChart.setTimeRange('', '');
					this.exchangeChart.getData(true);
					this.exchangeChart.startUpdate();
				}} onSelectTime={(sym, start, stop) => {
					this.exchangeChart.selectSymbol(sym);
					this.exchangeChart.setTimeRange(start, stop);
					this.exchangeChart.getData(true);
				}}></ExchangePosition> */}

				{/* <div style={{ marginBottom: 15, marginTop: 15 }}>
					<Account_summaryView onClickAccount={(id) => {
						if (App.accountSelector) App.accountSelector.selectAccount(id);
					}}></Account_summaryView>

				</div> */}



				{SERVER_LOCATION != 'google' && <>
					{/* bbb */}
					{/* <Chart_BTC_Votility></Chart_BTC_Votility> */}


					{/* <Chart_BTC></Chart_BTC> */}
				
					<Volume24hView ref={c => this.volumeView = c}></Volume24hView>
					<CoinMarketTable ref={c => this.CoinMarketTable = c} ></CoinMarketTable>
					{/* <WMA24hView></WMA24hView> */}

					{/* <Finance24hView></Finance24hView> */}

				
				</>}
			
				{/* {
					App.user[AUTHEN_GROUP] == 4 ? <></>  : App.isMobile() ? <></> : <>
					<ExchangeChartLine ref={c => this.exchangeChart = c}></ExchangeChartLine>
					
				</>
				} */}
				{/* {App.isMobile()
					? <></>
					: <>
						<ExchangeChartLine ref={c => this.exchangeChart = c}></ExchangeChartLine>
						
					</>
				} */}
				{/* <FearChartLine OrderTracking={(data) => this.OrderTracking.setData(data)}></FearChartLine> */}
				
				
				{/* {SERVER_LOCATION != 'google' && <Chart_CandleVolume></Chart_CandleVolume>} */}
				{/* {SERVER_LOCATION != 'google' && <CandleVolumeTableW></CandleVolumeTableW>} */}
				{/* {SERVER_LOCATION != 'google' && <CandleVolumeTable></CandleVolumeTable>} */}

				{/* bbb */}
				{/* {SERVER_LOCATION != 'google' && <TableMaxPain></TableMaxPain>}
				{SERVER_LOCATION != 'google' && <Chart_Liquidation></Chart_Liquidation>} */}

				{/* {SERVER_LOCATION == 'google' ? <></> : App.user[AUTHEN_GROUP] == 4 ? <></> :
					<>
						<div className='box_flex box_border box_padding' style={{ justifyContent: 'space-around', position: 'relative', flexWrap: 'wrap' }}>
							<div style={{
								position: 'absolute',
								top: -10,
								background: 'white',
								padding: '0px 5px',
								fontWeight: 'bold',
								color: 'rgb(0, 123, 255)',

							}}>FILTER BAR</div>
							<div style={{ padding: 5 }}>
								<div style={{ textAlign: 'center', fontWeight: 'bold', marginBottom: 5 }}>Symbol</div>
								<div>
									<Input className='input' struct={{
										[INPUT_TYPE]: 'text',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {
											var value = input.getValue();
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_SYMBOL] = { data: { contain: value } }
											this.volatilityView.table.filter();
											this.volumeView.table[STRUCT_TABLE][DATA_FILTERS][CANDLE_24H_SYMBOL] = { data: { contain: value } }
											this.volumeView.table.filter();

											this.CoinMarketTable.table[STRUCT_TABLE][DATA_FILTERS][COINMARKET_SYMBOL] = { data: { contain: value } }
											this.CoinMarketTable.table.filter();


											this.Volatility_historyView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_SYMBOL] = { data: { contain: value } }
											this.Volatility_historyView.table.filter();
										}
									}}></Input>
								</div>
							</div>

							<div style={{ padding: 5 }}>
								<div style={{ textAlign: 'center', fontWeight: 'bold', marginBottom: 5 }}>3D H-L Rank</div>
								<div className='box_flex'>
									<Input className='input' style={{ width: 80 }} placeholder="From" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {

											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_LOW_AVG3D_RANK])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_LOW_AVG3D_RANK] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_LOW_AVG3D_RANK]['data']['>='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
									<Input className='input' style={{ width: 80 }} placeholder="To" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {
											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_LOW_AVG3D_RANK])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_LOW_AVG3D_RANK] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_LOW_AVG3D_RANK]['data']['<='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
								</div>
							</div>

							<div style={{ padding: 5 }}>
								<div style={{ textAlign: 'center', fontWeight: 'bold', marginBottom: 5 }}>3D H-H Rank</div>
								<div className='box_flex'>
									<Input className='input' style={{ width: 80 }} placeholder="From" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {

											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_HIGH_AVG3D_RANK])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_HIGH_AVG3D_RANK] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_HIGH_AVG3D_RANK]['data']['>='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
									<Input className='input' style={{ width: 80 }} placeholder="To" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {
											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_HIGH_AVG3D_RANK])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_HIGH_AVG3D_RANK] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_HIGH_AVG3D_RANK]['data']['<='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
								</div>
							</div>

							<div style={{ padding: 5 }}>
								<div style={{ textAlign: 'center', fontWeight: 'bold', marginBottom: 5 }}>7D H-L Rank</div>
								<div className='box_flex'>
									<Input className='input' style={{ width: 80 }} placeholder="From" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {
											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_LOW_AVG7D_RANK])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_LOW_AVG7D_RANK] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_LOW_AVG7D_RANK]['data']['>='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
									<Input className='input' style={{ width: 80 }} placeholder="To" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {
											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_LOW_AVG7D_RANK])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_LOW_AVG7D_RANK] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_LOW_AVG7D_RANK]['data']['<='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
								</div>
							</div>

							<div style={{ padding: 5 }}>
								<div style={{ textAlign: 'center', fontWeight: 'bold', marginBottom: 5 }}>7D H-H Rank</div>
								<div className='box_flex'>
									<Input className='input' style={{ width: 80 }} placeholder="From" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {
											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_HIGH_AVG7D_RANK])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_HIGH_AVG7D_RANK] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_HIGH_AVG7D_RANK]['data']['>='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
									<Input className='input' style={{ width: 80 }} placeholder="To" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {
											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_HIGH_AVG7D_RANK])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_HIGH_AVG7D_RANK] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_HIGH_AVG7D_RANK]['data']['<='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
								</div>
							</div>


							<div style={{ padding: 5 }}>
								<div style={{ textAlign: 'center', fontWeight: 'bold', marginBottom: 5 }}>3D H-L Value</div>
								<div className='box_flex'>
									<Input className='input' style={{ width: 80 }} placeholder="From" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {
											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_LOW_AVG3D_VALUE])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_LOW_AVG3D_VALUE] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_LOW_AVG3D_VALUE]['data']['>='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
									<Input className='input' style={{ width: 80 }} placeholder="To" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {
											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_LOW_AVG3D_VALUE])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_LOW_AVG3D_VALUE] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_LOW_AVG3D_VALUE]['data']['<='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
								</div>
							</div>

							<div style={{ padding: 5 }}>
								<div style={{ textAlign: 'center', fontWeight: 'bold', marginBottom: 5 }}>3D H-H Value</div>
								<div className='box_flex'>
									<Input className='input' style={{ width: 80 }} placeholder="From" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {
											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_HIGH_AVG3D_VALUE])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_HIGH_AVG3D_VALUE] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_HIGH_AVG3D_VALUE]['data']['>='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
									<Input className='input' style={{ width: 80 }} placeholder="To" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {
											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_HIGH_AVG3D_VALUE])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_HIGH_AVG3D_VALUE] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_HIGH_AVG3D_VALUE]['data']['<='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
								</div>
							</div>

							<div style={{ padding: 5 }}>
								<div style={{ textAlign: 'center', fontWeight: 'bold', marginBottom: 5 }}>7D H-L Value</div>
								<div className='box_flex'>
									<Input className='input' style={{ width: 80 }} placeholder="From" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {
											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_LOW_AVG7D_VALUE])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_LOW_AVG7D_VALUE] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_LOW_AVG7D_VALUE]['data']['>='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
									<Input className='input' style={{ width: 80 }} placeholder="To" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {
											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_LOW_AVG7D_VALUE])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_LOW_AVG7D_VALUE] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_LOW_AVG7D_VALUE]['data']['<='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
								</div>
							</div>

							<div style={{ padding: 5 }}>
								<div style={{ textAlign: 'center', fontWeight: 'bold', marginBottom: 5 }}>7D H-H Value</div>
								<div className='box_flex'>
									<Input className='input' style={{ width: 80 }} placeholder="From" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {
											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_HIGH_AVG7D_VALUE])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_HIGH_AVG7D_VALUE] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_HIGH_AVG7D_VALUE]['data']['>='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
									<Input className='input' style={{ width: 80 }} placeholder="To" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {
											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_HIGH_AVG7D_VALUE])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_HIGH_AVG7D_VALUE] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_1D_HIGH_HIGH_AVG7D_VALUE]['data']['<='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
								</div>
							</div>

						</div>

						<div className='box_flex box_border box_padding' style={{ justifyContent: 'space-around', position: 'relative', flexWrap: 'wrap', color: '#007bff' }}>
							<div style={{
								position: 'absolute',
								top: -10,
								background: 'white',
								padding: '0px 5px',
								fontWeight: 'bold',
								color: 'rgb(0, 123, 255)',

							}}>FILTER BAR 4H</div>


							<div style={{ padding: 5 }}>
								<div style={{ textAlign: 'center', fontWeight: 'bold', marginBottom: 5 }}>3D H-L Rank</div>
								<div className='box_flex'>
									<Input className='input' style={{ width: 80 }} placeholder="From" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {
											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_LOW_AVG3D_RANK])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_LOW_AVG3D_RANK] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_LOW_AVG3D_RANK]['data']['>='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
									<Input className='input' style={{ width: 80 }} placeholder="To" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {
											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_LOW_AVG3D_RANK])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_LOW_AVG3D_RANK] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_LOW_AVG3D_RANK]['data']['<='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
								</div>
							</div>

							<div style={{ padding: 5 }}>
								<div style={{ textAlign: 'center', fontWeight: 'bold', marginBottom: 5 }}>3D H-H Rank</div>
								<div className='box_flex'>
									<Input className='input' style={{ width: 80 }} placeholder="From" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {

											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_HIGH_AVG3D_RANK])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_HIGH_AVG3D_RANK] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_HIGH_AVG3D_RANK]['data']['>='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
									<Input className='input' style={{ width: 80 }} placeholder="To" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {
											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_HIGH_AVG3D_RANK])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_HIGH_AVG3D_RANK] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_HIGH_AVG3D_RANK]['data']['<='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
								</div>
							</div>

							<div style={{ padding: 5 }}>
								<div style={{ textAlign: 'center', fontWeight: 'bold', marginBottom: 5 }}>7D H-L Rank</div>
								<div className='box_flex'>
									<Input className='input' style={{ width: 80 }} placeholder="From" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {

											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_LOW_AVG7D_RANK])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_LOW_AVG7D_RANK] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_LOW_AVG7D_RANK]['data']['>='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
									<Input className='input' style={{ width: 80 }} placeholder="To" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {
											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_LOW_AVG7D_RANK])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_LOW_AVG7D_RANK] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_LOW_AVG7D_RANK]['data']['<='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
								</div>
							</div>

							<div style={{ padding: 5 }}>
								<div style={{ textAlign: 'center', fontWeight: 'bold', marginBottom: 5 }}>7D H-H Rank</div>
								<div className='box_flex'>
									<Input className='input' style={{ width: 80 }} placeholder="From" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {

											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_HIGH_AVG7D_RANK])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_HIGH_AVG7D_RANK] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_HIGH_AVG7D_RANK]['data']['>='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
									<Input className='input' style={{ width: 80 }} placeholder="To" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {
											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_HIGH_AVG7D_RANK])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_HIGH_AVG7D_RANK] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_HIGH_AVG7D_RANK]['data']['<='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
								</div>
							</div>


							<div style={{ padding: 5 }}>
								<div style={{ textAlign: 'center', fontWeight: 'bold', marginBottom: 5 }}>3D H-L Value</div>
								<div className='box_flex'>
									<Input className='input' style={{ width: 80 }} placeholder="From" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {

											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_LOW_AVG3D_VALUE])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_LOW_AVG3D_VALUE] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_LOW_AVG3D_VALUE]['data']['>='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
									<Input className='input' style={{ width: 80 }} placeholder="To" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {
											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_LOW_AVG3D_VALUE])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_LOW_AVG3D_VALUE] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_LOW_AVG3D_VALUE]['data']['<='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
								</div>
							</div>

							<div style={{ padding: 5 }}>
								<div style={{ textAlign: 'center', fontWeight: 'bold', marginBottom: 5 }}>3D H-H Value</div>
								<div className='box_flex'>
									<Input className='input' style={{ width: 80 }} placeholder="From" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {

											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_HIGH_AVG3D_VALUE])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_HIGH_AVG3D_VALUE] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_HIGH_AVG3D_VALUE]['data']['>='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
									<Input className='input' style={{ width: 80 }} placeholder="To" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {
											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_HIGH_AVG3D_VALUE])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_HIGH_AVG3D_VALUE] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_HIGH_AVG3D_VALUE]['data']['<='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
								</div>
							</div>

							<div style={{ padding: 5 }}>
								<div style={{ textAlign: 'center', fontWeight: 'bold', marginBottom: 5 }}>7D H-L Value</div>
								<div className='box_flex'>
									<Input className='input' style={{ width: 80 }} placeholder="From" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {

											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_LOW_AVG7D_VALUE])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_LOW_AVG7D_VALUE] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_LOW_AVG7D_VALUE]['data']['>='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
									<Input className='input' style={{ width: 80 }} placeholder="To" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {
											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_LOW_AVG7D_VALUE])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_LOW_AVG7D_VALUE] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_LOW_AVG7D_VALUE]['data']['<='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
								</div>
							</div>

							<div style={{ padding: 5 }}>
								<div style={{ textAlign: 'center', fontWeight: 'bold', marginBottom: 5 }}>7D H-H Value</div>
								<div className='box_flex'>
									<Input className='input' style={{ width: 80 }} placeholder="From" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {

											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_HIGH_AVG7D_VALUE])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_HIGH_AVG7D_VALUE] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_HIGH_AVG7D_VALUE]['data']['>='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
									<Input className='input' style={{ width: 80 }} placeholder="To" struct={{
										[INPUT_TYPE]: 'number',
										[INPUT_ONCHANGE_BLUR]: (obj, input) => {
											var value = input.getValue();
											if (!isset(this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_HIGH_AVG7D_VALUE])) {
												this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_HIGH_AVG7D_VALUE] = { data: {} }
											}
											this.volatilityView.table[STRUCT_TABLE][DATA_FILTERS][VOLATILITY_4H_HIGH_HIGH_AVG7D_VALUE]['data']['<='] = value;
											this.volatilityView.table.filter();
										}
									}}></Input>
								</div>
							</div>

						</div>
					</>
				}

				{
					App.user[AUTHEN_GROUP] != 4 && <VolatilityView ref={c => this.volatilityView = c}></VolatilityView>
				} */}
		
				{/* {SERVER_LOCATION == 'google' ? <></> : App.user[AUTHEN_GROUP] == 4 ? <></> : <>

					<Volatility_historyView ref={c => this.Volatility_historyView = c}></Volatility_historyView>
					<br />
				</>} */}


				<TrackAlertModal ref={c => this.trackAlertModal = c}></TrackAlertModal>
				<MakeOrderModal ref={c => this.makeOrderModal = c}></MakeOrderModal>



			</div>
		);
	}


	async getUserData() {
		var tradeModel = new Trades();
		this.userTradeIndex = await tradeModel.getUserTrade(App.accountSelector.getSelectedAccount());
	}

	async getMarketCap() {
		if (SERVER_LOCATION != 'google')
			this.coinMarketData = await this.coinMarketModel.getRank();
	}

	getIcon() {
		var watchlist = new Watchlist();

		watchlist.getIcon().then(res => this.watchlistIcon = res);

	}



	componentDidMount() {
		// this.OrderTracking.setDataCoin();
		this.getIcon();
		this.getVolumn24h()
		this.interval = setInterval(() => {
			this.table.filter(false);
			// this.OrderTracking.setDataCoin();
		}, 3000);

		this.getUserData().then(() => {
			return this.getMarketCap()
		}).then(res => {
			this.table.filter();
		})
	}

	async getVolumn24h(){
		var model = new Candle_24h();
		var dateData = await model.read({ [CANDLE_24H_DATE]: moment.utc().startOf('day').format('x') });
		if (dateData['result']) {
			dateData = dateData['data'];
			dateData.map(item => {
				this.volumn24h[item[CANDLE_24H_SYMBOL]] = item[CANDLE_24H_VOLUME_USDT]
			})
		}

		
	}

	componentWillUnmount() {
		if (this.interval) clearInterval(this.interval);
	}

	makePosition(type, data) {
		this.makeOrderModal.loadData(data, type);
		this.makeOrderModal.modal();
	}

	// async makePosition(type, symbol) {

	// 	var account = App.accountSelector.getSelectedAccount();
	// 	var accountName = account[ACCOUNT_NAME];
	// 	var accountId = account[ACCOUNT_ID];

	// 	var isConfirm = await makeQuestion('Do you want to make <b>' + (type == ACTION_TYPE_LONG ? 'LONG' : 'SHORT') + " " + symbol + "</b> on account <br/><b>[" + accountName + "]</b>?");
	// 	if (isConfirm) {
	// 		App.loading(true);
	// 		return axios.request({
	// 			url: '/admin/actions/makeOrder',
	// 			method: 'POST',
	// 			data: {
	// 				type,
	// 				symbol,
	// 				account: accountId
	// 			}
	// 		})

	// 			.then(response => {
	// 				App.loading(false);
	// 				response = response['data'];
	// 				if (!response['result']) {
	// 					error_handle(response)
	// 				}
	// 			})

	// 			.catch((error) => {
	// 				App.loading(false);
	// 				error_handle(error)
	// 				return false;
	// 			})
	// 	}
	// }
}

export default Testnet_order_trackView
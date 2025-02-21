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

import Volatility from '../../model/admin/Volatility'
import FluctuationsChart from '../../components/analytics/FluctuationsChart'
import Candle_24h from '../../model/admin/Candle_24h'
import TrackAvgAlertModal from '../../components/admin/TrackAvgAlertModal'
import Coinmarket from '../../model/admin/Coinmarket'
import Trades from '../../model/admin/Trades'
import Watchlist from '../../model/admin/Watchlist'
class VolatilityView extends Component {

	constructor(props) {
		super(props);

		this.volatility_struct = {};
		this.volatility_struct[STRUCT_FILTERS] = {}
		this.volatility_struct[STRUCT_COLUMNS] = {

			[VOLATILITY_SYMBOL]: {
				[COL_NAME]: lang(VOLATILITY_SYMBOL),
				[COL_SORT]: true,
				[COL_STYLE]: { fontWeight: 'bold' },
				[COL_DECORATOR_IN]: data => {
					var rankData = (data == '1000SHIBUSDT' ? 'SHIBUSDT' : data);
					var style = {cursor: 'pointer', fontWeight:'bold', color:'darkgray'};
					if(isset(this.userTradeIndex[data])) style.color = 'black';
					
					return <span style={style}>
						<img style={{ width: '20px', height: '20px', marginRight: '10px' }} src={this.watchlistIcon[data]}></img>
						{data}
						<span style={{ color: 'red', fontWeight: 'normal' }}> [{get(this.volumeData[data], '')}]</span>
						<span style={{ color: 'blue', fontWeight: 'normal' }}> [{get(this.coinMarketData[rankData], '')}]</span>
					</span>
				}

			},

			[VOLATILITY_4H_HIGH_LOW_AVG3D_VALUE]: {
				[COL_NAME]: lang('4H High Low'),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center', fontWeight: 'bold', color: '#007bff' },
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <span>{rowData[colid]}<span style={{ color: 'red', fontWeight: 'normal' }}> [{rowData[VOLATILITY_4H_HIGH_LOW_AVG3D_RANK]}]</span></span>
				}

			},
			[VOLATILITY_4H_HIGH_HIGH_AVG3D_VALUE]: {
				[COL_NAME]: lang('4H High High'),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center', fontWeight: 'bold', color: '#007bff' },
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <span>{rowData[colid]}<span style={{ color: 'red', fontWeight: 'normal' }}> [{rowData[VOLATILITY_4H_HIGH_HIGH_AVG3D_RANK]}]</span></span>
				}

			},
			[VOLATILITY_4H_LOW_LOW_AVG3D_VALUE]: {
				[COL_NAME]: lang('4H Low Low'),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center', fontWeight: 'bold', color: '#007bff' },
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <span>{rowData[colid]}<span style={{ color: 'red', fontWeight: 'normal' }}> [{rowData[VOLATILITY_4H_LOW_LOW_AVG3D_RANK]}]</span></span>
				}

			},
			[VOLATILITY_4H_CLOSE_LOW_AVG3D_VALUE]: {
				[COL_NAME]: lang('4H Close Low'),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center', fontWeight: 'bold', color: '#007bff' },
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <span>{rowData[colid]}<span style={{ color: 'red', fontWeight: 'normal' }}> [{rowData[VOLATILITY_4H_CLOSE_LOW_AVG3D_RANK]}]</span></span>
				}

			},

			[VOLATILITY_1D_HIGH_LOW_AVG3D_VALUE]: {
				[COL_NAME]: lang('1D High Low'),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center', fontWeight: 'bold' },
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <span>{rowData[colid]}<span style={{ color: 'red', fontWeight: 'normal' }}> [{rowData[VOLATILITY_1D_HIGH_LOW_AVG3D_RANK]}]</span></span>
				}

			},
			[VOLATILITY_1D_HIGH_HIGH_AVG3D_VALUE]: {
				[COL_NAME]: lang('1D High High'),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center', fontWeight: 'bold' },
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <span>{rowData[colid]}<span style={{ color: 'red', fontWeight: 'normal' }}> [{rowData[VOLATILITY_1D_HIGH_HIGH_AVG3D_RANK]}]</span></span>
				}

			},
			[VOLATILITY_1D_LOW_LOW_AVG3D_VALUE]: {
				[COL_NAME]: lang('1D Low Low'),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center', fontWeight: 'bold' },
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <span>{rowData[colid]}<span style={{ color: 'red', fontWeight: 'normal' }}> [{rowData[VOLATILITY_1D_LOW_LOW_AVG3D_RANK]}]</span></span>
				}

			},

			[VOLATILITY_1D_CLOSE_LOW_AVG3D_VALUE]: {
				[COL_NAME]: lang('1D Close Low'),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center', fontWeight: 'bold' },
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <span>{rowData[colid]}<span style={{ color: 'red', fontWeight: 'normal' }}> [{rowData[VOLATILITY_1D_CLOSE_LOW_AVG3D_RANK]}]</span></span>
				}

			},

			[VOLATILITY_4H_HIGH_LOW_AVG7D_VALUE]: {
				[COL_NAME]: lang('4H High Low'),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center', fontWeight: 'bold', color: '#007bff' },
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <span>{rowData[colid]}<span style={{ color: 'red', fontWeight: 'normal' }}> [{rowData[VOLATILITY_4H_HIGH_LOW_AVG7D_RANK]}]</span></span>
				}

			},
			[VOLATILITY_4H_HIGH_HIGH_AVG7D_VALUE]: {
				[COL_NAME]: lang('4H High High'),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center', fontWeight: 'bold', color: '#007bff' },
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <span>{rowData[colid]}<span style={{ color: 'red', fontWeight: 'normal' }}> [{rowData[VOLATILITY_4H_HIGH_HIGH_AVG7D_RANK]}]</span></span>
				}

			},
			[VOLATILITY_4H_LOW_LOW_AVG7D_VALUE]: {
				[COL_NAME]: lang('4H Low Low'),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center', fontWeight: 'bold', color: '#007bff' },
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <span>{rowData[colid]}<span style={{ color: 'red', fontWeight: 'normal' }}> [{rowData[VOLATILITY_4H_LOW_LOW_AVG7D_RANK]}]</span></span>
				}

			},

			[VOLATILITY_4H_CLOSE_LOW_AVG7D_VALUE]: {
				[COL_NAME]: lang('4H Close Low'),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center', fontWeight: 'bold', color: '#007bff' },
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <span>{rowData[colid]}<span style={{ color: 'red', fontWeight: 'normal' }}> [{rowData[VOLATILITY_4H_CLOSE_LOW_AVG7D_RANK]}]</span></span>
				}

			},

			[VOLATILITY_1D_HIGH_LOW_AVG7D_VALUE]: {
				[COL_NAME]: lang('1D High Low'),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center', fontWeight: 'bold' },
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <span>{rowData[colid]}<span style={{ color: 'red', fontWeight: 'normal' }}> [{rowData[VOLATILITY_1D_HIGH_LOW_AVG7D_RANK]}]</span></span>
				}

			},
			[VOLATILITY_1D_HIGH_HIGH_AVG7D_VALUE]: {
				[COL_NAME]: lang('1D High High'),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center', fontWeight: 'bold' },
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <span>{rowData[colid]}<span style={{ color: 'red', fontWeight: 'normal' }}> [{rowData[VOLATILITY_1D_HIGH_HIGH_AVG7D_RANK]}]</span></span>
				}

			},
			[VOLATILITY_1D_LOW_LOW_AVG7D_VALUE]: {
				[COL_NAME]: lang('1D Low Low'),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center', fontWeight: 'bold' },
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <span>{rowData[colid]}<span style={{ color: 'red', fontWeight: 'normal' }}> [{rowData[VOLATILITY_1D_LOW_LOW_AVG7D_RANK]}]</span></span>
				}

			},

			[VOLATILITY_1D_CLOSE_LOW_AVG7D_VALUE]: {
				[COL_NAME]: lang('1D Close Low'),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center', fontWeight: 'bold' },
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <span>{rowData[colid]}<span style={{ color: 'red', fontWeight: 'normal' }}> [{rowData[VOLATILITY_1D_CLOSE_LOW_AVG7D_RANK]}]</span></span>
				}

			},



			Analytics: {
				[COL_NAME]: lang('Analytics'),
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <div className='box_flex' style={{ justifyContent: 'center' }}>
						<div className='button btn btn-info btn-sm' style={{ fontSize: 10 }} onClick={() => {
							this.fluctChart.getData(rowData[VOLATILITY_SYMBOL], '1h');
							this.fluctChart.modal();
						}}>1H</div>
						<div className='button btn btn-info btn-sm' style={{ fontSize: 10 }} onClick={() => {
							this.fluctChart.getData(rowData[VOLATILITY_SYMBOL], '4h');
							this.fluctChart.modal();
						}}>4H</div>
						<div className='button btn btn-info btn-sm' style={{ fontSize: 10 }} onClick={() => {
							this.fluctChart.getData(rowData[VOLATILITY_SYMBOL], '1d');
							this.fluctChart.modal();
						}}>1D</div>
					</div>
				}
			},
			[VOLATILITY_TIME]: {
				[COL_NAME]: lang('Update Time'),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},



		}
		this.volatility_struct[STRUCT_FILTERS] = {

			[VOLATILITY_SYMBOL]: {
				[FILTER_NAME]: lang(VOLATILITY_SYMBOL),
				[FILTER_TYPE]: 'text',
			},



		}

		this.volatility_struct[STRUCT_EDIT] = {


		}

		this.volatility_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData} />
				</div>
			},
			[ROW_BANNER]: (data, visibleColumns) => {
				return <tr>
					<th style={{ visibility: "hidden" }} colSpan={3}></th>
					<th style={{ background: 'white' }} colSpan={8}>Avg 3 Days</th>
					<th style={{ background: 'white' }} colSpan={8}>Avg 7 Days</th>
					<th style={{ visibility: "hidden" }} colSpan={2}></th>
				</tr>
			}
		};
		this.volatility_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: VOLATILITY_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionVolatilityView(),
			[DATA_KEY]: [VOLATILITY_ID],
			[DATA_SORT]: { [VOLATILITY_4H_HIGH_LOW_AVG3D_VALUE]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: false,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Volatility()

		};


		this.volumeModel = new Candle_24h();
		this.volumeData = {};

		this.coinMarketModel = new Coinmarket();
		this.watchlistIcon = {};
		this.coinMarketData = {};

		this.userTradeIndex = {};


	}

	permissionVolatilityView() {
		return Object.assign(
			...Object.keys(this.volatility_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.volatility_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	async getVolume24H(){
		var startDate = Math.floor(moment().format('X')/86400)*86400000;
		var dateData = await this.volumeModel.read({ [CANDLE_24H_DATE]: startDate }, false);
		var indexData = {};
		if(dateData['result']){
			var volData = dateData['data']; 
			volData = volData.sort((a,b)=> Number(b[CANDLE_24H_VOLUME_USDT]) - Number(a[CANDLE_24H_VOLUME_USDT]));
			for(let i in volData){
				indexData[volData[i][CANDLE_24H_SYMBOL]] = Number(i)+1;
			}
			this.volumeData = indexData;

		}
	}

	async getMarketData() {
		if(SERVER_LOCATION != 'google')
			this.coinMarketData = await this.coinMarketModel.getRank();
	}

	async getUserData(){
		var tradeModel = new Trades();
		this.userTradeIndex = await tradeModel.getUserTrade(App.accountSelector.getSelectedAccount());
	}

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.volatility_struct} autoload={false}>
					<FuncBar
						left={<><div className='button btn btn-sm btn-warning' onClick={() => {
							this.trackAvgAlertModal.modal()
						}} ><i className="fa fa-bell-o"></i>&nbsp;Alert</div></>}
						right={<><FuncClear></FuncClear><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-resizable'></MainTable>
					<Pagination></Pagination>
					<FluctuationsChart ref={c => this.fluctChart = c}></FluctuationsChart>
					<TrackAvgAlertModal ref={c => this.trackAvgAlertModal = c}></TrackAvgAlertModal>
				</Table>


			</div>
		);
	}
	getIcon() {
		var watchlist = new Watchlist();

		return watchlist.getIcon();

	}

	componentDidMount() {
		this.getVolume24H().then(()=>{
			this.getUserData();
		}).then(()=>{
			this.getMarketData();
		}).then(()=>{
			this.getIcon().then((res)=>{
				// console.log(res)
				this.watchlistIcon = res;
				this.table.filter();
			});
		})

		this.refeshInterval = setInterval(() => {
			this.getVolume24H().then(() => {
				this.table.filter(false);
			})
		}, 120000);
	}

	componentWillUnmount() {
		if (this.refeshInterval) {
			clearInterval(this.refeshInterval)
		}
	}
}

export default VolatilityView
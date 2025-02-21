import React, { Component } from 'react';

import Table from '../../components/table/Table';
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

import CoinMarket from '../../model/admin/Coinmarket'
import CoinMarketAlertModal from './CoinMarketAlertModal';
import Watchlist from '../../model/admin/Watchlist'
class CoinMarketTable extends Component {
	constructor(props) {
		super(props);

		this.coin_market_struct = {};
		this.coin_market_struct[STRUCT_FILTERS] = {}
		this.coin_market_struct[STRUCT_COLUMNS] = {

			[COINMARKET_SYMBOL]: {
				[COL_NAME]: lang(COINMARKET_SYMBOL),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => {

					if (data === null) return '';
					var img = this.watchlistIcon[data];
					if (img == undefined) {
						img = '/assets/img/Eicon.png'
						// img = this.watchlistIcon['BTCUSDT']
					}
					return <b>
						<img style={{ width: '20px', height: '20px', marginRight: '10px' }} src={img}></img>
						{data}
					</b>
				}

			},

			[COINMARKET_RANK]: {
				[COL_NAME]: lang(COINMARKET_RANK),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },

			},

			[COINMARKET_PRICE]: {
				[COL_NAME]: lang(COINMARKET_PRICE),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: data => {
					if (data === null) return '';

					return <span>{`$${formatNumber(data.toFixed(2))}`}</span>
				}

			},

			[COINMARKET_PERCENT_CHANGE_1H]: {
				[COL_NAME]: lang(COINMARKET_PERCENT_CHANGE_1H),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: data => {
					if (data === null) return '';
					if (data < 0) return <b style={{ color: 'red' }}>{Number(data).toFixed(2) + '%'}</b>
					if (data >= 0) return <b style={{ color: 'limegreen' }}>{Number(data).toFixed(2) + '%'}</b>
					return <b>{data + '%'}</b>
				}

			},

			[COINMARKET_PERCENT_CHANGE_24H]: {
				[COL_NAME]: lang(COINMARKET_PERCENT_CHANGE_24H),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: data => {
					if (data === null) return '';
					if (data < 0) return <b style={{ color: 'red' }}>{Number(data).toFixed(2) + '%'}</b>
					if (data >= 0) return <b style={{ color: 'limegreen' }}>{Number(data).toFixed(2) + '%'}</b>
					return <b>{data + '%'}</b>
				}

			},
			[COINMARKET_PERCENT_CHANGE_7D]: {
				[COL_NAME]: lang(COINMARKET_PERCENT_CHANGE_7D),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: data => {
					if (data === null) return '';
					if (data < 0) return <b style={{ color: 'red' }}>{Number(data).toFixed(2) + '%'}</b>
					if (data >= 0) return <b style={{ color: 'limegreen' }}>{Number(data).toFixed(2) + '%'}</b>
					return <b>{data + '%'}</b>
				}

			},
			[COINMARKET_PERCENT_CHANGE_30D]: {
				[COL_NAME]: lang(COINMARKET_PERCENT_CHANGE_30D),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: data => {
					if (data === null) return '';
					if (data < 0) return <b style={{ color: 'red' }}>{Number(data).toFixed(2) + '%'}</b>
					if (data >= 0) return <b style={{ color: 'limegreen' }}>{Number(data).toFixed(2) + '%'}</b>
					return <b>{data + '%'}</b>
				}

			},
			[COINMARKET_MARKET_CAP]: {
				[COL_NAME]: lang(COINMARKET_MARKET_CAP),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: data => {
					if (data === null) return '';

					return <span>{`$${formatNumber(Math.floor(data))}`}</span>
				}

			},
			[COINMARKET_VOLUME_24H]: {
				[COL_NAME]: lang(COINMARKET_VOLUME_24H),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: data => {
					if (data === null) return '';

					return <span>{`$${formatNumber(Math.ceil(data))}`}</span>
				}

			},

			[COINMARKET_LAST_UPDATED]: {
				[COL_NAME]: lang(COINMARKET_LAST_UPDATED),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap', textAlign: 'center' }

			},






		}
		this.coin_market_struct[STRUCT_FILTERS] = {

			[COINMARKET_SYMBOL]: {
				[FILTER_NAME]: lang(COINMARKET_SYMBOL),
				[FILTER_TYPE]: 'text',
			},

		}

		this.coin_market_struct[STRUCT_EDIT] = {

		}


		this.coin_market_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: COINMARKET_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {
				// [ORDER_TRACK_1H_DOWN]: true,
				// [ORDER_TRACK_1H_UP]: true,
				// [ORDER_TRACK_PRICE]: true,
				// [ORDER_TRACK_CLOSE]: true,
				// [ORDER_TRACK_LOW]: true,
				// [ORDER_TRACK_HIGH]: true,
				// [ORDER_TRACK_15M_DOWN]: true,
				// [ORDER_TRACK_15M_UP]: true,
				// [ORDER_TRACK_3M_DOWN]: true,
				// [ORDER_TRACK_3M_UP]: true,
				// [ORDER_TRACK_PRICE]: true,
				// [ORDER_TRACK_1D_RSI_WMA]: true,
				// [ORDER_TRACK_RSI1H_1]: true,
				// [ORDER_TRACK_RSI1H_0]: true,
				// [ORDER_TRACK_RSI4H_0]: true,
				// [ORDER_TRACK_RSI4H_1]: true,
				// [ORDER_TRACK_RSI_EMA9]: true,
				// action: true,
			},
			[DATA_PERMIT_COL]: this.permissionCoinMarketView(),
			[DATA_KEY]: [COINMARKET_ID],
			[DATA_SORT]: { [COINMARKET_ID]: 'asc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: false,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,
			[PAGE_QUANTITY]: 10,

			model: new CoinMarket()

		};
		this.watchlistIcon = {};

	}

	permissionCoinMarketView() {
		return Object.assign(
			...Object.keys(this.coin_market_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.coin_market_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}
	getIcon() {
		var watchlist = new Watchlist();

		return watchlist.getIcon();

	}

	componentDidMount() {
		this.getIcon().then(res => {
			this.watchlistIcon = res;
			this.table.filter(false);
		});
		this.interval = setInterval(() => {
			this.table.filter(false);

		}, 300000);
	}
	componentWillUnmount() {
		if (this.interval) clearInterval(this.interval);
	}
	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.coin_market_struct} autoload={true} >
					<FuncBar
						left={<><FuncHideCol /><div className='button btn btn-sm btn-warning' onClick={() => {
							this.CoinMarketAlertModal.modal()
						}} ><i className="fa fa-bell-o"></i>&nbsp;Alert</div></>}
						name={'Marketcap'}
						right={<><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-resizable'></MainTable>
					<Pagination></Pagination>

				</Table>
				<CoinMarketAlertModal ref={c => this.CoinMarketAlertModal = c}></CoinMarketAlertModal>
			</div>
		);
	}
}

export default CoinMarketTable;
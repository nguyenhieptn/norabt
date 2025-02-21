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

import Candle_1w from '../../model/admin/Candle_1w'

class Candle_1wView extends Component {

	constructor(props) {
		super(props);

		this.candle_1w_struct = {};
		this.candle_1w_struct[STRUCT_FILTERS] = {}
		this.candle_1w_struct[STRUCT_COLUMNS] = {

			[CANDLE_1W_SYMBOL]: {
				[COL_NAME]: lang(CANDLE_1W_SYMBOL),
				[COL_SORT]: true,
			},

			[CANDLE_1W_OPEN_TIME]: {
				[COL_NAME]: lang(CANDLE_1W_OPEN_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},

			[CANDLE_1W_CLOSE_TIME]: {
				[COL_NAME]: lang(CANDLE_1W_CLOSE_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},

			[CANDLE_1W_OPEN]: {
				[COL_NAME]: lang(CANDLE_1W_OPEN),
				[COL_SORT]: true,

			},
			[CANDLE_1W_CLOSE]: {
				[COL_NAME]: lang(CANDLE_1W_CLOSE),
				[COL_SORT]: true,

			},
			[CANDLE_1W_HIGH]: {
				[COL_NAME]: lang(CANDLE_1W_HIGH),
				[COL_SORT]: true,

			},
			[CANDLE_1W_LOW]: {
				[COL_NAME]: lang(CANDLE_1W_LOW),
				[COL_SORT]: true,

			},
			[CANDLE_1W_TRADES]: {
				[COL_NAME]: lang(CANDLE_1W_TRADES),
				[COL_SORT]: true,

			},
			[CANDLE_1W_VOLUME]: {
				[COL_NAME]: lang(CANDLE_1W_VOLUME),
				[COL_SORT]: true,

			},
			[CANDLE_1W_EMA5]: {
				[COL_NAME]: lang(CANDLE_1W_EMA5),
				[COL_SORT]: true,

			},
			[CANDLE_1W_EMA9]: {
				[COL_NAME]: lang(CANDLE_1W_EMA9),
				[COL_SORT]: true,

			},
			[CANDLE_1W_EMA12]: {
				[COL_NAME]: lang(CANDLE_1W_EMA12),
				[COL_SORT]: true,

			},
			[CANDLE_1W_EMA13]: {
				[COL_NAME]: lang(CANDLE_1W_EMA13),
				[COL_SORT]: true,

			},
			[CANDLE_1W_EMA26]: {
				[COL_NAME]: lang(CANDLE_1W_EMA26),
				[COL_SORT]: true,

			},
			[CANDLE_1W_MACD]: {
				[COL_NAME]: lang(CANDLE_1W_MACD),
				[COL_SORT]: true,

			},
			[CANDLE_1W_SIGNAL]: {
				[COL_NAME]: lang(CANDLE_1W_SIGNAL),
				[COL_SORT]: true,

			},
			[CANDLE_1W_HISTOGRAM]: {
				[COL_NAME]: lang(CANDLE_1W_HISTOGRAM),
				[COL_SORT]: true,

			},
			[CANDLE_1W_SIGNAL2]: {
				[COL_NAME]: lang(CANDLE_1W_SIGNAL2),
				[COL_SORT]: true,

			},
			[CANDLE_1W_HISTOGRAM2]: {
				[COL_NAME]: lang(CANDLE_1W_HISTOGRAM2),
				[COL_SORT]: true,

			},
			[CANDLE_1W_SIGNAL3]: {
				[COL_NAME]: lang(CANDLE_1W_SIGNAL3),
				[COL_SORT]: true,

			},
			[CANDLE_1W_HISTOGRAM3]: {
				[COL_NAME]: lang(CANDLE_1W_HISTOGRAM3),
				[COL_SORT]: true,

			},
			[CANDLE_1W_SIGNAL4]: {
				[COL_NAME]: lang(CANDLE_1W_SIGNAL4),
				[COL_SORT]: true,

			},
			[CANDLE_1W_HISTOGRAM4]: {
				[COL_NAME]: lang(CANDLE_1W_HISTOGRAM4),
				[COL_SORT]: true,

			},
			[CANDLE_1W_SIGNAL5]: {
				[COL_NAME]: lang(CANDLE_1W_SIGNAL5),
				[COL_SORT]: true,

			},
			[CANDLE_1W_HISTOGRAM5]: {
				[COL_NAME]: lang(CANDLE_1W_HISTOGRAM5),
				[COL_SORT]: true,

			},
			[CANDLE_1W_SIGNAL6]: {
				[COL_NAME]: lang(CANDLE_1W_SIGNAL6),
				[COL_SORT]: true,

			},
			[CANDLE_1W_HISTOGRAM6]: {
				[COL_NAME]: lang(CANDLE_1W_HISTOGRAM6),
				[COL_SORT]: true,

			},
			[CANDLE_1W_SIGNAL7]: {
				[COL_NAME]: lang(CANDLE_1W_SIGNAL7),
				[COL_SORT]: true,

			},
			[CANDLE_1W_RSI14]: {
				[COL_NAME]: lang(CANDLE_1W_RSI14),
				[COL_SORT]: true,

			},
			[CANDLE_1W_RSI_EMA9]: {
				[COL_NAME]: lang(CANDLE_1W_RSI_EMA9),
				[COL_SORT]: true,

			},
			[CANDLE_1W_RSI_EMA5]: {
				[COL_NAME]: lang(CANDLE_1W_RSI_EMA5),
				[COL_SORT]: true,

			},
			[CANDLE_1W_RSI_EMA4]: {
				[COL_NAME]: lang(CANDLE_1W_RSI_EMA4),
				[COL_SORT]: true,

			},
			[CANDLE_1W_RSI_WMA]: {
				[COL_NAME]: lang(CANDLE_1W_RSI_WMA),
				[COL_SORT]: true,

			},
			[CANDLE_1W_RSI_EMA9]: {
				[COL_NAME]: lang(CANDLE_1W_RSI_EMA9),
				[COL_SORT]: true,

			},
			[CANDLE_1W_RSI_WMA45]: {
				[COL_NAME]: lang(CANDLE_1W_RSI_WMA45),
				[COL_SORT]: true,

			},
			[CANDLE_1W_PRICE_EMA9]: {
				[COL_NAME]: lang(CANDLE_1W_PRICE_EMA9),
				[COL_SORT]: true,

			},
			[CANDLE_1W_PRICE_WMA45]: {
				[COL_NAME]: lang(CANDLE_1W_PRICE_WMA45),
				[COL_SORT]: true,

			},
			[CANDLE_1W_NET_EMA9_WMA45]: {
				[COL_NAME]: lang(CANDLE_1W_NET_EMA9_WMA45),
				[COL_SORT]: true,

			},



		}
		this.candle_1w_struct[STRUCT_FILTERS] = {

			[CANDLE_1W_SYMBOL]: {
				[FILTER_NAME]: lang(CANDLE_1W_SYMBOL),
				[FILTER_TYPE]: 'select',
			},
			[CANDLE_1W_OPEN_TIME]: {
				[FILTER_NAME]: lang(CANDLE_1W_OPEN_TIME),
				[FILTER_TYPE]: 'date',
			},
			[CANDLE_1W_CLOSE_TIME]: {
				[FILTER_NAME]: lang(CANDLE_1W_CLOSE_TIME),
				[FILTER_TYPE]: 'date',
			},
			[CANDLE_1W_OPEN]: {
				[FILTER_NAME]: lang(CANDLE_1W_OPEN),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_1W_CLOSE]: {
				[FILTER_NAME]: lang(CANDLE_1W_CLOSE),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_1W_HIGH]: {
				[FILTER_NAME]: lang(CANDLE_1W_HIGH),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_1W_LOW]: {
				[FILTER_NAME]: lang(CANDLE_1W_LOW),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_1W_TRADES]: {
				[FILTER_NAME]: lang(CANDLE_1W_TRADES),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_1W_VOLUME]: {
				[FILTER_NAME]: lang(CANDLE_1W_VOLUME),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_1W_EMA5]: {
				[FILTER_NAME]: lang(CANDLE_1W_EMA5),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_1W_EMA9]: {
				[FILTER_NAME]: lang(CANDLE_1W_EMA9),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_1W_EMA12]: {
				[FILTER_NAME]: lang(CANDLE_1W_EMA12),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_1W_EMA13]: {
				[FILTER_NAME]: lang(CANDLE_1W_EMA13),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_1W_EMA26]: {
				[FILTER_NAME]: lang(CANDLE_1W_EMA26),
				[FILTER_TYPE]: 'text',
			},

			[CANDLE_1W_MACD]: {
				[FILTER_NAME]: lang(CANDLE_1W_MACD),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_1W_SIGNAL]: {
				[FILTER_NAME]: lang(CANDLE_1W_SIGNAL),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_1W_HISTOGRAM]: {
				[FILTER_NAME]: lang(CANDLE_1W_HISTOGRAM),
				[FILTER_TYPE]: 'text',
			},

		}

		this.candle_1w_struct[STRUCT_EDIT] = {


			[CANDLE_1W_EMA5]: {
				[EDIT_NAME]: lang(CANDLE_1W_EMA5),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_1W_EMA9]: {
				[EDIT_NAME]: lang(CANDLE_1W_EMA9),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_1W_EMA12]: {
				[EDIT_NAME]: lang(CANDLE_1W_EMA12),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_1W_EMA13]: {
				[EDIT_NAME]: lang(CANDLE_1W_EMA13),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_1W_EMA26]: {
				[EDIT_NAME]: lang(CANDLE_1W_EMA26),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_1W_MACD]: {
				[EDIT_NAME]: lang(CANDLE_1W_MACD),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_1W_SIGNAL]: {
				[EDIT_NAME]: lang(CANDLE_1W_SIGNAL),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_1W_HISTOGRAM]: {
				[EDIT_NAME]: lang(CANDLE_1W_HISTOGRAM),
				[EDIT_TYPE]: 'text',

			},


		}

		this.candle_1w_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData} />
				</div>
			}
		};
		this.candle_1w_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: CANDLE_1W_TABLE,
			[DATA_SPECIAL]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionCandle_1wView(),
			[DATA_KEY]: [CANDLE_1W_ID],
			[DATA_SORT]: { [CANDLE_1W_ID]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Candle_1w()

		};


	}

	permissionCandle_1wView() {
		return Object.assign(
			...Object.keys(this.candle_1w_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.candle_1w_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	render() {
		
		return (
			<div>
				<Table ref={c => this.table = c} table={this.candle_1w_struct} autoload={true}>
					<FuncBar
						left={<FuncHideCol />}
						right={<><FuncAdd /><FuncDel /><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-striped table-resizable'></MainTable>
					<Pagination></Pagination>

				</Table>


				<div className='box_flex' style={{ justifyContent: 'flex-end' }}>
					{Object.keys(this.candle_1w_struct[STRUCT_EDIT]).map(item => {
						return <div key={item} className='button btn' style={{ border: 'solid thin darkgray', borderRadius: 5 }} onClick={() => {
							clearColumn(CANDLE_1W_TABLE, item, App.symbol).then(res => {
								if (res) {
									if (res['result']) {
										this.table.filter();
									} else {
										error_handle(res);
									}
								}
							})
						}}>Clear {lang(item)}</div>
					})}
				</div>


			</div>
		);
	}
}

export default Candle_1wView
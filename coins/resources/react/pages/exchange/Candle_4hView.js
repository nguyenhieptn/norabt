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

import Candle_4h from '../../model/admin/Candle_4h'

class Candle_4hView extends Component {

	constructor(props) {
		super(props);

		this.candle_4h_struct = {};
		this.candle_4h_struct[STRUCT_FILTERS] = {}
		this.candle_4h_struct[STRUCT_COLUMNS] = {

			[CANDLE_4H_SYMBOL]: {
				[COL_NAME]: lang(CANDLE_4H_SYMBOL),
				[COL_SORT]: true,


			},
			[CANDLE_4H_OPEN_TIME]: {
				[COL_NAME]: lang(CANDLE_4H_OPEN_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},
			[CANDLE_4H_CLOSE_TIME]: {
				[COL_NAME]: lang(CANDLE_4H_CLOSE_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},
			[CANDLE_4H_OPEN]: {
				[COL_NAME]: lang(CANDLE_4H_OPEN),
				[COL_SORT]: true,

			},
			[CANDLE_4H_CLOSE]: {
				[COL_NAME]: lang(CANDLE_4H_CLOSE),
				[COL_SORT]: true,

			},
			[CANDLE_4H_HIGH]: {
				[COL_NAME]: lang(CANDLE_4H_HIGH),
				[COL_SORT]: true,

			},
			[CANDLE_4H_LOW]: {
				[COL_NAME]: lang(CANDLE_4H_LOW),
				[COL_SORT]: true,

			},
			[CANDLE_4H_TRADES]: {
				[COL_NAME]: lang(CANDLE_4H_TRADES),
				[COL_SORT]: true,

			},
			[CANDLE_4H_VOLUME]: {
				[COL_NAME]: lang(CANDLE_4H_VOLUME),
				[COL_SORT]: true,

			},
			[CANDLE_4H_EMA5]: {
				[COL_NAME]: lang(CANDLE_4H_EMA5),
				[COL_SORT]: true,

			},
			[CANDLE_4H_EMA9]: {
				[COL_NAME]: lang(CANDLE_4H_EMA9),
				[COL_SORT]: true,

			},
			[CANDLE_4H_EMA12]: {
				[COL_NAME]: lang(CANDLE_4H_EMA12),
				[COL_SORT]: true,

			},
			[CANDLE_4H_EMA13]: {
				[COL_NAME]: lang(CANDLE_4H_EMA13),
				[COL_SORT]: true,

			},
			[CANDLE_4H_EMA26]: {
				[COL_NAME]: lang(CANDLE_4H_EMA26),
				[COL_SORT]: true,

			},
			[CANDLE_4H_MACD]: {
				[COL_NAME]: lang(CANDLE_4H_MACD),
				[COL_SORT]: true,

			},
			[CANDLE_4H_SIGNAL]: {
				[COL_NAME]: lang(CANDLE_4H_SIGNAL),
				[COL_SORT]: true,

			},
			[CANDLE_4H_HISTOGRAM]: {
				[COL_NAME]: lang(CANDLE_4H_HISTOGRAM),
				[COL_SORT]: true,

			},
			[CANDLE_4H_SIGNAL7]: {
				[COL_NAME]: lang(CANDLE_4H_SIGNAL7),
				[COL_SORT]: true,

			},
			[CANDLE_4H_HISTOGRAM7]: {
				[COL_NAME]: lang(CANDLE_4H_HISTOGRAM7),
				[COL_SORT]: true,

			},
			[CANDLE_4H_SIGNAL4]: {
				[COL_NAME]: lang(CANDLE_4H_SIGNAL4),
				[COL_SORT]: true,

			},
			[CANDLE_4H_HISTOGRAM4]: {
				[COL_NAME]: lang(CANDLE_4H_HISTOGRAM4),
				[COL_SORT]: true,

			},
			[CANDLE_4H_SIGNAL5]: {
				[COL_NAME]: lang(CANDLE_4H_SIGNAL5),
				[COL_SORT]: true,

			},
			[CANDLE_4H_HISTOGRAM5]: {
				[COL_NAME]: lang(CANDLE_4H_HISTOGRAM5),
				[COL_SORT]: true,

			},
			[CANDLE_4H_SIGNAL6]: {
				[COL_NAME]: lang(CANDLE_4H_SIGNAL6),
				[COL_SORT]: true,

			},
			[CANDLE_4H_HISTOGRAM6]: {
				[COL_NAME]: lang(CANDLE_4H_HISTOGRAM6),
				[COL_SORT]: true,

			},
			[CANDLE_4H_SIGNAL2]: {
				[COL_NAME]: lang(CANDLE_4H_SIGNAL2),
				[COL_SORT]: true,

			},
			[CANDLE_4H_HISTOGRAM2]: {
				[COL_NAME]: lang(CANDLE_4H_HISTOGRAM2),
				[COL_SORT]: true,

			},
			[CANDLE_4H_SIGNAL3]: {
				[COL_NAME]: lang(CANDLE_4H_SIGNAL3),
				[COL_SORT]: true,

			},
			[CANDLE_4H_HISTOGRAM3]: {
				[COL_NAME]: lang(CANDLE_4H_HISTOGRAM3),
				[COL_SORT]: true,

			},
			[CANDLE_4H_RSI14]: {
				[COL_NAME]: lang(CANDLE_4H_RSI14),
				[COL_SORT]: true,

			},
			[CANDLE_4H_RSI_EMA9]: {
				[COL_NAME]: lang(CANDLE_4H_RSI_EMA9),
				[COL_SORT]: true,

			},
			[CANDLE_4H_RSI_EMA5]: {
				[COL_NAME]: lang(CANDLE_4H_RSI_EMA5),
				[COL_SORT]: true,

			},
			[CANDLE_4H_RSI_EMA4]: {
				[COL_NAME]: lang(CANDLE_4H_RSI_EMA4),
				[COL_SORT]: true,

			},
			[CANDLE_4H_RSI_WMA]: {
				[COL_NAME]: lang(CANDLE_4H_RSI_WMA),
				[COL_SORT]: true,

			},



		}
		this.candle_4h_struct[STRUCT_FILTERS] = {

			[CANDLE_4H_SYMBOL]: {
				[FILTER_NAME]: lang(CANDLE_4H_SYMBOL),
				[FILTER_TYPE]: 'select',
			},
			[CANDLE_4H_OPEN_TIME]: {
				[FILTER_NAME]: lang(CANDLE_4H_OPEN_TIME),
				[FILTER_TYPE]: 'date',
				[FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },
			},
			[CANDLE_4H_CLOSE_TIME]: {
				[FILTER_NAME]: lang(CANDLE_4H_CLOSE_TIME),
				[FILTER_TYPE]: 'date',
				[FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },
			},
			[CANDLE_4H_OPEN]: {
				[FILTER_NAME]: lang(CANDLE_4H_OPEN),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_4H_CLOSE]: {
				[FILTER_NAME]: lang(CANDLE_4H_CLOSE),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_4H_HIGH]: {
				[FILTER_NAME]: lang(CANDLE_4H_HIGH),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_4H_LOW]: {
				[FILTER_NAME]: lang(CANDLE_4H_LOW),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_4H_TRADES]: {
				[FILTER_NAME]: lang(CANDLE_4H_TRADES),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_4H_VOLUME]: {
				[FILTER_NAME]: lang(CANDLE_4H_VOLUME),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_4H_EMA5]: {
				[FILTER_NAME]: lang(CANDLE_4H_EMA5),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_4H_EMA9]: {
				[FILTER_NAME]: lang(CANDLE_4H_EMA9),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_4H_EMA12]: {
				[FILTER_NAME]: lang(CANDLE_4H_EMA12),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_4H_EMA13]: {
				[FILTER_NAME]: lang(CANDLE_4H_EMA13),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_4H_EMA26]: {
				[FILTER_NAME]: lang(CANDLE_4H_EMA26),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_4H_MACD]: {
				[FILTER_NAME]: lang(CANDLE_4H_MACD),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_4H_SIGNAL]: {
				[FILTER_NAME]: lang(CANDLE_4H_SIGNAL),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_4H_HISTOGRAM]: {
				[FILTER_NAME]: lang(CANDLE_4H_HISTOGRAM),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_4H_SIGNAL7]: {
				[FILTER_NAME]: lang(CANDLE_4H_SIGNAL7),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_4H_HISTOGRAM7]: {
				[FILTER_NAME]: lang(CANDLE_4H_HISTOGRAM7),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_4H_SIGNAL4]: {
				[FILTER_NAME]: lang(CANDLE_4H_SIGNAL4),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_4H_HISTOGRAM4]: {
				[FILTER_NAME]: lang(CANDLE_4H_HISTOGRAM4),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_4H_SIGNAL5]: {
				[FILTER_NAME]: lang(CANDLE_4H_SIGNAL5),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_4H_HISTOGRAM5]: {
				[FILTER_NAME]: lang(CANDLE_4H_HISTOGRAM5),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_4H_SIGNAL6]: {
				[FILTER_NAME]: lang(CANDLE_4H_SIGNAL6),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_4H_HISTOGRAM6]: {
				[FILTER_NAME]: lang(CANDLE_4H_HISTOGRAM6),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_4H_SIGNAL2]: {
				[FILTER_NAME]: lang(CANDLE_4H_SIGNAL2),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_4H_HISTOGRAM2]: {
				[FILTER_NAME]: lang(CANDLE_4H_HISTOGRAM2),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_4H_SIGNAL3]: {
				[FILTER_NAME]: lang(CANDLE_4H_SIGNAL3),
				[FILTER_TYPE]: 'text',
			},
			[CANDLE_4H_HISTOGRAM3]: {
				[FILTER_NAME]: lang(CANDLE_4H_HISTOGRAM3),
				[FILTER_TYPE]: 'text',
			},


		}

		this.candle_4h_struct[STRUCT_EDIT] = {

			[CANDLE_4H_SYMBOL]: {
				[EDIT_NAME]: lang(CANDLE_4H_SYMBOL),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_4H_OPEN_TIME]: {
				[EDIT_NAME]: lang(CANDLE_4H_OPEN_TIME),
				[EDIT_TYPE]: 'date',
				[EDIT_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[EDIT_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },

			},
			[CANDLE_4H_CLOSE_TIME]: {
				[EDIT_NAME]: lang(CANDLE_4H_CLOSE_TIME),
				[EDIT_TYPE]: 'date',
				[EDIT_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[EDIT_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },

			},
			[CANDLE_4H_OPEN]: {
				[EDIT_NAME]: lang(CANDLE_4H_OPEN),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_4H_CLOSE]: {
				[EDIT_NAME]: lang(CANDLE_4H_CLOSE),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_4H_HIGH]: {
				[EDIT_NAME]: lang(CANDLE_4H_HIGH),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_4H_LOW]: {
				[EDIT_NAME]: lang(CANDLE_4H_LOW),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_4H_TRADES]: {
				[EDIT_NAME]: lang(CANDLE_4H_TRADES),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_4H_VOLUME]: {
				[EDIT_NAME]: lang(CANDLE_4H_VOLUME),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_4H_EMA5]: {
				[EDIT_NAME]: lang(CANDLE_4H_EMA5),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_4H_EMA9]: {
				[EDIT_NAME]: lang(CANDLE_4H_EMA9),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_4H_EMA12]: {
				[EDIT_NAME]: lang(CANDLE_4H_EMA12),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_4H_EMA13]: {
				[EDIT_NAME]: lang(CANDLE_4H_EMA13),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_4H_EMA26]: {
				[EDIT_NAME]: lang(CANDLE_4H_EMA26),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_4H_MACD]: {
				[EDIT_NAME]: lang(CANDLE_4H_MACD),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_4H_SIGNAL]: {
				[EDIT_NAME]: lang(CANDLE_4H_SIGNAL),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_4H_HISTOGRAM]: {
				[EDIT_NAME]: lang(CANDLE_4H_HISTOGRAM),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_4H_SIGNAL7]: {
				[EDIT_NAME]: lang(CANDLE_4H_SIGNAL7),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_4H_HISTOGRAM7]: {
				[EDIT_NAME]: lang(CANDLE_4H_HISTOGRAM7),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_4H_SIGNAL4]: {
				[EDIT_NAME]: lang(CANDLE_4H_SIGNAL4),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_4H_HISTOGRAM4]: {
				[EDIT_NAME]: lang(CANDLE_4H_HISTOGRAM4),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_4H_SIGNAL5]: {
				[EDIT_NAME]: lang(CANDLE_4H_SIGNAL5),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_4H_HISTOGRAM5]: {
				[EDIT_NAME]: lang(CANDLE_4H_HISTOGRAM5),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_4H_SIGNAL6]: {
				[EDIT_NAME]: lang(CANDLE_4H_SIGNAL6),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_4H_HISTOGRAM6]: {
				[EDIT_NAME]: lang(CANDLE_4H_HISTOGRAM6),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_4H_SIGNAL2]: {
				[EDIT_NAME]: lang(CANDLE_4H_SIGNAL2),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_4H_HISTOGRAM2]: {
				[EDIT_NAME]: lang(CANDLE_4H_HISTOGRAM2),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_4H_SIGNAL3]: {
				[EDIT_NAME]: lang(CANDLE_4H_SIGNAL3),
				[EDIT_TYPE]: 'text',

			},
			[CANDLE_4H_HISTOGRAM3]: {
				[EDIT_NAME]: lang(CANDLE_4H_HISTOGRAM3),
				[EDIT_TYPE]: 'text',

			},


		}

		this.candle_4h_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData} />
				</div>
			}
		};
		this.candle_4h_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: CANDLE_4H_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionCandle_4hView(),
			[DATA_KEY]: [CANDLE_4H_ID],
			[DATA_SORT]: { [CANDLE_4H_ID]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Candle_4h()

		};


	}

	permissionCandle_4hView() {
		return Object.assign(
			...Object.keys(this.candle_4h_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.candle_4h_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.candle_4h_struct} autoload={true}>
					<FuncBar
						left={<FuncHideCol />}
						right={<><FuncAdd /><FuncDel /><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-striped table-resizable'></MainTable>
					<Pagination></Pagination>

				</Table>


			</div>
		);
	}
}

export default Candle_4hView
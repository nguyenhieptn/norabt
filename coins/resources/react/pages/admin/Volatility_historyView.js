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

import Volatility_history from '../../model/admin/Volatility_history'
import Watchlist from '../../model/admin/Watchlist'
class Volatility_historyView extends Component {

	constructor(props) {
		super(props);

		this.volatility_history_struct = {};
		this.volatility_history_struct[STRUCT_FILTERS] = {}
		this.volatility_history_struct[STRUCT_COLUMNS] = {

			[VOLATILITY_SYMBOL]: {
				[COL_NAME]: lang(VOLATILITY_SYMBOL),
				[COL_SORT]: true,
				[COL_STYLE]: { fontWeight:'bold'},
				[COL_DECORATOR_IN]: data => {
					
					
					return <span >
						<img style={{ width: '20px', height: '20px', marginRight: '10px' }} src={this.watchlistIcon[data]}></img>
						{data}
					
					</span>
				}

			},



			[VOLATILITY_4H_HIGHHIGH_T0_VALUE]: {
				[COL_NAME]: lang(VOLATILITY_4H_HIGHHIGH_T0_VALUE),
				[COL_SORT]: true,
				[COL_STYLE]: {textAlign:'center', fontWeight:'bold', color: '#007bff'},
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <span>{rowData[colid]}<span style={{color:'red', fontWeight:'normal'}}> [{rowData[VOLATILITY_4H_HIGHHIGH_T0_RANK]}]</span></span>
				}

			},
			[VOLATILITY_4H_HIGHHIGH_T1_VALUE]: {
				[COL_NAME]: lang(VOLATILITY_4H_HIGHHIGH_T1_VALUE),
				[COL_SORT]: true,
				[COL_STYLE]: {textAlign:'center', fontWeight:'bold', color: '#007bff'},
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <span>{rowData[colid]}<span style={{color:'red', fontWeight:'normal'}}> [{rowData[VOLATILITY_4H_HIGHHIGH_T1_RANK]}]</span></span>
				}

			},
			[VOLATILITY_4H_HIGHHIGH_T2_VALUE]: {
				[COL_NAME]: lang(VOLATILITY_4H_HIGHHIGH_T2_VALUE),
				[COL_SORT]: true,
				[COL_STYLE]: {textAlign:'center', fontWeight:'bold', color: '#007bff'},
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <span>{rowData[colid]}<span style={{color:'red', fontWeight:'normal'}}> [{rowData[VOLATILITY_4H_HIGHHIGH_T2_RANK]}]</span></span>
				}

			},



			[VOLATILITY_1D_HIGHHIGH_T0_VALUE]: {
				[COL_NAME]: lang(VOLATILITY_1D_HIGHHIGH_T0_VALUE),
				[COL_SORT]: true,
				[COL_STYLE]: {textAlign:'center', fontWeight:'bold'},
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <span>{rowData[colid]}<span style={{color:'red', fontWeight:'normal'}}> [{rowData[VOLATILITY_1D_HIGHHIGH_T0_RANK]}]</span></span>
				}

			},
			[VOLATILITY_1D_HIGHHIGH_T1_VALUE]: {
				[COL_NAME]: lang(VOLATILITY_1D_HIGHHIGH_T1_VALUE),
				[COL_SORT]: true,
				[COL_STYLE]: {textAlign:'center', fontWeight:'bold'},
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <span>{rowData[colid]}<span style={{color:'red', fontWeight:'normal'}}> [{rowData[VOLATILITY_1D_HIGHHIGH_T1_RANK]}]</span></span>
				}

			},
			[VOLATILITY_1D_HIGHHIGH_T2_VALUE]: {
				[COL_NAME]: lang(VOLATILITY_1D_HIGHHIGH_T2_VALUE),
				[COL_SORT]: true,
				[COL_STYLE]: {textAlign:'center', fontWeight:'bold'},
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <span>{rowData[colid]}<span style={{color:'red', fontWeight:'normal'}}> [{rowData[VOLATILITY_1D_HIGHHIGH_T2_RANK]}]</span></span>
				}

			},




			[VOLATILITY_4H_HIGHLOW_T0_VALUE]: {
				[COL_NAME]: lang(VOLATILITY_4H_HIGHLOW_T0_VALUE),
				[COL_SORT]: true,
				[COL_STYLE]: {textAlign:'center', fontWeight:'bold', color: '#007bff'},
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <span>{rowData[colid]}<span style={{color:'red', fontWeight:'normal'}}> [{rowData[VOLATILITY_4H_HIGHLOW_T0_RANK]}]</span></span>
				}

			},
			[VOLATILITY_4H_HIGHLOW_T1_VALUE]: {
				[COL_NAME]: lang(VOLATILITY_4H_HIGHLOW_T1_VALUE),
				[COL_SORT]: true,
				[COL_STYLE]: {textAlign:'center', fontWeight:'bold', color: '#007bff'},
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <span>{rowData[colid]}<span style={{color:'red', fontWeight:'normal'}}> [{rowData[VOLATILITY_4H_HIGHLOW_T1_RANK]}]</span></span>
				}

			},
			[VOLATILITY_4H_HIGHLOW_T2_VALUE]: {
				[COL_NAME]: lang(VOLATILITY_4H_HIGHLOW_T2_VALUE),
				[COL_SORT]: true,
				[COL_STYLE]: {textAlign:'center', fontWeight:'bold', color: '#007bff'},
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <span>{rowData[colid]}<span style={{color:'red', fontWeight:'normal'}}> [{rowData[VOLATILITY_4H_HIGHLOW_T2_RANK]}]</span></span>
				}

			},

			
			
			

			[VOLATILITY_1D_HIGHLOW_T0_VALUE]: {
				[COL_NAME]: lang(VOLATILITY_1D_HIGHLOW_T0_VALUE),
				[COL_SORT]: true,
				[COL_STYLE]: {textAlign:'center', fontWeight:'bold'},
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <span>{rowData[colid]}<span style={{color:'red', fontWeight:'normal'}}> [{rowData[VOLATILITY_1D_HIGHLOW_T0_RANK]}]</span></span>
				}

			},
			[VOLATILITY_1D_HIGHLOW_T1_VALUE]: {
				[COL_NAME]: lang(VOLATILITY_1D_HIGHLOW_T1_VALUE),
				[COL_SORT]: true,
				[COL_STYLE]: {textAlign:'center', fontWeight:'bold'},
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <span>{rowData[colid]}<span style={{color:'red', fontWeight:'normal'}}> [{rowData[VOLATILITY_1D_HIGHLOW_T1_RANK]}]</span></span>
				}

			},
			[VOLATILITY_1D_HIGHLOW_T2_VALUE]: {
				[COL_NAME]: lang(VOLATILITY_1D_HIGHLOW_T2_VALUE),
				[COL_SORT]: true,
				[COL_STYLE]: {textAlign:'center', fontWeight:'bold'},
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <span>{rowData[colid]}<span style={{color:'red', fontWeight:'normal'}}> [{rowData[VOLATILITY_1D_HIGHLOW_T2_RANK]}]</span></span>
				}

			},

			


			
			
			

			[VOLATILITY_TIME]: {
				[COL_NAME]: lang(VOLATILITY_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},

		}

		this.volatility_history_struct[STRUCT_FILTERS] = {

			[VOLATILITY_ID]: {
				[FILTER_NAME]: lang(VOLATILITY_ID),
				[FILTER_TYPE]: 'text',
			},
			[VOLATILITY_SYMBOL]: {
				[FILTER_NAME]: lang(VOLATILITY_SYMBOL),
				[FILTER_TYPE]: 'text',
			},
			
			[VOLATILITY_4H_HIGHLOW_T0_VALUE]: {
				[FILTER_NAME]: lang(VOLATILITY_4H_HIGHLOW_T0_VALUE),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<=']
			},
			[VOLATILITY_4H_HIGHLOW_T1_VALUE]: {
				[FILTER_NAME]: lang(VOLATILITY_4H_HIGHLOW_T1_VALUE),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<=']
			},
			[VOLATILITY_4H_HIGHLOW_T2_VALUE]: {
				[FILTER_NAME]: lang(VOLATILITY_4H_HIGHLOW_T2_VALUE),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<=']
			},
			[VOLATILITY_4H_HIGHHIGH_T0_VALUE]: {
				[FILTER_NAME]: lang(VOLATILITY_4H_HIGHHIGH_T0_VALUE),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<=']
			},
			[VOLATILITY_4H_HIGHHIGH_T1_VALUE]: {
				[FILTER_NAME]: lang(VOLATILITY_4H_HIGHHIGH_T1_VALUE),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<=']
			},
			[VOLATILITY_4H_HIGHHIGH_T2_VALUE]: {
				[FILTER_NAME]: lang(VOLATILITY_4H_HIGHHIGH_T2_VALUE),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<=']
			},
			[VOLATILITY_1D_HIGHLOW_T0_VALUE]: {
				[FILTER_NAME]: lang(VOLATILITY_1D_HIGHLOW_T0_VALUE),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<=']
			},
			[VOLATILITY_1D_HIGHLOW_T1_VALUE]: {
				[FILTER_NAME]: lang(VOLATILITY_1D_HIGHLOW_T1_VALUE),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<=']
			},
			[VOLATILITY_1D_HIGHLOW_T2_VALUE]: {
				[FILTER_NAME]: lang(VOLATILITY_1D_HIGHLOW_T2_VALUE),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<=']
			},
			[VOLATILITY_1D_HIGHHIGH_T0_VALUE]: {
				[FILTER_NAME]: lang(VOLATILITY_1D_HIGHHIGH_T0_VALUE),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<=']
			},
			[VOLATILITY_1D_HIGHHIGH_T1_VALUE]: {
				[FILTER_NAME]: lang(VOLATILITY_1D_HIGHHIGH_T1_VALUE),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<=']
			},
			[VOLATILITY_1D_HIGHHIGH_T2_VALUE]: {
				[FILTER_NAME]: lang(VOLATILITY_1D_HIGHHIGH_T2_VALUE),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<=']
			},
			[VOLATILITY_4H_HIGHLOW_T0_RANK]: {
				[FILTER_NAME]: lang(VOLATILITY_4H_HIGHLOW_T0_RANK),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<=']
			},
			[VOLATILITY_4H_HIGHLOW_T1_RANK]: {
				[FILTER_NAME]: lang(VOLATILITY_4H_HIGHLOW_T1_RANK),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<=']
			},
			[VOLATILITY_4H_HIGHLOW_T2_RANK]: {
				[FILTER_NAME]: lang(VOLATILITY_4H_HIGHLOW_T2_RANK),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<=']
			},
			[VOLATILITY_4H_HIGHHIGH_T0_RANK]: {
				[FILTER_NAME]: lang(VOLATILITY_4H_HIGHHIGH_T0_RANK),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<=']
			},
			[VOLATILITY_4H_HIGHHIGH_T1_RANK]: {
				[FILTER_NAME]: lang(VOLATILITY_4H_HIGHHIGH_T1_RANK),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<=']
			},
			[VOLATILITY_4H_HIGHHIGH_T2_RANK]: {
				[FILTER_NAME]: lang(VOLATILITY_4H_HIGHHIGH_T2_RANK),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<=']
			},
			[VOLATILITY_1D_HIGHLOW_T0_RANK]: {
				[FILTER_NAME]: lang(VOLATILITY_1D_HIGHLOW_T0_RANK),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<=']
			},
			[VOLATILITY_1D_HIGHLOW_T1_RANK]: {
				[FILTER_NAME]: lang(VOLATILITY_1D_HIGHLOW_T1_RANK),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<=']
			},
			[VOLATILITY_1D_HIGHLOW_T2_RANK]: {
				[FILTER_NAME]: lang(VOLATILITY_1D_HIGHLOW_T2_RANK),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<=']
			},
			[VOLATILITY_1D_HIGHHIGH_T0_RANK]: {
				[FILTER_NAME]: lang(VOLATILITY_1D_HIGHHIGH_T0_RANK),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<=']
			},
			[VOLATILITY_1D_HIGHHIGH_T1_RANK]: {
				[FILTER_NAME]: lang(VOLATILITY_1D_HIGHHIGH_T1_RANK),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<=']
			},
			[VOLATILITY_1D_HIGHHIGH_T2_RANK]: {
				[FILTER_NAME]: lang(VOLATILITY_1D_HIGHHIGH_T2_RANK),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<=']
			},


		}

		this.volatility_history_struct[STRUCT_EDIT] = {

			


		}

		this.volatility_history_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData} />
				</div>
			},
		};
		this.volatility_history_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: VOLATILITY_HISTORY_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionVolatility_historyView(),
			[DATA_KEY]: [VOLATILITY_ID],
			[DATA_SORT]: { [VOLATILITY_4H_HIGHLOW_T0_VALUE]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: false,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Volatility_history()

		};

		this.watchlistIcon = {};


	}

	permissionVolatility_historyView() {
		return Object.assign(
			...Object.keys(this.volatility_history_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.volatility_history_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}
	getIcon() {
		var watchlist = new Watchlist();

		return watchlist.getIcon();

	}
	componentDidMount() {

		this.getIcon().then((res) => {
			this.watchlistIcon = res;
			this.table.filter();
		})
	}


	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.volatility_history_struct} autoload={true}>
					<FuncBar
						left={<FuncHideCol />}
						right={<><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-resizable'></MainTable>
					<Pagination></Pagination>

				</Table>


			</div>
		);
	}
}

export default Volatility_historyView
import React, { Component } from 'react'
// import Table from '../../components/table/Table'
import Table from '../../components/table/TableStatic'
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

import Watchlist from '../../model/analytics/Watchlist'
import FluctuationsChart from '../../components/analytics/FluctuationsChart'
import Coinmarket from '../../../react/model/admin/Coinmarket'
class FluctuationView extends Component {

	constructor(props) {
		super(props);

		this.lab_watchlist_struct = {};
		this.lab_watchlist_struct[STRUCT_FILTERS] = {}
		this.lab_watchlist_struct[STRUCT_COLUMNS] = {

			[WL_SYMBOL]: {
				[COL_NAME]: lang(WL_SYMBOL),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <span >
					
						{rowData[colid]}
						<span style={{ color: 'blue', fontWeight: 'normal' }}> [{rowData['rank']}]</span>

					</span>
				}

			},
			'rank': {
				[COL_NAME]: 'Rank',
				[COL_SORT]: true,

			},

			

			Analytics: {
				[COL_NAME]: lang('Analytics'),
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <div className='box_flex' style={{justifyContent:'center'}}>
						<div className='button btn btn-info btn-sm' style={{fontSize:10}} onClick={()=>{
							this.fluctChart.getData(rowData[WL_SYMBOL], '1h');
							this.fluctChart.modal();
						}}>1H</div>
						<div className='button btn btn-info btn-sm' style={{fontSize:10}} onClick={()=>{
							this.fluctChart.getData(rowData[WL_SYMBOL], '4h');
							this.fluctChart.modal();
						}}>4H</div>
						<div className='button btn btn-info btn-sm' style={{fontSize:10}} onClick={()=>{
							this.fluctChart.getData(rowData[WL_SYMBOL], '1d');
							this.fluctChart.modal();
						}}>1D</div>
					</div>
				}
			}



		}
		this.lab_watchlist_struct[STRUCT_FILTERS] = {

			[WL_SYMBOL]: {
				[FILTER_NAME]: lang(WL_SYMBOL),
				[FILTER_TYPE]: 'text',
			},


		}

		this.lab_watchlist_struct[STRUCT_EDIT] = {

			[WL_SYMBOL]: {
				[EDIT_NAME]: lang(WL_SYMBOL),
				[EDIT_TYPE]: 'text',

			},


		}

		this.lab_watchlist_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
				
				</div>
			}
		};
		this.lab_watchlist_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: WATCHLIST_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionLab_watchlistView(),
			[DATA_KEY]: [WL_ID, WL_SYMBOL],
			[DATA_SORT]: { [WL_ID]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: false,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Watchlist()

		};




	}

	permissionLab_watchlistView() {
		return Object.assign(
			...Object.keys(this.lab_watchlist_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.lab_watchlist_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	getRankCoinMarket(){
		var model = new Coinmarket();

		return model.getRank()
	}
	async componentDidMount(){

		this.loadOrigin()
	}

	
    async loadOrigin() {
		
		let model = new Watchlist()

		let data = await model.read();
		if (!data['result']) {
            error_handle(data);
            return null;
        }else{
			let rankCoinMark = await this.getRankCoinMarket()
			data['data'].map(item => {
				let symbol = item[WL_SYMBOL]
				item['rank'] = symbol =='1000SHIBUSDT' ? rankCoinMark['SHIBUSDT'] : rankCoinMark[symbol]
			})
			this.table.setOrigin(data['data']);
		}
        


    }

	render() {
		return (
			<div>
				{/* <Table ref={c => this.table = c} table={this.lab_watchlist_struct} autoload={true}> */}
				<Table ref={c => this.table = c} table={this.lab_watchlist_struct} autoload={false} loadOrigin={this.loadOrigin.bind(this)}>
					<FuncBar
						left={<><FuncHideCol />
							{/* <div className='button btn btn-warning btn-sm' onClick={() => { this.calculates() }} style={{ fontSize: 12 }}>Calculates</div> */}
							{/* <div className='button btn btn-primary btn-sm' onClick={() => { this.startServices() }} style={{ fontSize: 12 }}>Start Crawler</div> */}
						</>}
						right={<><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-striped table-resizable'></MainTable>
					<Pagination></Pagination>

					<FluctuationsChart ref={c => this.fluctChart = c}></FluctuationsChart>

				</Table>


			</div>
		);
	}

	




}

export default FluctuationView
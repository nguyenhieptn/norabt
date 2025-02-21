import React, { Component } from 'react'
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

import Watchlist from '../../model/admin/Watchlist'
import FluctuationsChart from '../../components/analytics/FluctuationsChart'
import TrackAvgAlertModal from '../../components/admin/TrackAvgAlertModal'

class FluctuationView extends Component {

	constructor(props) {
		super(props);

		this.lab_watchlist_struct = {};
		this.lab_watchlist_struct[STRUCT_FILTERS] = {}
		this.lab_watchlist_struct[STRUCT_COLUMNS] = {

			[WL_SYMBOL]: {
				[COL_NAME]: lang(WL_SYMBOL),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {

					return <div ><b>{data}</b></div>
				}

			},

			'1d_high_low_avg3d': {
				[COL_NAME]: lang('1D High-Low'),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					// var data1 = [];
					// data.map(item => data1.push(item['1d_high_low_avg3d']));
					// console.log(data1);

					return <div className='text-center' ><b>{data[rowid][colid]}</b></div>
				}
			},

			'1d_high_high_avg3d': {
				[COL_NAME]: lang('1D High-High'),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {

					return <div className='text-center' ><b>{data}</b></div>
				}
			},

			'1d_low_low_avg3d': {
				[COL_NAME]: lang('1D Low-Low'),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {

					return <div className='text-center' ><b>{data}</b></div>
				}
			},

			'4h_high_low_avg3d': {
				[COL_NAME]: <span style={{ color: '#007bff' }}>{lang('4H High-Low')}</span>,
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {

					return <div className='text-center' style={{ color: '#007bff' }}> <b>{data}</b></div>
				}
			},

			'4h_high_high_avg3d': {
				[COL_NAME]: <span className='text-center' style={{ color: '#007bff' }}>{lang('4H High-High')}</span>,
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {

					return <div className='text-center' style={{ color: '#007bff' }}> <b>{data}</b></div>
				}
			},

			'4h_low_low_avg3d': {
				[COL_NAME]: <span style={{ color: '#007bff' }}>{lang('4H Low-Low')}</span>,
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {

					return <div className='text-center' style={{ color: '#007bff' }}> <b>{data}</b></div>
				}
			},

			'1d_high_low_avg7d': {
				[COL_NAME]: lang('1D High-Low'),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {

					return <div className='text-center' ><b>{data}</b></div>
				}
			},

			'1d_high_high_avg7d': {
				[COL_NAME]: lang('1D High-High'),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {

					return <div className='text-center' ><b>{data}</b></div>
				}
			},

			'1d_low_low_avg7d': {
				[COL_NAME]: lang('1D Low-Low'),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {

					return <div className='text-center' ><b>{data}</b></div>
				}
			},

			'4h_high_low_avg7d': {
				[COL_NAME]: <span style={{ color: '#007bff' }}>{lang('4H High-Low')}</span>,
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {

					return <div className='text-center' style={{ color: '#007bff' }}> <b>{data}</b></div>
				}
			},

			'4h_high_high_avg7d': {
				[COL_NAME]: <span style={{ color: '#007bff' }}>{lang('4H High-High')}</span>,
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {

					return <div className='text-center' style={{ color: '#007bff' }}> <b>{data}</b></div>
				}
			},

			'4h_low_low_avg7d': {
				[COL_NAME]: <span style={{ color: '#007bff' }}>{lang('4H Low-Low')}</span>,
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {

					return <div className='text-center' style={{ color: '#007bff' }}> <b>{data}</b></div>
				}
			},

			Analytics: {
				[COL_NAME]: lang('Analytics'),
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <div className='box_flex' style={{ justifyContent: 'center' }}>
						<div className='button btn btn-info btn-sm' style={{ fontSize: 10 }} onClick={() => {
							this.fluctChart.getData(rowData[WL_SYMBOL], '1h');
							this.fluctChart.modal();
						}}>1H</div>
						<div className='button btn btn-info btn-sm' style={{ fontSize: 10 }} onClick={() => {
							this.fluctChart.getData(rowData[WL_SYMBOL], '4h');
							this.fluctChart.modal();
						}}>4H</div>
						<div className='button btn btn-info btn-sm' style={{ fontSize: 10 }} onClick={() => {
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
			},
			[ROW_BANNER]: (data, visibleColumns) => {
				return <tr>
					<th style={{ visibility: "hidden" }} colSpan={3}></th>
					<th style={{ background: 'white' }} colSpan={6}>Avg 3 Days</th>
					<th style={{ background: 'white' }} colSpan={6}>Avg 7 Days</th>
					<th style={{ visibility: "hidden" }}></th>
				</tr>
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

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.lab_watchlist_struct} autoload={false} loadOrigin={this.loadOrigin.bind(this)}>
					<FuncBar
						left={<>
							{/* <div className='button btn btn-warning btn-sm' onClick={() => { this.calculates() }} style={{ fontSize: 12 }}>Calculates</div> */}
							{/* <div className='button btn btn-primary btn-sm' onClick={() => { this.startServices() }} style={{ fontSize: 12 }}>Start Crawler</div> */}
							<div className='button btn btn-sm btn-warning' onClick={() => {
								this.trackAvgAlertModal.modal()
							}} ><i className="fa fa-bell-o"></i>&nbsp;Alert</div>
						</>}
						right={<><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-resizable' minHeight={0}></MainTable>
					<Pagination></Pagination>

					<FluctuationsChart ref={c => this.fluctChart = c}></FluctuationsChart>

					<TrackAvgAlertModal ref={c => this.trackAvgAlertModal = c}></TrackAvgAlertModal>

				</Table>


			</div>
		);
	}

	loadOrigin(dataKeys, loading = true) {
		if (loading) App.loading(true, 'Loading...');
		this.table.model.readCalAvg(dataKeys).then((res) => {
			if (res) {
				if (res['result']) {
					var response = res['data'];
					this.table.setOrigin(response);
					this.table.filter();
				}
			}
		})

	}

	componentDidMount() {
		this.table.loadOrigin();
	}






}

export default FluctuationView
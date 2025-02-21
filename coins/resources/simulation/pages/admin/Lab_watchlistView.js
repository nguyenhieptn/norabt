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

import Lab_watchlist from '../../model/admin/Lab_watchlist'
import FluctuationsChart from '../../components/admin/FluctuationsChart'
import CrawlerYearModal from '../../components/admin/CrawlerYearModal'
import CrawlerYearCheckModal from '../../components/admin/CrawlerYearCheckModal'


import Coinmarket from '../../../react/model/admin/Coinmarket'

class Lab_watchlistView extends Component {

	constructor(props) {
		super(props);

		this.lab_watchlist_struct = {};
		this.lab_watchlist_struct[STRUCT_FILTERS] = {}
		this.lab_watchlist_struct[STRUCT_COLUMNS] = {

			[LAB_WL_SYMBOL]: {
				[COL_NAME]: lang(LAB_WL_SYMBOL),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => {
					var rankData = (data == '1000SHIBUSDT' ? 'SHIBUSDT' : data);

					return <b>
						{data}
						<span style={{ color: 'blue', fontWeight: 'normal' }}> [{get(this.coinMarketData[rankData], '')}]</span>
						</b>
				}

			},

			[LAB_WL_SYM_RANK]: {
				[COL_NAME]: lang(LAB_WL_SYM_RANK),
				[COL_SORT]: true,
				
			},

			'lab_candle': {
				[COL_NAME]: lang('Crawler Service'),
				[COL_DECORATOR_IN]: data => {
					return data ? <div style={{ color: '#00e209', fontWeight: 'bold', textAlign: 'center' }}>Running</div> : <div style={{ color: 'red', fontWeight: 'bold', textAlign: 'center' }}>Stopped</div>
				}
			},

			[LAB_WL_TIME]: {
				[COL_NAME]: lang(LAB_WL_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},

			[LAB_WL_STOPTIME]: {
				[COL_NAME]: lang(LAB_WL_STOPTIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},

			Analytics: {
				[COL_NAME]: lang('Analytics'),
				[COL_DECORATOR_IN]: (colid, rowid, data) => {
					var rowData = data[rowid];
					return <div className='box_flex' style={{ justifyContent: 'center' }}>
						<div className='button btn btn-info btn-sm' style={{ fontSize: 10 }} onClick={() => {
							this.fluctChart.getData(rowData[LAB_WL_SYMBOL], '1h');
							this.fluctChart.modal();
						}}>1H</div>
						<div className='button btn btn-info btn-sm' style={{ fontSize: 10 }} onClick={() => {
							this.fluctChart.getData(rowData[LAB_WL_SYMBOL], '4h');
							this.fluctChart.modal();
						}}>4H</div>
						<div className='button btn btn-info btn-sm' style={{ fontSize: 10 }} onClick={() => {
							this.fluctChart.getData(rowData[LAB_WL_SYMBOL], '1d');
							this.fluctChart.modal();
						}}>1D</div>
						{/* <div className='button btn btn-info btn-sm' style={{ fontSize: 10 }}
						 onClick={() => {
							// this.fluctChart.getData(rowData[LAB_WL_SYMBOL], '1d');
							this.Avg4h1dModal.modal();
						}}
						>4H-1D</div> */}
					</div>
				}
			}



		}
		this.lab_watchlist_struct[STRUCT_FILTERS] = {

			[LAB_WL_SYMBOL]: {
				[FILTER_NAME]: lang(LAB_WL_SYMBOL),
				[FILTER_TYPE]: 'text',
			},


		}

		this.lab_watchlist_struct[STRUCT_EDIT] = {

			[LAB_WL_SYMBOL]: {
				[EDIT_NAME]: lang(LAB_WL_SYMBOL),
				[EDIT_TYPE]: 'text',

			},


		}

		this.lab_watchlist_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData} ><div className='button btn btn-warning btn-sm' style={{ fontSize: 12 }}>Edit</div></FuncEditRow>
					<div className='button btn btn-danger btn-sm' onClick={() => { this.cleanData(rowData[LAB_WL_SYMBOL]) }} style={{ fontSize: 12 }}>Clean</div>
					{/* <div className='button btn btn-warning btn-sm' onClick={() => { this.calculate(rowData[LAB_WL_SYMBOL]) }} style={{ fontSize: 12 }}>Calculate</div> */}
					<div className='button btn btn-primary btn-sm' onClick={() => { this.restartServices(rowData[LAB_WL_SYMBOL]) }} style={{ fontSize: 12 }}>Start Crawler</div>
					


				</div>
			}
		};
		this.lab_watchlist_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: LAB_WATCHLIST_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionLab_watchlistView(),
			[DATA_KEY]: [LAB_WL_ID, LAB_WL_SYMBOL],
			[DATA_SORT]: { [LAB_WL_ID]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Lab_watchlist()

		};

		this.coinMarketData = {}


	}

	permissionLab_watchlistView() {
		return Object.assign(
			...Object.keys(this.lab_watchlist_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.lab_watchlist_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	updateRank(){

		
		makeQuestion(`Do you want update Rank `).then(res => {
			if(res){
				let model = new Lab_watchlist();


				model.updateRank().then(res => {
			
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
				<Table ref={c => this.table = c} table={this.lab_watchlist_struct} autoload={true}>
					<FuncBar
						left={<><FuncHideCol />
							{/* <div className='button btn btn-warning btn-sm' onClick={() => { this.calculates() }} style={{ fontSize: 12 }}>Calculates</div> */}
							{/* <div className='button btn btn-primary btn-sm' onClick={() => { this.startServices() }} style={{ fontSize: 12 }}>Start Crawler</div> */}
							<div className='button btn btn-primary btn-sm' onClick={() => { this.restartServices() }} style={{ fontSize: 12 }}>Start Crawler</div>
							<div className='button btn btn-danger btn-sm' onClick={() => { this.stopServices() }} style={{ fontSize: 12 }}>Stop Crawler</div>

							<div className='button btn btn-primary btn-sm' onClick={() => { this.startCrawlerYear() }} style={{ fontSize: 12 }}>Crawler 1m</div>
							<div className='button btn btn-primary btn-sm' onClick={() => { this.check1mData() }} style={{ fontSize: 12 }}>Check 1m Data</div>

							<button type="button" className="button btn btn-sm btn-primary" onClick={() => this.updateRank()}>Update Rank</button>

						</>}
						right={<><FuncAdd /><FuncDel /><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-striped table-resizable'></MainTable>
					<Pagination></Pagination>

					<FluctuationsChart ref={c => this.fluctChart = c}></FluctuationsChart>

					<CrawlerYearModal ref={c => this.CrawlerYearModal = c} ></CrawlerYearModal>

					<CrawlerYearCheckModal ref={c=>this.crawlerYearCheckModal = c}></CrawlerYearCheckModal>
				

				</Table>


			</div>
		);
	}

	getRankCoinMarket(){
		var model = new Coinmarket();

		return model.getRank()
	}


	async componentDidMount() {
		this.coinMarketData = await this.getRankCoinMarket()

		// this.table.map().then(res => {
		// 	this.table.filter()
		// })
		this.table.filter()
	}

	calculate(symbol, loading = true) {
		if (loading) App.loading(true)
		return axios.request({
			url: `/admin/lab_watchlist/calculate`,
			method: 'POST',
			data: {
				symbol: symbol
			}
		})

			.then(response => {
				if (loading) App.loading(false);
				response = response['data'];
				if (response['result']) {
					if (loading) this.table.filter();
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

	async calculates() {
		var dataSelect = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];
		var wl = [];
		for (let i in dataSelect) {
			wl.push(dataSelect[i][LAB_WL_SYMBOL]);
		}

		if (wl.length == 0) {
			showLog('Please select a symbol');
			return;
		}

		var confirm = await makeQuestion('Do you want to calculate: ' + wl.join(', ') + '?');
		if (!confirm) return;

		var promises = [];
		App.loading(true);
		for (let i in wl) {
			promises.push(this.calculate(wl[i], false));
		}

		Promise.all(promises).then(value => {
			App.loading(false);
			this.table.filter();
		});
	}



	startService(symbol, loading = true) {
		if (loading) App.loading(true)
		return axios.request({
			url: `/admin/lab_watchlist/startService`,
			method: 'POST',
			data: {
				symbol: symbol
			}
		})

			.then(response => {
				if (loading) App.loading(false);
				response = response['data'];
				if (response['result']) {
					if (loading) this.table.filter();
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


	async startServices() {
		var dataSelect = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];
		var wl = [];
		for (let i in dataSelect) {
			wl.push(dataSelect[i][LAB_WL_SYMBOL]);
		}

		if (wl.length == 0) {
			showLog('Please select a symbol');
			return;
		}

		var confirm = await makeQuestion('Do you want to start service: ' + wl.join(', ') + '?');
		if (!confirm) return;

		var promises = [];
		App.loading(true);
		for (let i in wl) {
			promises.push(this.startService(wl[i], false));
		}

		Promise.all(promises).then(value => {
			App.loading(false);
			this.table.filter();
		});
	}

	async startCrawlerYear() {

		var dataSelect = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];
		var wl = [];
		for (let i in dataSelect) {

			wl.push({
				symbol : dataSelect[i][LAB_WL_SYMBOL]
			});
		}

		// if (wl.length == 0) {
		// 	showLog('Please select a symbol');
		// 	return;
		// }

		this.CrawlerYearModal.modal();
		this.CrawlerYearModal.loadOrigin(wl);
	}


	async stopServices() {

		var dataSelect = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];
		var wl = [];
		for (let i in dataSelect) {
			wl.push(dataSelect[i][LAB_WL_SYMBOL]);
		}

		if (wl.length == 0) {
			showLog('Please select a symbol');
			return;
		}

		var confirm = await makeQuestion('Do you want to Stop service: ' + wl.join(', ') + '?');
		if (!confirm) return;

		for (let i in wl) {
			await this.stopService(wl[i]);

		}
	}

	async stopService(symbol) {

		App.loading(true)
		return axios.request({
			url: `/admin/lab_watchlist/stopService`,
			method: 'POST',
			data: {
				symbol: symbol
			}
		})

			.then(response => {
				App.loading(false);
				response = response['data'];
				if (response['result']) {
					this.table.filter();
				}
				else {
					error_handle(response);
				}
			})

			.catch((error) => {
				App.loading(false);
				error_handle(error)
				return false;
			})
	}


	async restartServices() {

		var dataSelect = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];
		var wl = [];
		for (let i in dataSelect) {
			wl.push(dataSelect[i][LAB_WL_SYMBOL]);
		}

		if (wl.length == 0) {
			showLog('Please select a symbol');
			return;
		}

		var confirm = await makeQuestion('Do you want to Start/Restart service: ' + wl.join(', ') + '?');
		if (!confirm) return;

		for (let i in wl) {
			await this.restartService(wl[i]);

		}
	}

	restartService(symbol) {
		App.loading(true)
		return axios.request({
			url: `/admin/lab_watchlist/restartService`,
			method: 'POST',
			data: {
				symbol: symbol
			}
		})

			.then(response => {
				App.loading(false);
				response = response['data'];
				if (response['result']) {
					this.table.filter();
				}
				else {
					error_handle(response);
				}
			})

			.catch((error) => {
				App.loading(false);
				error_handle(error)
				return false;
			})
	}


	async cleanData(symbol) {
		var confirm = await makeQuestion('Do you want to clean Data?');
		if (!confirm) return;
		App.loading(true)
		return axios.request({
			url: `/admin/lab_watchlist/cleanData`,
			method: 'POST',
			data: {
				symbol: symbol
			}
		})

			.then(response => {
				App.loading(false);
				response = response['data'];
				if (response['result']) {

				}
				else {
					error_handle(response);
				}
			})

			.catch((error) => {
				App.loading(false);
				error_handle(error)
				return false;
			})
	}



	check1mData(){
		var dataSelect = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];
		var wl = [];
		for (let i in dataSelect) {
			wl.push(dataSelect[i][LAB_WL_SYMBOL]);
		}

		if (wl.length == 0) {
			showLog('Please select a symbol');
			return;
		}

		this.crawlerYearCheckModal.modal()
		this.crawlerYearCheckModal.setState({symbols: wl})

	}





}

export default Lab_watchlistView
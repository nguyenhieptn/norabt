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


import Lab_optimization from '../../model/admin/Lab_optimization'

import FuncAddAOptimize from '../../components/admin/FuncAddAOptimize'
import ToolTip from '../../components/common/Tooltip'
import OptLogModal from '../../components/admin/OptLogModal'
import ResultSummaryModal from '../../components/admin/Opt_result/ResultSummaryModal'


class OptimizeView extends Component {

	constructor(props) {
		super(props);



		this.lab_optimize_struct = {};
		this.lab_optimize_struct[STRUCT_FILTERS] = {}
		this.lab_optimize_struct[STRUCT_COLUMNS] = {

			'action': {
				[COL_NAME]: lang('Action'),
				[COL_SORT]: false,
				[COL_STYLE]: {maxWidth:500},
				[COL_DECORATOR_IN]: (col, row, data) => {
					var rowData = data[row];
					var id = rowData[LAB_OPT_ID];
					return <div className='box_flex' style={{ justifyContent: 'center' }}>

						{/* <div className='button btn btn-primary' style={{ fontSize: 10 }} onClick={() => {
							this.optimize(id, true, 'python');
						}}>Start</div>
						<div className='button btn btn-warning' style={{ fontSize: 10 }} onClick={() => {
							this.optimize(id, true, 'python', true);
						}}>Resume</div> */}
						<div className='button btn btn-primary' style={{ fontSize: 10 }} onClick={() => {
							this.optimize(id, true, 'python_1m');
						}}>Start</div>
						<div className='button btn btn-warning' style={{ fontSize: 10 }} onClick={() => {
							this.optimize(id, true, 'python_1m', true);
						}}>Resume</div>
						<div className='button btn btn-danger' style={{ fontSize: 10 }} onClick={() => {
							this.killOptimize(id, true);
						}}>Stop</div>

						<div className='button btn btn-info' style={{ fontSize: 10 }} onClick={() => {
							// this.killOptimize(id, true);
							this.ResultSummaryModal.modal()
							this.ResultSummaryModal.loadOrigin(id)
						}}>Summary</div>

					</div>
				}

			},
			[LAB_OPT_NAME]: {
				[COL_NAME]: lang(LAB_OPT_NAME),
				[COL_SORT]: true,
				[COL_STYLE]: { maxWidth: 'unset' }

			},
			[LAB_OPT_ACCOUNT]: {
				[COL_NAME]: lang(LAB_OPT_ACCOUNT),
				[COL_SORT]: true,
				[COL_STYLE]: { maxWidth: 'unset' }

			},
			[LAB_OPT_PARAMS]: {
				[COL_NAME]: lang(LAB_OPT_PARAMS),
				[COL_SORT]: false,

			},
			[LAB_OPT_SERVER]: {
				[COL_NAME]: lang(LAB_OPT_SERVER),
				[COL_SORT]: true,
			},
			[LAB_OPT_THREAD]: {
				[COL_NAME]: lang(LAB_OPT_THREAD),
				[COL_SORT]: true,

			},
			[LAB_OPT_DATA_LENG]: {
				[COL_NAME]: lang(LAB_OPT_DATA_LENG),
				[COL_SORT]: true,

			},

			'isRunning': {
				[COL_NAME]: lang('State'),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => {
					return data == 0
					? <b style={{ color: 'red' }}>Stopped</b>
					: data == 1
					?<b style={{ color: 'limegreen' }}>Running</b> 
					:<b style={{ color: 'orange' }}>Paused</b> 
					
				}
			},

			[LAB_OPT_PROCESSED]: {
				[COL_NAME]: lang(LAB_OPT_PROCESSED),
				[COL_SORT]: false,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {

					var rowData = data[rowId];
					var data = rowData[colId];
					if (!data) data = '0,0';
					data = data.split(',');
					var total = get(data[0], 0);
					var process = get(data[1], 0);
					var percent = total > 0 ? Math.round(process * 100 / total) : 0;

					return <div className='box_flex' style={{ minWidth: 200 }}>

						<div className="progress" style={{ flexGrow: 1 }}>
							<div className="progress-bar progress-bar-striped active" role="progressbar" style={{ width: `${percent}%` }}>
								{`${process}/${total}`}
							</div>
						</div>

					</div>
				},

			},
			[LAB_OPT_START_TIME]: {
				[COL_NAME]: lang(LAB_OPT_START_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }

			},
			[LAB_OPT_STOP_TIME]: {
				[COL_NAME]: lang(LAB_OPT_STOP_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }

			},
		
			[LAB_OPT_LOG]: {
				[COL_NAME]: lang(LAB_OPT_LOG),
				[COL_SORT]: false,

			},
			[LAB_OPT_USER]: {
				[COL_NAME]: lang(LAB_OPT_USER),
				[COL_SORT]: false,

			},
			[LAB_OPT_NOTE]: {
				[COL_NAME]: lang(LAB_OPT_NOTE),
				[COL_SORT]: false,

			},





		}
		this.lab_optimize_struct[STRUCT_FILTERS] = {

			[LAB_OPT_ID]: {
				[FILTER_NAME]: lang(LAB_OPT_ID),
				[FILTER_TYPE]: 'text',
			},
			[LAB_OPT_NAME]: {
				[FILTER_NAME]: lang(LAB_OPT_NAME),
				[FILTER_TYPE]: 'text',
			},
			[LAB_OPT_SERVER]: {
				[FILTER_NAME]: lang(LAB_OPT_SERVER),
				[FILTER_TYPE]: 'select',
			},
			[LAB_OPT_USER]: {
				[FILTER_NAME]: lang(LAB_OPT_USER),
				[FILTER_TYPE]: 'select',
			},
			[LAB_OPT_ACCOUNT]: {
				[FILTER_NAME]: lang(LAB_OPT_ACCOUNT),
				[FILTER_TYPE]: 'select_unsort',
			},



		}

		this.lab_optimize_struct[STRUCT_EDIT] = {

		}

		this.lab_optimize_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData} onClick={e => {
						this.FuncAddAOptimize.modal()
						this.FuncAddAOptimize.setValue(rowData[LAB_OPT_ID])
					}} ><div className='button btn btn-sm btn-info' style={{ fontSize: 12 }}>Edit</div></FuncEditRow>
					<div className='button btn btn-sm btn-info' style={{ fontSize: 12 }} onClick={e => {

						window.open(App.link('/admin/opt_result/view?optimization=' + rowData[LAB_OPT_ID]));

					}}>Results</div>
					<div className='button btn btn-sm btn-info' style={{ fontSize: 12 }} onClick={e => {

						this.OptLogModal.modal()
						this.OptLogModal.setValue(rowData[LAB_OPT_ID])

					}}>Log</div>

					

				</div>
			},
		};
		this.mainModel = new Lab_optimization()
		this.lab_optimize_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: LAB_OPTIMIZATION_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: { [LAB_OPT_PARAMS]: true },
			[DATA_PERMIT_COL]: this.permissionLab_resultsView(),
			[DATA_KEY]: [LAB_OPT_ID],
			[DATA_SORT]: {[LAB_OPT_ID]: 'desc'},
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: this.mainModel

		};

		


	}

	permissionLab_resultsView() {
		return Object.assign(
			...Object.keys(this.lab_optimize_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.lab_optimize_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	componentDidMount() {
		this.intervalUpdate = setInterval(() => {
			this.table.filter(false)
		}, 30000)
	}

	componentWillUnmount() {
		if (this.intervalUpdate) {
			clearInterval(this.intervalUpdate)
		}
	}

	funcClone() {
		return (
			<div className="table_function">

				<div className="button" title="Add Row"
					onClick={(e) => {
						var dataSelect = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];
						
						var optId = Object.keys(dataSelect)[0];
						var leng =  Object.keys(dataSelect).length ; 


						if (leng !== 1) {
							showLog('Please select one optimization');
							return;
						}

						this.FuncAddAOptimize.modal()
						this.FuncAddAOptimize.setValue(optId , 'clone')
						
					}}
					style={{ display: 'flex' }}>
					<i className="fa fa-clone"></i>&nbsp;Clone
				</div>

			</div>
		)
	}

	

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.lab_optimize_struct} autoload={true}>
					<FuncBar
						left={<FuncHideCol />}
						right={<><FuncAdd onClick={() => {
							this.FuncAddAOptimize.modal()
							this.FuncAddAOptimize.setValue(null )
						}} />{this.funcClone()} <FuncClear /><FuncRefresh /> <FuncDel></FuncDel><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-striped table-resizable'></MainTable>
					<Pagination></Pagination>

				</Table>


				<FuncAddAOptimize ref={c => this.FuncAddAOptimize = c} table={() => this.table} onSave={e => this.table.filter()}></FuncAddAOptimize>
				<OptLogModal ref={c => this.OptLogModal = c} ></OptLogModal>

					<ResultSummaryModal ref={c => this.ResultSummaryModal = c} ></ResultSummaryModal>


			</div>
		);
	}

	async optimize(id, loading = true, code = "", isContinue=false) {

		if (!isContinue) {
			var confirm = await makeQuestion('Old result will be deleted. Do you want to start this Optimization?');
			if (!confirm) return;
			App.loading(true)
		}

		var url = code == 'python_1m' ? `/admin/lab_optimization/optimize1m` : `/admin/lab_optimization/optimize`

		return axios.request({
			url: url,
			method: 'POST',
			data: {
				id: id,
				continue: isContinue
			}
		})

			.then(response => {
				if (loading) App.loading(false);
				response = response['data'];
				if (response['result']) {
					this.table.filter();
				}
				else {
					error_handle(response);
				}
				return response;
			})

			.catch((error) => {
				if (loading) App.loading(false);
				error_handle(error)
				return false;
			})
	}

	async killOptimize(id, loading = true) {

		if (loading) {
			var confirm = await makeQuestion('Do you want to stop this Optimization?');
			if (!confirm) return;
		}

		if (loading) App.loading(true)
		return axios.request({
			url: `/admin/lab_optimization/kill`,
			method: 'POST',
			data: {
				id: id
			}
		})

			.then(response => {
				if (loading) App.loading(false);
				response = response['data'];
				if (response['result']) {
					this.table.filter();
				}
				else {
					error_handle(response);
				}
				return response;
			})

			.catch((error) => {
				if (loading) App.loading(false);
				error_handle(error)
				return false;
			})
	}


}

export default OptimizeView
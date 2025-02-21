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

import Lab_opt_schedule from '../../model/admin/Lab_opt_schedule'
import FunOptSchedule from '../../components/admin/FunOptSchedule'

class Lab_opt_scheduleView extends Component {

	constructor(props) {
		super(props);

		this.lab_opt_schedule_struct = {};
		this.lab_opt_schedule_struct[STRUCT_FILTERS] = {}
		this.lab_opt_schedule_struct[STRUCT_COLUMNS] = {

			'Action': {
				[COL_NAME]: 'Action',
				[COL_STYLE]: { maxWidth: 500 , textAlign : 'center'},
				[COL_DECORATOR_IN]: (col, row, data) => {
					var rowData = data[row];
					return (
						<>
							<div className='button btn btn-sm btn-primary' style={{ fontSize: 12 }} onClick={e => {

								this.OnRun(rowData, true)

							}}>Start</div>
							<div className='button btn btn-sm btn-danger' style={{ fontSize: 12 }} onClick={e => {

								this.OnRun(rowData, false)

							}}>Stop</div>
						</>

					)
				},

				
			},

			[LAB_OPT_SCHE_NAME]: {
				[COL_NAME]: lang(LAB_OPT_SCHE_NAME),
				[COL_SORT]: true,

			},
			[LAB_OPT_SCHE_PARAM]: {
				[COL_NAME]: lang(LAB_OPT_SCHE_PARAM),
				[COL_SORT]: false,
				[COL_STYLE]: { maxWidth: 1000},
				[COL_DECORATOR_IN]: data => {

					var data = JSON.parse(data);
					var mapping = this.table.mapping[LAB_OPT_ACCOUNT]
					if(!mapping) return
					return data.map((row,index) => {
						return (
							<div key={index} style={{display : 'flex'}}>
								<span style={{ flex : 2  }}>{mapping[row['opt']] ? mapping[row['opt']] : '' }</span> :
								<span style={{ flex : 1 , marginLeft : 20 }}>{row['status']}</span>
							</div>
						)
					})


				}

			},
			[LAB_OPT_SCHE_START]: {
				[COL_NAME]: lang(LAB_OPT_SCHE_START),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},
			[LAB_OPT_SCHE_STOP]: {
				[COL_NAME]: lang(LAB_OPT_SCHE_STOP),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},
			[LAB_OPT_SCHE_STATUS]: {
				[COL_NAME]: lang(LAB_OPT_SCHE_STATUS),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => {
					
					if (data == 0) {
						return (<b style={{ color: 'red' }}>Stopped</b>)
					}
					if (data == 1) {
						return (<b style={{ color: 'limegreen' }}>Running</b>)
					}


				}

			},
			[LAB_OPT_SCHE_USER]: {
				[COL_NAME]: lang(LAB_OPT_SCHE_USER),
				[COL_SORT]: false,

			},
			[LAB_OPT_SCHE_NOTE]: {
				[COL_NAME]: lang(LAB_OPT_SCHE_NOTE),
				[COL_SORT]: false,

			},
			[LAB_OPT_SCHE_LOG]: {
				[COL_NAME]: lang(LAB_OPT_SCHE_LOG),
				[COL_SORT]: false,

			},



		}
		this.lab_opt_schedule_struct[STRUCT_FILTERS] = {

			[LAB_OPT_SCHE_NAME]: {
				[FILTER_NAME]: lang(LAB_OPT_SCHE_NAME),
				[FILTER_TYPE]: 'text',
			},

			[LAB_OPT_SCHE_STATUS]: {
				[FILTER_NAME]: lang(LAB_OPT_SCHE_STATUS),
				[FILTER_TYPE]: 'select',
			},
			[LAB_OPT_SCHE_USER]: {
				[FILTER_NAME]: lang(LAB_OPT_SCHE_USER),
				[FILTER_TYPE]: 'select',
			},



		}

		this.lab_opt_schedule_struct[STRUCT_EDIT] = {

			[LAB_OPT_SCHE_NAME]: {
				[EDIT_NAME]: lang(LAB_OPT_SCHE_NAME),
				[EDIT_TYPE]: 'text',

			},
			[LAB_OPT_SCHE_PARAM]: {
				[EDIT_NAME]: lang(LAB_OPT_SCHE_PARAM),
				[EDIT_TYPE]: 'textarea',

			},
			[LAB_OPT_SCHE_START]: {
				[EDIT_NAME]: lang(LAB_OPT_SCHE_START),
				[EDIT_TYPE]: 'date',

			},
			[LAB_OPT_SCHE_STOP]: {
				[EDIT_NAME]: lang(LAB_OPT_SCHE_STOP),
				[EDIT_TYPE]: 'date',

			},
			[LAB_OPT_SCHE_STATUS]: {
				[EDIT_NAME]: lang(LAB_OPT_SCHE_STATUS),
				[EDIT_TYPE]: 'select',

			},
			[LAB_OPT_SCHE_NOTE]: {
				[EDIT_NAME]: lang(LAB_OPT_SCHE_NOTE),
				[EDIT_TYPE]: 'select',

			},
			[LAB_OPT_SCHE_NOTE]: {
				[EDIT_NAME]: lang(LAB_OPT_SCHE_NOTE),
				[EDIT_TYPE]: 'textarea',

			},
			[LAB_OPT_SCHE_LOG]: {
				[EDIT_NAME]: lang(LAB_OPT_SCHE_LOG),
				[EDIT_TYPE]: 'textarea',

			},


		}

		this.lab_opt_schedule_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData} onClick={e => {
						this.FunOptSchedule.modal()
						this.FunOptSchedule.setValue(rowData[LAB_OPT_SCHE_ID])
					}}  ><div className='button btn btn-sm btn-info' style={{ fontSize: 12 }}>Edit</div></FuncEditRow>

				</div>
			}
		};
		this.lab_opt_schedule_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: LAB_OPT_SCHEDULE_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionLab_opt_scheduleView(),
			[DATA_KEY]: [LAB_OPT_SCHE_ID],
			[DATA_SORT]: { [LAB_OPT_SCHE_ID]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Lab_opt_schedule()

		};


	}

	permissionLab_opt_scheduleView() {
		return Object.assign(
			...Object.keys(this.lab_opt_schedule_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.lab_opt_schedule_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	OnRun(row, isStart) {

		var data = {
			[LAB_OPT_SCHE_STATUS]: isStart ? 1 : 0,
			
		}
		
		if(isStart){
			data[LAB_OPT_SCHE_START] = moment().format('X');
			data[LAB_OPT_SCHE_STOP] =  null;
		}else{
			data[LAB_OPT_SCHE_STOP] =  moment().format('X');
		}

		
		var lab_opt_scheduleModel = new Lab_opt_schedule();
		lab_opt_scheduleModel.edit({
			[LAB_OPT_SCHE_ID]: row[LAB_OPT_SCHE_ID]
		}, data).then(res => {
			if (res['result']) {
				this.table.filter();
			} else {
				error_handle(res)
			}
		})

	}

	funcClone() {
		return (
			<div className="table_function">

				<div className="button" title="Add Row"
					onClick={(e) => {
						var dataSelect = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];

						var optId = Object.keys(dataSelect)[0];
						var leng = Object.keys(dataSelect).length;


						if (leng !== 1) {
							showLog('Please select one schedule');
							return;
						}

						this.FunOptSchedule.modal()
						this.FunOptSchedule.setValue(optId, 'clone')

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
				<Table ref={c => this.table = c} table={this.lab_opt_schedule_struct} autoload={true}>
					<FuncBar
						left={<FuncHideCol />}
						right={<><FuncAdd onClick={() => {
							this.FunOptSchedule.modal()
							this.FunOptSchedule.setValue(null)
						}} />{this.funcClone()} <FuncDel /><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-striped table-resizable'></MainTable>
					<Pagination></Pagination>

				</Table>

				<FunOptSchedule ref={c => this.FunOptSchedule = c} table={() => this.table}></FunOptSchedule>


			</div>
		);
	}
}

export default Lab_opt_scheduleView
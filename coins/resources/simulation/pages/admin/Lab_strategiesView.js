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

import Lab_strategies from '../../model/admin/Lab_strategies'
import Input from '../../components/input/Input'
import FuncEdit from '../../components/table/FuncEdit'
import ContainerEditModal from '../../components/admin/ContainerEditModal'
import FuncClone from '../../components/table/FuncClone'

class Lab_strategiesView extends Component {

	constructor(props) {
		super(props);
		this.lab_strategies_struct = {};
		this.lab_strategies_struct[STRUCT_FILTERS] = {}
		this.lab_strategies_struct[STRUCT_COLUMNS] = {


			[LAB_STRATEGY_NAME]: {
				[COL_NAME]: lang(LAB_STRATEGY_NAME),
				[COL_SORT]: true,
				[COL_STYLE]: { maxWidth: 'unset' },
				[COL_DECORATOR_IN]: (colId, rowId, tbdata) => {
					var data = tbdata[rowId][colId];
					var isContainer = tbdata[rowId][LAB_STRATEGY_CONTAINER];
					if(isContainer) return <div><i className="fa fa-cube" style={{marginRight:10}}></i><b>{data}</b></div>
					return <div><i className="fa fa-file-o" style={{marginRight:10}}></i><b>{data}</b></div>
				}
			},

			[LAB_STRATEGY_CONTENT]: {
				[COL_NAME]: lang(LAB_STRATEGY_CONTENT),
				[COL_SORT]: false,
				[COL_STYLE]: { whiteSpace: 'pre', minWidth: 400 }

			},
			[LAB_STRATEGY_TAKEPROFIT]: {
				[COL_NAME]: lang(LAB_STRATEGY_TAKEPROFIT),
				[COL_SORT]: true,

			},
			[LAB_STRATEGY_STOPLOSS]: {
				[COL_NAME]: lang(LAB_STRATEGY_STOPLOSS),
				[COL_SORT]: true,

			},
			[LAB_STRATEGY_BASEPROFIT]: {
				[COL_NAME]: lang(LAB_STRATEGY_BASEPROFIT),
				[COL_SORT]: true,

			},
			[LAB_STRATEGY_STEPPROFIT]: {
				[COL_NAME]: lang(LAB_STRATEGY_STEPPROFIT),
				[COL_SORT]: true,

			},
			[LAB_STRATEGY_BACKPROFIT]: {
				[COL_NAME]: lang(LAB_STRATEGY_BACKPROFIT),
				[COL_SORT]: true,

			},
			[LAB_STRATEGY_BASEPROFIT_BASEON]: {
				[COL_NAME]: lang(LAB_STRATEGY_BASEPROFIT_BASEON),
				[COL_SORT]: true,

			},
			[LAB_STRATEGY_TIMELIFE]: {
				[COL_NAME]: lang(LAB_STRATEGY_TIMELIFE),
				[COL_SORT]: true,

			},
			[LAB_STRATEGY_INTERVAL]: {
				[COL_NAME]: lang(LAB_STRATEGY_INTERVAL),
				[COL_SORT]: true,

			},
			[LAB_STRATEGY_MARGIN]: {
				[COL_NAME]: lang(LAB_STRATEGY_MARGIN),
				[COL_SORT]: true,

			},
			[LAB_STRATEGY_USER]: {
				[COL_NAME]: lang(LAB_STRATEGY_USER),
				[COL_SORT]: true,

			},
			[LAB_STRATEGY_GROUP]: {
				[COL_NAME]: lang(LAB_STRATEGY_GROUP),
				[COL_SORT]: true,

			},

			[LAB_STRATEGY_NOTE]: {
				[COL_NAME]: lang(LAB_STRATEGY_NOTE),
				[COL_SORT]: false,
				[COL_DECORATOR_IN]: (data) => <div dangerouslySetInnerHTML={{ __html: data }}></div>

			},



		}
		this.lab_strategies_struct[STRUCT_FILTERS] = {

			[LAB_STRATEGY_ID]: {
				[FILTER_NAME]: lang(LAB_STRATEGY_ID),
				[FILTER_TYPE]: 'text',
			},
			[LAB_STRATEGY_NAME]: {
				[FILTER_NAME]: lang(LAB_STRATEGY_NAME),
				[FILTER_TYPE]: 'text',
			},
			[LAB_STRATEGY_USER]: {
				[FILTER_NAME]: lang(LAB_STRATEGY_USER),
				[FILTER_TYPE]: 'select',
			},
			[LAB_STRATEGY_GROUP]: {
				[FILTER_NAME]: lang(LAB_STRATEGY_GROUP),
				[FILTER_TYPE]: 'text',
			},


		}

		this.lab_strategies_struct[STRUCT_EDIT] = {


			[LAB_STRATEGY_NAME]: {
				[EDIT_NAME]: lang(LAB_STRATEGY_NAME),
				[EDIT_TYPE]: 'text',
				[EDIT_NULL]: false,

			},
			[LAB_STRATEGY_CONTENT]: {
				[EDIT_NAME]: lang(LAB_STRATEGY_CONTENT),
				[EDIT_TYPE]: 'ace',
				[EDIT_NULL]: false,
				[EDIT_DES]: 'The configuration for Long/Short order (JSON format)'
			},
			[LAB_STRATEGY_TAKEPROFIT]: {
				[EDIT_NAME]: lang(LAB_STRATEGY_TAKEPROFIT),
				[EDIT_TYPE]: 'number',

			},
			[LAB_STRATEGY_STOPLOSS]: {
				[EDIT_NAME]: lang(LAB_STRATEGY_STOPLOSS),
				[EDIT_TYPE]: 'number',

			},
			[LAB_STRATEGY_BASEPROFIT]: {
				[EDIT_NAME]: lang(LAB_STRATEGY_BASEPROFIT),
				[EDIT_TYPE]: 'number',

			},
			[LAB_STRATEGY_STEPPROFIT]: {
				[EDIT_NAME]: lang(LAB_STRATEGY_STEPPROFIT),
				[EDIT_TYPE]: 'number',
				[EDIT_DES]: 'The increment step of base profit'

			},
			[LAB_STRATEGY_BACKPROFIT]: {
				[EDIT_NAME]: lang(LAB_STRATEGY_BACKPROFIT),
				[EDIT_TYPE]: 'number',
				[EDIT_DES]: 'Cancle order if profit < baseprofit - backprofit'

			},
			[LAB_STRATEGY_BASEPROFIT_BASEON]: {
				[EDIT_NAME]: lang(LAB_STRATEGY_BASEPROFIT_BASEON),
				[EDIT_TYPE]: 'select',
				[EDIT_DES]: 'Use to calculate base profit',
				[EDIT_DEFAULT]: 'close'
			},

			[LAB_STRATEGY_TIMELIFE]: {
				[EDIT_NAME]: lang(LAB_STRATEGY_TIMELIFE),
				[EDIT_TYPE]: 'number',
				[EDIT_DES]: 'The time before the Pending order is cancle in minutes',
				[EDIT_DEFAULT]: 6

			},
			[LAB_STRATEGY_INTERVAL]: {
				[EDIT_NAME]: lang(LAB_STRATEGY_INTERVAL),
				[EDIT_TYPE]: 'number',
				[EDIT_DES]: 'Interval between 2 Orders in minutes',
				[EDIT_DEFAULT]: 0

			},
			[LAB_STRATEGY_MARGIN]: {
				[EDIT_NAME]: lang(LAB_STRATEGY_MARGIN),
				[EDIT_TYPE]: 'number',
				[EDIT_DEFAULT]: 1

			},
			[LAB_STRATEGY_USER]: {
				[EDIT_NAME]: lang(LAB_STRATEGY_USER),
				[EDIT_TYPE]: 'select',

			},
			[LAB_STRATEGY_GROUP]: {
				[EDIT_NAME]: lang(LAB_STRATEGY_GROUP),
				[EDIT_TYPE]: 'text',
				[EDIT_DEFAULT]: App.parsed.group
			},
			[LAB_STRATEGY_NOTE]: {
				[EDIT_NAME]: lang(LAB_STRATEGY_NOTE),
				[EDIT_TYPE]: 'editor',

			},
		


		}

		this.lab_strategies_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData} onClick={()=>{
						if(rowData[LAB_STRATEGY_CONTAINER] == 1){
							this.containerEditModal.loadData(rowData);

							this.containerEditModal.setOptionUser(this.table.mapping[LAB_STRATEGY_USER] , this.table.mapping[LAB_STRATEGY_GROUP])
						 	this.containerEditModal.modal();
						}else{
							this.table.children['EditModal'].loadData(rowData);
						 	this.table.children['EditModal'].modal();
						}
					}} />
				</div>
			}
		};
		this.lab_strategies_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: LAB_STRATEGIES_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: { [LAB_STRATEGY_CONTENT]: true },
			[DATA_PERMIT_COL]: this.permissionLab_strategiesView(),
			[DATA_KEY]: [LAB_STRATEGY_ID],
			[DATA_SORT]: { [LAB_STRATEGY_ID]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Lab_strategies()

		};


	}

	permissionLab_strategiesView() {
		return Object.assign(
			...Object.keys(this.lab_strategies_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.lab_strategies_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
			{ 'lab_strategy_user': App.user[AUTHEN_GROUP] == 0 ? 'Write' : 'Read' }
		)
	}

	componentDidMount() {
		this.table.map().then(res => {
			this.table[STRUCT_TABLE][DATA_SPECIAL] = { group: App.parsed.group }
			this.table.filter();
		})
		

	}


	

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.lab_strategies_struct} autoload={false}>
					<FuncBar
						left={<><FuncHideCol /> <div style={{display : 'flex' , alignItems : 'center', fontSize : '16px'}}>
							
						<b><span style={{ cursor : 'pointer'}} onClick={() => {  window.location.href = App.link('/admin/lab_strategies_group/view')}}>Strategies</span> / {App.parsed.group}</b>

					</div></>}
						right={<>
						<div className='button' onClick={()=>{
							this.containerEditModal.loadData({});
							this.containerEditModal.setOptionUser(this.table.mapping[LAB_STRATEGY_USER] , this.table.mapping[LAB_STRATEGY_GROUP])
							this.containerEditModal.modal();
						}}><i className="fa fa-cubes"></i>&nbsp;Container</div>
						<FuncAdd /><FuncClone/> <FuncDel /><FuncEdit></FuncEdit><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-striped table-resizable'></MainTable>
					<Pagination></Pagination>

				</Table>

				<ContainerEditModal ref={c => this.containerEditModal = c} onClickHandle={()=>{this.table.filter()}}></ContainerEditModal>

				<style>{`
					.modal-lg {
						max-width: 90%
					}
					.editor_item {
						display: grid;
						grid-auto-flow: column;
						grid-gap: 10px;
						grid-template-columns: 1fr 2fr;
						align-items: center;
					}
				
				`}</style>


			</div>
		);
	}
}

export default Lab_strategiesView
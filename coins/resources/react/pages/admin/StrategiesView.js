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

import Strategies from '../../model/admin/Strategies'
import FuncEdit from '../../components/table/FuncEdit'
import FuncEditModal from '../../components/table/FuncEditModal'
import ContainerEditModal from '../../components/admin/ContainerEditModal'
import FuncClone from '../../components/table/FuncClone'

class StrategiesView extends Component {

	constructor(props) {
		super(props);

		this.strategies_struct = {};
		this.strategies_struct[STRUCT_FILTERS] = {}
		this.strategies_struct[STRUCT_COLUMNS] = {

			[STRATEGY_NAME]: {
				[COL_NAME]: lang(STRATEGY_NAME),
				[COL_SORT]: true,
				[COL_STYLE]: { maxWidth: 'unset' },
				[COL_DECORATOR_IN]: (colId, rowId, tbdata) => {
					var data = tbdata[rowId][colId];
					var isContainer = tbdata[rowId][STRATEGY_CONTAINER];
					if(isContainer) return <div><i className="fa fa-cube" style={{marginRight:10}}></i><b>{data}</b></div>
					return <div><i className="fa fa-file-o" style={{marginRight:10}}></i><b>{data}</b></div>
				}

			},
			[STRATEGY_CONTENT]: {
				[COL_NAME]: lang(STRATEGY_CONTENT),
				[COL_SORT]: false,
				[COL_STYLE]: { whiteSpace: 'pre', minWidth: 400 }

			},

			[STRATEGY_MARGIN]: {
				[COL_NAME]: lang(STRATEGY_MARGIN),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' },
				[COL_DECORATOR_IN]: data => {
					return <b style={{ color: 'red' }} >{data}</b>
				}

			},


			[STRATEGY_TAKEPROFIT]: {
				[COL_NAME]: lang(STRATEGY_TAKEPROFIT),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' }

			},
			[STRATEGY_STOPLOSS]: {
				[COL_NAME]: lang(STRATEGY_STOPLOSS),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' }

			},
			[STRATEGY_BASEPROFIT]: {
				[COL_NAME]: lang(STRATEGY_BASEPROFIT),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' }

			},
			[STRATEGY_STEPPROFIT]: {
				[COL_NAME]: lang(STRATEGY_STEPPROFIT),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' }

			},
			[STRATEGY_BACKPROFIT]: {
				[COL_NAME]: lang(STRATEGY_BACKPROFIT),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' }

			},
			[STRATEGY_BASEPROFIT_BASEON]: {
				[COL_NAME]: lang(STRATEGY_BASEPROFIT_BASEON),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' }

			},
			[STRATEGY_TIMELIFE]: {
				[COL_NAME]: lang(STRATEGY_TIMELIFE),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' }

			},
			[STRATEGY_INTERVAL]: {
				[COL_NAME]: lang(STRATEGY_INTERVAL),
				[COL_SORT]: true,
				[COL_STYLE]: { textAlign: 'center' }

			},
			[STRATEGY_USER]: {
				[COL_NAME]: lang(STRATEGY_USER),
				[COL_SORT]: true,
		

			},


			[STRATEGY_NOTE]: {
				[COL_NAME]: lang(STRATEGY_NOTE),
				[COL_SORT]: false,
				[COL_DECORATOR_IN]: (data) => <div dangerouslySetInnerHTML={{ __html: data }}></div>

			},



		}
		this.strategies_struct[STRUCT_FILTERS] = {

			[STRATEGY_NAME]: {
				[FILTER_NAME]: lang(STRATEGY_NAME),
				[FILTER_TYPE]: 'text',
			},
			[STRATEGY_USER]: {
				[FILTER_NAME]: lang(STRATEGY_USER),
				[FILTER_TYPE]: 'select',
			},


		}

		this.strategies_struct[STRUCT_EDIT] = {
		

			[STRATEGY_NAME]: {
				[EDIT_NAME]: lang(STRATEGY_NAME),
				[EDIT_TYPE]: 'text',
				[EDIT_NULL]: false,

			},
			[STRATEGY_CONTENT]: {
				[EDIT_NAME]: lang(STRATEGY_CONTENT),
				[EDIT_TYPE]: 'ace',
				[EDIT_NULL]: false,
				[EDIT_DES]: 'The configuration for Long/Short order (JSON format)'
			},
			[STRATEGY_TAKEPROFIT]: {
				[EDIT_NAME]: lang(STRATEGY_TAKEPROFIT),
				[EDIT_TYPE]: 'number',

			},
			[STRATEGY_STOPLOSS]: {
				[EDIT_NAME]: lang(STRATEGY_STOPLOSS),
				[EDIT_TYPE]: 'number',

			},
			[STRATEGY_BASEPROFIT]: {
				[EDIT_NAME]: lang(STRATEGY_BASEPROFIT),
				[EDIT_TYPE]: 'number',

			},
			[STRATEGY_STEPPROFIT]: {
				[EDIT_NAME]: lang(STRATEGY_STEPPROFIT),
				[EDIT_TYPE]: 'number',
				[EDIT_DES]: 'The increment step of base profit'

			},
			[STRATEGY_BACKPROFIT]: {
				[EDIT_NAME]: lang(STRATEGY_BACKPROFIT),
				[EDIT_TYPE]: 'number',
				[EDIT_DES]: 'Cancle order if profit < baseprofit - backprofit'

			},
			[STRATEGY_BASEPROFIT_BASEON]: {
				[EDIT_NAME]: lang(STRATEGY_BASEPROFIT_BASEON),
				[EDIT_TYPE]: 'select',
				[EDIT_DEFAULT]: 'close'

			},

			[STRATEGY_TIMELIFE]: {
				[EDIT_NAME]: lang(STRATEGY_TIMELIFE),
				[EDIT_TYPE]: 'number',
				[EDIT_DES]: 'The time before the Pending order is cancle in minutes',
				[EDIT_DEFAULT]: 6

			},
			[STRATEGY_INTERVAL]: {
				[EDIT_NAME]: lang(STRATEGY_INTERVAL),
				[EDIT_TYPE]: 'number',
				[EDIT_DES]: 'Interval between 2 Orders in minutes',
				[EDIT_DEFAULT]: 0

			},
			[STRATEGY_MARGIN]: {
				[EDIT_NAME]: lang(STRATEGY_MARGIN),
				[EDIT_TYPE]: 'number',

			},
			[STRATEGY_USER]: {
				[EDIT_NAME]: lang(STRATEGY_USER),
				[EDIT_TYPE]: 'select',

			},
			[STRATEGY_NOTE]: {
				[EDIT_NAME]: lang(STRATEGY_NOTE),
				[EDIT_TYPE]: 'editor',

			},


		}

		this.strategies_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData} onClick={()=>{
						if(rowData[STRATEGY_CONTAINER] == 1){
							this.containerEditModal.loadData(rowData);
							this.containerEditModal.setOptionUser(this.table.mapping[STRATEGY_USER])
						 	this.containerEditModal.modal();
						}else{
							this.editModal.loadData(rowData);
						 	this.editModal.modal();
						}
					}} />
				</div>
			}
		};
		this.strategies_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: STRATEGIES_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {
				[STRATEGY_CONTENT]: true,
				[STRATEGY_TAKEPROFIT]: true,
				[STRATEGY_STOPLOSS]: true,
				[STRATEGY_BASEPROFIT]: true,
				[STRATEGY_STEPPROFIT]: true,
				[STRATEGY_BACKPROFIT]: true,
				[STRATEGY_BASEPROFIT_BASEON]: true,
			},
			[DATA_PERMIT_COL]: this.permissionStrategiesView(),
			[DATA_KEY]: [STRATEGY_ID],
			[DATA_SORT]: { [STRATEGY_ID]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Strategies()

		};


	}

	permissionStrategiesView() {
		return Object.assign(
			...Object.keys(this.strategies_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.strategies_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
			{ [STRATEGY_USER]: App.user[AUTHEN_GROUP] == 0 ? 'Write' : 'Read' }
		)
	}

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.strategies_struct} autoload={true}>
					<FuncBar
						left={<FuncHideCol />}
						right={<>
						<div className='button' onClick={()=>{
							this.containerEditModal.loadData({});
							this.containerEditModal.setOptionUser(this.table.mapping[STRATEGY_USER])
							this.containerEditModal.modal();
						}}><i className="fa fa-cubes"></i>&nbsp;Container</div>
						<FuncAdd /><FuncClone/> <FuncDel /><FuncEdit></FuncEdit><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-striped table-resizable'></MainTable>
					<Pagination></Pagination>

					<FuncEditModal ref={c => this.editModal = c} extraFunction={<div className='button btn btn-warning' onClick={() => {
						var model = new Strategies();
						var rowData = this.editModal.form.getValue();

						if (rowData == null) return;

						for (let i in rowData) {

							if (this.editModal.permitCol[i] == 'Read') {
								delete (rowData[i]);
							}
						}

						const { key, value } = this.table.createKey(this.editModal.rowData);

						var data_key = value;
						var data_edit = rowData;

						model.edit(data_key, data_edit, true, { apply: 1 }).then(res => {
							if (res) {
								if (this.table.loadOrigin) {
									this.table.loadOrigin();
								} else {
									this.table.filter();
								}
								this.editModal.modal('hide');
							}
						})

					}}>Save and Apply</div>} />

				</Table>

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

				<ContainerEditModal ref={c => this.containerEditModal = c} onClickHandle={()=>{this.table.filter()}}></ContainerEditModal>

			</div>
		);
	}
}

export default StrategiesView
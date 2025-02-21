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

import Lab_candle_1m from '../../model/admin/Lab_candle_1m'

class ShowDbModal extends Component {

	constructor(props) {
		super(props);
		this.id = makeId();


		this.state = {
			db : '',
			remote_server: 'local'
		}

		this.show_db_struct = {};
		this.show_db_struct[STRUCT_FILTERS] = {}
		this.show_db_struct[STRUCT_COLUMNS] = {

			'symbol': {
				[COL_NAME]: lang( 'symbol'),
				[COL_SORT]: true,
			},
			'startTime': {
				[COL_NAME]: lang( 'Start Time'),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},
			'endTime': {
				[COL_NAME]: lang( 'End Time'),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},

			
		}

		this.show_db_struct[STRUCT_EDIT] = {


		}

		this.show_db_struct[STRUCT_FILTERS] = {

			
			'symbol': {
				[EDIT_NAME]: lang('symbol'),
				[EDIT_TYPE]: 'text',

			},
			'startTime': {
				[FILTER_NAME]: lang('startTime'),
				[FILTER_TYPE]: 'date',
				[FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },
			},
			'endTime': {
				[FILTER_NAME]: lang('endTime'),
				[FILTER_TYPE]: 'date',
				[FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },
			},

		}
	

		this.show_db_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: '1sss222',
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionAccountDetailView(),
			[DATA_KEY]: [],
			[DATA_SORT]: {},
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: false,
			[FLAG_SETTING_ROWS]: false,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,



		};
	}
	
	permissionAccountDetailView() {
        return Object.assign(
            ...Object.keys(this.show_db_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
            ...Object.keys(this.show_db_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
        )
    }


	async setData(data){
		var Model = new Lab_candle_1m();
		var result = await Model.showdb(data);
		this.setState({
			db : data['control_lab_db'],			
			remote_server : data['remote_server']
		});
		this.loadOrigin(Object.values(result.data));

	}

	async loadOrigin(data) {

		 this.table.setOrigin(data);
	}

	modal(cmd = 'show') {
		if (cmd == 'hide') {
			$("#bladeModal" + this.id).modal('hide');
		} else {
			$("#bladeModal" + this.id).modal();
		}
	}


	render() {

		return (
			<>
				<div className="modal fade" id={"bladeModal" + this.id}>
					<div className="modal-dialog modal-lg modal-dialog-centered" style={{ maxWidth: '75%' }}>
						<div className="modal-content">

						<div className="modal-header">
                            <h4 className="modal-title">{this.state.db}</h4>
                            <button type="button" className="close" data-dismiss="modal">&times;</button>
                        </div>

							<div  className="modal-body" style={{ textAlign: 'initial' }}>

							
							<Table ref={c => this.table = c} table={this.show_db_struct} autoload={false} loadOrigin={this.loadOrigin.bind(this)}>
									<FuncBar
										left={<>
											<div className='box_flex'>
												<FuncHideCol />
											</div>
										</>}
										right={<><FuncClear></FuncClear><FuncRefresh /><FuncExport /></>}></FuncBar>
									<MainTable className='table table-bordered table-striped table-resizable' minHeight={0}></MainTable>
									<Pagination></Pagination>

								</Table>
							

							</div>

							<div className="modal-footer">
								<button type="button" className="btn btn-danger" data-dismiss="modal">Close</button>
							</div>

						</div>
					</div>
				</div>

			</>
		)
	}




}
export default ShowDbModal
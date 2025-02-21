import React, { Component } from 'react'



import Table from '../../table/TableStatic'
import MainTable from '../../table/MainTable'
import Pagination from '../../table/Pagination'
import FuncBar from '../../table/FuncBar'

import FuncEditRow from '../../table/FuncEditRow'
import FuncAdd from '../../table/FuncAdd'
import FuncHideCol from '../../table/FuncHideCol'
import FuncDel from '../../table/FuncDel'
import FuncClear from '../../table/FuncClear'
import FuncRefresh from '../../table/FuncRefresh'
import FuncExport from '../../table/FuncExport'

import Lab_campaigns from '../../../model/admin/Lab_campaigns'

class CampaignModal extends Component {

	constructor(props) {
		super(props);
		this.id = makeId();


		this.show_db_struct = {};
		this.show_db_struct[STRUCT_FILTERS] = {}
		this.show_db_struct[STRUCT_COLUMNS] = {

			[LAB_CAMPAIGN_NAME]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_NAME),
				[COL_SORT]: true,

			},
			[LAB_CAMPAIGN_SYMBOL]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_SYMBOL),
				[COL_SORT]: true,
		
			},
			[LAB_CAMPAIGN_ACCOUNT]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_ACCOUNT),
				[COL_SORT]: true,

			},
			
			[LAB_CAMPAIGN_PRIORITY]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_PRIORITY),
				[COL_SORT]: true,

			},
			
			[LAB_CAMPAIGN_START]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_START),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},
			[LAB_CAMPAIGN_STOP]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_STOP),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},

			[LAB_CAMPAIGN_RUNTIME]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_RUNTIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap', fontWeight:'bold' }
			},

			[LAB_CAMPAIGN_STATUS]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_STATUS),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {

					var rowData = data[rowId];
					var data = rowData[colId];
					var id = rowData[LAB_CAMPAIGN_ID];
					var running = rowData[LAB_CAMPAIGN_RUNNING];
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

						{/* {running
							? <i className="button fa fa-times-circle" style={{ color: 'red', marginLeft: 5 }} onClick={() => this.killSimulate(id)}></i>
							: <i className="button fa fa-play-circle" style={{ color: 'green', marginLeft: 5 }} onClick={() => this.simulate(id)}></i>
						} */}


					</div>
				},
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},

			[LAB_CAMPAIGN_STRATEGY]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_STRATEGY),
				[COL_SORT]: true,
			},

			[LAB_CAMPAIGN_SIDE]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_SIDE),
				[COL_SORT]: true,
			},
			[LAB_CAMPAIGN_BUDGET]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_BUDGET),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => Number(data).toFixed(3),
			
			},
			[LAB_CAMPAIGN_MONEY]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_MONEY),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => Number(data).toFixed(3),
			
			},
			[LAB_CAMPAIGN_ACTIVE_BUDGET]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_ACTIVE_BUDGET),
				[COL_SORT]: true,

			},
	
			[LAB_CAMPAIGN_COMPOUND]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_COMPOUND),
				[COL_SORT]: true,
			},
		
			[LAB_CAMPAIGN_PARAMS]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_PARAMS),
				[COL_SORT]: false,
				[COL_DECORATOR_IN]: data => {
					var configs = JSON.parse(data);
					if (isset(configs)) {
						configs = Object.keys(configs).map((key) => {
							return <div key={key} className="box_flex">
								<div className="box_line" style={{ flex: 2 }}>{lang(key)}</div>
								<div>:&nbsp;</div>
								<div className="box_line" style={{ flex: 1 }}>{configs[key]}</div>
							</div>
						});
					} else {
						configs = '';
					}
					return <div>{configs}</div>
				}

			},

			[LAB_CAMPAIGN_LAST]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_LAST),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},
			[LAB_CAMPAIGN_LOG]: {
				[COL_NAME]: lang(LAB_CAMPAIGN_LOG),
				[COL_SORT]: true,
				
			},
		


		}

		this.show_db_struct[STRUCT_EDIT] = {


		}

		this.show_db_struct[STRUCT_FILTERS] = {



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




	async loadOrigin(row) {
		var data = JSON.parse(row);

		var CampaignModal = new Lab_campaigns();
		var campaignMapping = await CampaignModal.map();
		this.table.setMapping(campaignMapping['data']);
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
					<div className="modal-dialog modal-lg modal-dialog-centered" style={{ maxWidth: '98%' }}>
						<div className="modal-content">

							<div className="modal-header">
								<h4 className="modal-title">Campaign</h4>
								<button type="button" className="close" data-dismiss="modal">&times;</button>
							</div>

							<div className="modal-body" style={{ textAlign: 'initial' }}>


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
export default CampaignModal
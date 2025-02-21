import React, { Component } from 'react'
import Table from '../../components/table/Table'
import FilterBar from '../../components/table/FilterBar'
import MainTable from '../../components/table/MainTable'
import Pagination from '../../components/table/Pagination'
import FuncBar from '../../components/table/FuncBar'

import FuncEdit from '../../components/table/FuncEdit'
import FuncRelation from '../../components/table/FuncRelation'
import FuncRelationModal from '../../components/table/FuncRelationModal'
import FuncAdd from '../../components/table/FuncAdd'
import FuncHideCol from '../../components/table/FuncHideCol'
import FuncDel from '../../components/table/FuncDel'
import FuncClear from '../../components/table/FuncClear'
import FuncRefresh from '../../components/table/FuncRefresh'
import FuncExport from '../../components/table/FuncExport'
import AuthenModel from '../../model/auth/AuthenModel'
import FuncEditRow from '../../components/table/FuncEditRow'
import FilesManager from '../../components/input/FilesManager'


class Users extends Component {

	constructor(props) {
		super(props);

		this.state = {
			groups: {},
		}

		this.userTb = {};
		this.userTb[STRUCT_FILTERS] = {}
		this.userTb[STRUCT_COLUMNS] = {

			[AUTHEN_ID]: {
				[COL_NAME]: lang(AUTHEN_ID),
				[COL_SORT]: true,
			},
			[AUTHEN_USERNAME]: {
				[COL_NAME]: lang(AUTHEN_USERNAME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => {
					return <b >{data}</b>
				}
			},

			[AUTHEN_GROUP]: {
				[COL_NAME]: lang(AUTHEN_GROUP),
				[COL_SORT]: true,
			},

			[AUTHEN_ACTIVE]: {
				[COL_NAME]: lang(AUTHEN_ACTIVE),
				[COL_SORT]: true,
				[COL_STYLE]: { whiteSpace: 'nowrap' },
			},
			[AUTHEN_STATUS]: {
				[COL_NAME]: lang(AUTHEN_STATUS),
				[COL_SORT]: true,
				[COL_STYLE]: { whiteSpace: 'nowrap' },
			},
			[AUTHEN_TIME]: {
				[COL_NAME]: lang(AUTHEN_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: function (data) { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap', textAlign: 'center' }
			},
			[AUTHEN_ONLINE]: {
				[COL_NAME]: lang(AUTHEN_ONLINE),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {
					var current = moment().format('X');
					var inteval = Number(current) - Number(data);
					var online = moment(data, 'X').format(DATE_FORMAT);
					if (online == 'Invalid date') online = '';
					if (inteval < 600) {
						return <span style={{ textAlign: 'left' }}><i title={'Online: ' + online} className="fa fa-circle" style={{ color: 'green', cursor: 'pointer' }}></i>&nbsp;{online}</span>
					} else {

						return <span style={{ textAlign: 'left' }}><i title={'Offline: ' + online} className="fa fa-circle" style={{ color: 'red', cursor: 'pointer' }}></i>&nbsp;{online}</span>
					}
				},
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},


			[AUTHEN_EMAIL]: {
				[COL_NAME]: lang(AUTHEN_EMAIL),
				[COL_SORT]: true,
			},

			[AUTHEN_PHONE]: {
				[COL_NAME]: lang(AUTHEN_PHONE),
				[COL_SORT]: true,
			},

			[AUTHEN_IMG]: {
				[COL_NAME]: lang(AUTHEN_IMG),
				[COL_SORT]: false,
				[COL_DECORATOR_IN]: (data) => { if (data != null) return <img width='100px' src={'/auth/authentication/uploader_read?file=' + data}></img> }
			},



		}
		this.userTb[STRUCT_FILTERS] = {
			[AUTHEN_USERNAME]: {
				[FILTER_NAME]: lang(AUTHEN_USERNAME),
				[FILTER_TYPE]: 'text',

			},

			[AUTHEN_EMAIL]: {
				[FILTER_NAME]: lang(AUTHEN_EMAIL),
				[FILTER_TYPE]: 'text',
			},

			[AUTHEN_PHONE]: {
				[FILTER_NAME]: lang(AUTHEN_PHONE),
				[FILTER_TYPE]: 'text',
			},

			[AUTHEN_TIME]: {
				[FILTER_NAME]: lang(AUTHEN_TIME),
				[FILTER_TYPE]: 'date',
			},
			[AUTHEN_ONLINE]: {
				[FILTER_NAME]: lang(AUTHEN_ONLINE),
				[FILTER_TYPE]: 'date',
			},
			[AUTHEN_GROUP]: {
				[FILTER_NAME]: lang(AUTHEN_GROUP),
				[FILTER_TYPE]: 'select',
			},
			[AUTHEN_ACTIVE]: {
				[FILTER_NAME]: lang(AUTHEN_ACTIVE),
				[FILTER_TYPE]: 'select',
			},
			[AUTHEN_STATUS]: {
				[FILTER_NAME]: lang(AUTHEN_STATUS),
				[FILTER_TYPE]: 'select',
			},
		}

		this.userTb[STRUCT_EDIT] = {
			[AUTHEN_USERNAME]: {
				[EDIT_NAME]: lang(AUTHEN_USERNAME),
				[EDIT_TYPE]: 'text',
			},

			[AUTHEN_IMG]: {
				[EDIT_NAME]: lang(AUTHEN_IMG),
				[EDIT_TYPE]: 'image',
				[EDIT_EXTEND]: {
					fileManager: () => this.fileManager
				}
			},

			[AUTHEN_EMAIL]: {
				[EDIT_NAME]: lang(AUTHEN_EMAIL),
				[EDIT_TYPE]: 'text',
			},

			[AUTHEN_PHONE]: {
				[EDIT_NAME]: lang(AUTHEN_PHONE),
				[EDIT_TYPE]: 'text',
			},

			[AUTHEN_GROUP]: {
				[EDIT_NAME]: lang(AUTHEN_GROUP),
				[EDIT_TYPE]: 'select',
			},

			[AUTHEN_ACTIVE]: {
				[EDIT_NAME]: lang(AUTHEN_ACTIVE),
				[EDIT_TYPE]: 'select',
			},

			[AUTHEN_STATUS]: {
				[EDIT_NAME]: lang(AUTHEN_STATUS),
				[EDIT_TYPE]: 'select',
			},

			[AUTHEN_PASS]: {
				[EDIT_NAME]: lang(AUTHEN_PASS),
				[EDIT_TYPE]: 'password',
				[EDIT_DECORATOR_IN]: function (data) { return ""; },
				[EDIT_DECORATOR_OUT]: function (data) { if (data != "") return btoa(data); else return "" }
			},

		}


		this.userTb[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: AUTHENTICATION_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionAuthentication(),
			[DATA_KEY]: [AUTHEN_ID],
			[DATA_SORT]: { [AUTHEN_ONLINE]: 'desc' },
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,
			model: new AuthenModel()
		};



		//================================



		this.userTb[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex'>
					<FuncEditRow key={1} rowData={rowData} />
				</div>
			}
		};

	}

	permissionAuthentication() {
		return Object.assign(
			...Object.keys(this.userTb[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.userTb[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	componentDidMount() {

	}


	render() {
		return (
			<div>
				<Table table={this.userTb} autoload={true}>

					<FuncBar
						left={<FuncHideCol />}
						right={<><FuncAdd /><FuncDel /><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-striped table-resizable'></MainTable>
					<Pagination></Pagination>
					{/* <FuncRelationModal id='map_group_modal' relate_table={this.groupTb} map_table={this.mapTb} button='Save' relation={[AUTHEN_ID, MAP_UG_PEOPLEID, MAP_UG_GROUPID, GROUP_ID]} /> */}
				</Table>

				<FilesManager ref={c => this.fileManager = c} column={AUTHEN_IMG} links={{
					get: { method: 'GET', link: '/auth/authentication/uploader_get' },
					read: { method: 'GET', link: '/auth/authentication/uploader_read' },
					upload: { method: 'POST', link: '/auth/authentication/uploader_upload' },
					delete: { method: 'POST', link: '/auth/authentication/uploader_delete' },
				}}></FilesManager>

			


			</div>
		);
	}
}

export default Users
import React, { Component } from 'react'
import Table from '../../components/table/Table'
import FilterBar from '../../components/table/FilterBar'
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
import Config from '../../components/mailer/Config'
import Mailer_configModel from '../../model/mailer/Mailer_configModel'


class Mailer extends Component {

	constructor(props) {
		super(props);

		this.mailer_struct = {};
		this.mailer_struct[STRUCT_FILTERS] = {}
		this.mailer_struct[STRUCT_COLUMNS] = {

			// [MAIL_MAILER]:{
			//             [COL_NAME]: lang(MAIL_MAILER),
			//             [COL_SORT]: true,
			//         },
			[MAIL_NAME]: {
				[COL_NAME]: lang(MAIL_NAME),
				[COL_SORT]: true,

			},
			[MAIL_CONFIG]: {
				[COL_NAME]: lang(MAIL_CONFIG),
				[COL_SORT]: false,
				[COL_DECORATOR_IN]: data => {
					var configs = JSON.parse(data);
					if (isset(configs)) {
						configs = Object.keys(configs).map((key) => {
							return <div key={key} className="box_flex">
								<div className="box_line" style={{ flex: 1 }}>{key}</div>
								<div>:&nbsp;</div>
								<div title={configs[key]} className="box_line" style={{ flex: 2 }}>{configs[key]}</div>
							</div>
						});
					} else {
						configs = '';
					}
					return <div>{configs}</div>
				}
			},
			[MAIL_WEIGHT]: {
				[COL_NAME]: lang(MAIL_WEIGHT),
				[COL_SORT]: true,

			},
			[MAIL_USED]: {
				[COL_NAME]: lang(MAIL_USED),
				[COL_SORT]: true,

			},
			[MAIL_FREE]: {
				[COL_NAME]: lang(MAIL_FREE),
				[COL_SORT]: true,

			},
			[MAIL_LIMIT]: {
				[COL_NAME]: lang(MAIL_LIMIT),
				[COL_SORT]: true,

			},
			[MAIL_TARGET]: {
				[COL_NAME]: lang(MAIL_TARGET),
				[COL_SORT]: true,

			},
			[MAIL_ACTIVE]: {
				[COL_NAME]: lang(MAIL_ACTIVE),
				[COL_SORT]: true,

			},



		}
		this.mailer_struct[STRUCT_FILTERS] = {

			// [MAIL_MAILER]:{
			//  	[FILTER_NAME]: lang(MAIL_MAILER),
			//  	[FILTER_TYPE]:'text',
			// },
			[MAIL_NAME]: {
				[FILTER_NAME]: lang(MAIL_NAME),
				[FILTER_TYPE]: 'text',
			},
			[MAIL_WEIGHT]: {
				[FILTER_NAME]: lang(MAIL_WEIGHT),
				[FILTER_TYPE]: 'text',
			},
			[MAIL_USED]: {
				[FILTER_NAME]: lang(MAIL_USED),
				[FILTER_TYPE]: 'text',
			},
			[MAIL_FREE]: {
				[FILTER_NAME]: lang(MAIL_FREE),
				[FILTER_TYPE]: 'text',
			},
			[MAIL_LIMIT]: {
				[FILTER_NAME]: lang(MAIL_LIMIT),
				[FILTER_TYPE]: 'text',
			},
			[MAIL_TARGET]: {
				[FILTER_NAME]: lang(MAIL_TARGET),
				[FILTER_TYPE]: 'text',
			},
			[MAIL_ACTIVE]: {
				[FILTER_NAME]: lang(MAIL_ACTIVE),
				[FILTER_TYPE]: 'select',
			},


		}

		this.mailer_struct[STRUCT_EDIT] = {

			// [MAIL_MAILER]:{
			//  	[EDIT_NAME]: lang(MAIL_MAILER),
			//  	[EDIT_TYPE]:'text',
			// },
			[MAIL_NAME]: {
				[EDIT_NAME]: lang(MAIL_NAME),
				[EDIT_TYPE]: 'text',
			},
			// [MAIL_CONFIG]: {
			// 	[EDIT_NAME]: lang(MAIL_CONFIG),
			// 	[EDIT_TYPE]: 'textarea',
			// },
			[MAIL_WEIGHT]: {
				[EDIT_NAME]: lang(MAIL_WEIGHT),
				[EDIT_TYPE]: 'Number',
			},
			[MAIL_USED]: {
				[EDIT_NAME]: lang(MAIL_USED),
				[EDIT_TYPE]: 'Number',
			},
			[MAIL_FREE]: {
				[EDIT_NAME]: lang(MAIL_FREE),
				[EDIT_TYPE]: 'Number',
			},
			[MAIL_LIMIT]: {
				[EDIT_NAME]: lang(MAIL_LIMIT),
				[EDIT_TYPE]: 'Number',
			},
			[MAIL_TARGET]: {
				[EDIT_NAME]: lang(MAIL_TARGET),
				[EDIT_TYPE]: 'Number',
			},
			[MAIL_ACTIVE]: {
				[EDIT_NAME]: lang(MAIL_ACTIVE),
				[EDIT_TYPE]: 'select',
			},


		}

		this.mailer_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return [
					<FuncEditRow key={1} rowData={rowData} />,
					<div title="Configure" className="button" onClick={() => { this.config.loadData(rowData); this.config.modal() }} key={3}><i className="fa fa-cog"></i></div>,
				]
			}
		};
		this.mailer_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: MAILER_CONFIG_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionMailer(),
			[DATA_KEY]: [MAIL_ID],
			[DATA_SORT]: { [MAIL_ID]: 'desc' },
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,
			model : new Mailer_configModel()

		};


	}

	permissionMailer() {
		return Object.assign(
			...Object.keys(this.mailer_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.mailer_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	render() {
		return (
			<div>
				<Table table={this.mailer_struct} autoload={true}>
					<FuncBar
						left={<FuncHideCol />}
						right={<><FuncAdd /><FuncDel /><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-resizable'></MainTable>
					<Pagination></Pagination>
					<Config ref={config => this.config = config} />
				</Table>
			</div>
		);
	}
}

export default Mailer
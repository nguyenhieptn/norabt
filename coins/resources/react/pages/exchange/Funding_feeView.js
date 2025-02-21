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

import Funding_fee from '../../model/admin/Funding_fee'

class Funding_feeView extends Component {

	constructor(props) {
		super(props);

		this.funding_fee_struct = {};
		this.funding_fee_struct[STRUCT_FILTERS] = {}
		this.funding_fee_struct[STRUCT_COLUMNS] = {

			[FUNDING_FEE_ACCOUNT]: {
				[COL_NAME]: lang(FUNDING_FEE_ACCOUNT),
				[COL_SORT]: true,

			},
			[FUNDING_FEE_SYMBOL]: {
				[COL_NAME]: lang(FUNDING_FEE_SYMBOL),
				[COL_SORT]: true,

			},
			[FUNDING_FEE_INCOME]: {
				[COL_NAME]: lang(FUNDING_FEE_INCOME),
				[COL_SORT]: true,
				[COL_SUM]: true,

			},
			[FUNDING_FEE_TIME]: {
				[COL_NAME]: lang(FUNDING_FEE_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},



		}
		this.funding_fee_struct[STRUCT_FILTERS] = {

			[FUNDING_FEE_ACCOUNT]: {
				[FILTER_NAME]: lang(FUNDING_FEE_ACCOUNT),
				[FILTER_TYPE]: 'select',
			},
			[FUNDING_FEE_SYMBOL]: {
				[FILTER_NAME]: lang(FUNDING_FEE_SYMBOL),
				[FILTER_TYPE]: 'select',
			},
			[FUNDING_FEE_TIME]: {
				[FILTER_NAME]: lang(FUNDING_FEE_TIME),
				[FILTER_TYPE]: 'date',
				[FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },
			},


		}

		this.funding_fee_struct[STRUCT_EDIT] = {

			[FUNDING_FEE_ACCOUNT]: {
				[EDIT_NAME]: lang(FUNDING_FEE_ACCOUNT),
				[EDIT_TYPE]: 'Number',

			},
			[FUNDING_FEE_SYMBOL]: {
				[EDIT_NAME]: lang(FUNDING_FEE_SYMBOL),
				[EDIT_TYPE]: 'text',

			},
			[FUNDING_FEE_INCOME]: {
				[EDIT_NAME]: lang(FUNDING_FEE_INCOME),
				[EDIT_TYPE]: 'Number',

			},
			[FUNDING_FEE_TIME]: {
				[EDIT_NAME]: lang(FUNDING_FEE_TIME),
				[EDIT_TYPE]: 'date',

			},


		}

		this.funding_fee_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData} />
				</div>
			}
		};
		this.funding_fee_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: FUNDING_FEE_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionFunding_feeView(),
			[DATA_KEY]: [FUNDING_FEE_ID],
			[DATA_SORT]: { [FUNDING_FEE_ID]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: false,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Funding_fee()

		};


	}

	permissionFunding_feeView() {
		return Object.assign(
			...Object.keys(this.funding_fee_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.funding_fee_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.funding_fee_struct} autoload={false}>
					<FuncBar
						left={<FuncHideCol />}
						right={<><FuncAdd /><FuncDel /><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-striped table-resizable'></MainTable>
					<Pagination></Pagination>

				</Table>


			</div>
		);
	}

	componentDidMount() {
	
		this.table.setFilter({
			[FUNDING_FEE_ACCOUNT]: {
				"logic": "and",
				"data": {
					"=": App.accountSelector.selected()
				}
			}
		});
		this.table.map()
		this.table.filter()
	
	
		if (App.accountSelector) {
			App.accountSelector.register('funding_fee_view', () => {
				this.table.map();
				this.table.setFilter({
					[FUNDING_FEE_ACCOUNT]: {
						"logic": "and",
						"data": {
							"=": App.accountSelector.selected()
						}
					}
				});
				this.table.filter()
			});
		}
	}

	componentWillUnmount(){
		App.accountSelector.unregister('funding_fee_view')
	}
}

export default Funding_feeView
import React, { Component } from 'react'
import Table from '../table/Table'
import MainTable from '../table/MainTable'
import Pagination from '../table/Pagination'
import FuncBar from '../table/FuncBar'

import FuncEditRow from '../table/FuncEditRow'
import FuncAdd from '../table/FuncAdd'
import FuncHideCol from '../table/FuncHideCol'
import FuncDel from '../table/FuncDel'
import FuncClear from '../table/FuncClear'
import FuncRefresh from '../table/FuncRefresh'
import FuncExport from '../table/FuncExport'

import Orders from '../../model/admin/Orders'

class OrderModal extends Component {

    constructor(props) {
        super(props);

        this.orders_struct = {};
        this.orders_struct[STRUCT_FILTERS] = {}
        this.orders_struct[STRUCT_COLUMNS] = {

            [ORDER_BINANCE]: {
                [COL_NAME]: lang(ORDER_BINANCE),
                [COL_SORT]: true,

            },
            [ORDER_ACCOUNT]: {
                [COL_NAME]: lang(ORDER_ACCOUNT),
                [COL_SORT]: true,

            },
            [ORDER_TIME]: {
                [COL_NAME]: lang(ORDER_TIME),
                [COL_SORT]: true,
                // [COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' },

                [COL_DECORATOR_IN]: (colId, rowId, data) => {

					var rowData = data[rowId];
					var data = rowData[colId];
					if (!data) return '';
					return <div style={{ cursor: 'pointer' }} onClick={() => {
                        this.props.onSelectTime 
                        ? this.props.onSelectTime(rowData[ORDER_SYMBOL], (Math.floor(rowData[ORDER_TIME] / 1000) - 300) * 1000, (Math.floor(rowData[ORDER_TIME] / 1000) + 3000) * 1000)
                        : window.open(App.link('/admin/dashboard/view?symbol=' + rowData[ORDER_SYMBOL]) + "&start=" + (Math.floor(rowData[ORDER_TIME] / 1000) - 300) * 1000 + "&stop=" + (Math.floor(rowData[ORDER_TIME] / 1000) + 3000) * 1000, '_blank');
                    }}><b>{moment(data, 'x').format(DATE_FORMAT)}</b></div>
				}

            },
            [ORDER_SYMBOL]: {
                [COL_NAME]: lang(ORDER_SYMBOL),
                [COL_SORT]: true,

            },

            [ORDER_TYPE]: {
                [COL_NAME]: lang(ORDER_TYPE),
                [COL_SORT]: true,

            },
            [ORDER_SIDE]: {
                [COL_NAME]: lang(ORDER_SIDE),
                [COL_SORT]: true,

            },
            [ORDER_PRICE]: {
                [COL_NAME]: lang(ORDER_PRICE),
                [COL_SORT]: true,

            },
            [ORDER_STOP_PRICE]: {
                [COL_NAME]: lang(ORDER_STOP_PRICE),
                [COL_SORT]: true,

            },
            [ORDER_STATUS]: {
                [COL_NAME]: lang(ORDER_STATUS),
                [COL_SORT]: true,

            },
            [ORDER_QTY]: {
                [COL_NAME]: lang(ORDER_QTY),
                [COL_SORT]: true,

            },
            [ORDER_PNL]: {
                [COL_NAME]: lang(ORDER_PNL),
                [COL_SORT]: true,
                [COL_SUM]: true

            },
            [ORDER_COMMIT]: {
                [COL_NAME]: lang(ORDER_COMMIT),
                [COL_SORT]: true,
                [COL_SUM]: true

            },
            [ORDER_DATA]: {
                [COL_NAME]: lang(ORDER_DATA),
                [COL_SORT]: false,

            },



        }
        this.orders_struct[STRUCT_FILTERS] = {


            [ORDER_BINANCE]: {
                [FILTER_NAME]: lang(ORDER_BINANCE),
                [FILTER_TYPE]: 'text',
            },
            [ORDER_ACCOUNT]: {
                [FILTER_NAME]: lang(ORDER_ACCOUNT),
                [FILTER_TYPE]: 'select',
            },
            [ORDER_TIME]: {
                [FILTER_NAME]: lang(ORDER_TIME),
                [FILTER_TYPE]: 'date',
               
            },
            [ORDER_SYMBOL]: {
                [FILTER_NAME]: lang(ORDER_SYMBOL),
                [FILTER_TYPE]: 'text',
            },

            [ORDER_TYPE]: {
                [FILTER_NAME]: lang(ORDER_TYPE),
                [FILTER_TYPE]: 'select',
            },
            [ORDER_SIDE]: {
                [FILTER_NAME]: lang(ORDER_SIDE),
                [FILTER_TYPE]: 'select',
            },
            [ORDER_PRICE]: {
                [FILTER_NAME]: lang(ORDER_PRICE),
                [FILTER_TYPE]: 'text',
            },
            [ORDER_STOP_PRICE]: {
                [FILTER_NAME]: lang(ORDER_STOP_PRICE),
                [FILTER_TYPE]: 'text',
            },
            [ORDER_STATUS]: {
                [FILTER_NAME]: lang(ORDER_STATUS),
                [FILTER_TYPE]: 'select',
            },
            [ORDER_QTY]: {
                [FILTER_NAME]: lang(ORDER_QTY),
                [FILTER_TYPE]: 'text',
            },
            [ORDER_PNL]: {
                [FILTER_NAME]: lang(ORDER_PNL),
                [FILTER_TYPE]: 'text',
            },
            [ORDER_COMMIT]: {
                [FILTER_NAME]: lang(ORDER_COMMIT),
                [FILTER_TYPE]: 'text',
            },


        }

        this.orders_struct[STRUCT_EDIT] = {




        }

        this.orders_struct[STRUCT_ROWS] = {
            [ROW_FUNCS]: (rowData) => {
                return <div className='box_flex' style={{ justifyContent: 'center' }}>
                    <FuncEditRow rowData={rowData} />
                </div>
            }
        };
        this.orders_struct[STRUCT_TABLE] = {
            [DATA_TABLE_ID]: ORDERS_TABLE,
            [DATA_FILTERS]: {},
            [DATA_HIDDEN_COL]: { [ORDER_DATA]: true },
            [DATA_PERMIT_COL]: this.permissionOrdersView(),
            [DATA_KEY]: [ORDER_ID],
            [DATA_SORT]: { [ORDER_ID]: 'desc' },
            [FLAG_FILTER]: true,
            [FLAG_FILTER_CHANGE]: true,
            [FLAG_MULTI_SORT]: false,
            [FLAG_RESIZABLE]: true,
            [FLAG_SELECT_ROWS]: true,
            [FLAG_SETTING_ROWS]: false,
            [FLAG_EXPAND_ROWS]: false,
            [FLAG_HEAD_ROW]: true,

            model: new Orders()

        };


    }

    permissionOrdersView() {
        return Object.assign(
            ...Object.keys(this.orders_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
            ...Object.keys(this.orders_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
        )
    }

    modal(cmd = 'show') {
		if (cmd == 'hide') {
			$("#add_row_modal" + this.id).modal('hide');
		} else {
			$("#add_row_modal" + this.id).modal();
		}
	}

	loadData(rowData) {
		this.rowData = rowData;
		this.table[STRUCT_TABLE][DATA_SPECIAL] = {[ORDER_ACTION] : rowData[ACTION_ID]};
		this.table.filter();
        this.table.map();
	}

    render() {
        return (
            <div className="modal fade" id={"add_row_modal" + this.id} onClick={() => { addClass($('body')[0], 'modal-open') }}>
                <div className="modal-dialog modal-lg modal-dialog-centered" style={{maxWidth:'95%'}}>
                    <div className="modal-content">

                        <div className="modal-header">
                            <h4 className="modal-title">{get(this.props.title, lang("Add"))}</h4>
                            <button type="button" className="close" data-dismiss="modal">&times;</button>
                        </div>

                        <div className="modal-body">
                            <Table ref={c => this.table = c} table={this.orders_struct} autoload={false}>
                                <FuncBar
                                    left={<FuncHideCol />}
                                    right={<><FuncDel /><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
                                <MainTable className='table table-bordered table-striped table-resizable'></MainTable>
                                <Pagination></Pagination>

                            </Table>


                        </div>

                        <div className="modal-footer">
                            <button type="button" className="btn btn-danger" data-dismiss="modal">{lang('Close')}</button>
                        </div>
                    </div>
                </div>
            </div>
        );
    }
}

export default OrderModal
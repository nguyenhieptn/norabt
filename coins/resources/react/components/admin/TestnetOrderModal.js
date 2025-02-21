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

import Testnet_order from '../../model/admin/Testnet_order'

class TestnetOrderModal extends Component {

    constructor(props) {
        super(props);

        this.lab_order_struct = {};
        this.lab_order_struct[STRUCT_FILTERS] = {}
        this.lab_order_struct[STRUCT_COLUMNS] = {

            [TESTNET_ORDER_TIME]: {
                [COL_NAME]: lang(TESTNET_ORDER_TIME),
                [COL_SORT]: true,
                // [COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
                [COL_STYLE]: { whiteSpace: 'nowrap' },
                [COL_DECORATOR_IN]: (colId, rowId, data) => {

					var rowData = data[rowId];
					var data = rowData[colId];
					if(!data) return '';
					return <div style={{ cursor: 'pointer' }} onClick={() => {
						window.open(App.link('/admin/testnet/view?symbol=' + rowData[TESTNET_ORDER_SYMBOL]) + "&start=" + (Math.floor(data/1000)-300) * 1000 + "&stop=" + (Math.floor(data/1000)+3000) * 1000, '_blank');
					}}><b>{moment(data, 'x').format(DATE_FORMAT)}</b></div>
				}
            },
            [TESTNET_ORDER_ACTION]: {
                [COL_NAME]: lang(TESTNET_ORDER_ACTION),
                [COL_SORT]: true,

            },
            [TESTNET_ORDER_SYMBOL]: {
                [COL_NAME]: lang(TESTNET_ORDER_SYMBOL),
                [COL_SORT]: true,

            },
            [TESTNET_ORDER_QTY]: {
                [COL_NAME]: lang(TESTNET_ORDER_QTY),
                [COL_SORT]: true,

            },
            [TESTNET_ORDER_PRICE]: {
                [COL_NAME]: lang(TESTNET_ORDER_PRICE),
                [COL_SORT]: true,

            },
            
            [TESTNET_ORDER_TYPE]:{
                [COL_NAME]: lang(TESTNET_ORDER_TYPE),
                [COL_SORT]: true,
                
            },
            [TESTNET_ORDER_PHASE]:{
                [COL_NAME]: lang(TESTNET_ORDER_PHASE),
                [COL_SORT]: true,
                
            },
            [TESTNET_ORDER_PNL]:{
                [COL_NAME]: lang(TESTNET_ORDER_PNL),
                [COL_SORT]: true,
                [COL_SUM]: true,
                
            },
            [TESTNET_ORDER_COMMIT]:{
                [COL_NAME]: lang(TESTNET_ORDER_COMMIT),
                [COL_SORT]: true,
                [COL_SUM]: true,
                
            },



        }
        this.lab_order_struct[STRUCT_FILTERS] = {

            [TESTNET_ORDER_SYMBOL]: {
                [FILTER_NAME]: lang(TESTNET_ORDER_SYMBOL),
                [FILTER_TYPE]: 'text',
            },
            
            [TESTNET_ORDER_TYPE]: {
                [FILTER_NAME]: lang(TESTNET_ORDER_TYPE),
                [FILTER_TYPE]: 'select',
            },


        }

        this.lab_order_struct[STRUCT_EDIT] = {

            [TESTNET_ORDER_TIME]: {
                [EDIT_NAME]: lang(TESTNET_ORDER_TIME),
                [EDIT_TYPE]: 'date',

            },
            [TESTNET_ORDER_ACTION]: {
                [EDIT_NAME]: lang(TESTNET_ORDER_ACTION),
                [EDIT_TYPE]: 'Number',

            },
            [TESTNET_ORDER_SYMBOL]: {
                [EDIT_NAME]: lang(TESTNET_ORDER_SYMBOL),
                [EDIT_TYPE]: 'text',

            },
            [TESTNET_ORDER_QTY]: {
                [EDIT_NAME]: lang(TESTNET_ORDER_QTY),
                [EDIT_TYPE]: 'text',

            },
            [TESTNET_ORDER_PRICE]: {
                [EDIT_NAME]: lang(TESTNET_ORDER_PRICE),
                [EDIT_TYPE]: 'text',

            },
            [TESTNET_ORDER_BASEON]: {
                [EDIT_NAME]: lang(TESTNET_ORDER_BASEON),
                [EDIT_TYPE]: 'textarea',

            },


        }

        this.lab_order_struct[STRUCT_ROWS] = {
            [ROW_FUNCS]: (rowData) => {
                return <div className='box_flex' style={{ justifyContent: 'center' }}>
                    <FuncEditRow rowData={rowData} />
                </div>
            }
        };
        this.lab_order_struct[STRUCT_TABLE] = {
            [DATA_TABLE_ID]: TESTNET_ORDER_TABLE,
            [DATA_FILTERS]: {},
            [DATA_HIDDEN_COL]: {},
            [DATA_PERMIT_COL]: this.permissionTestnet_orderView(),
            [DATA_KEY]: [TESTNET_ORDER_ID],
            [DATA_SORT]: { [TESTNET_ORDER_TIME]: 'desc' },
            [FLAG_FILTER]: true,
            [FLAG_FILTER_CHANGE]: true,
            [FLAG_MULTI_SORT]: false,
            [FLAG_RESIZABLE]: true,
            [FLAG_SELECT_ROWS]: false,
            [FLAG_SETTING_ROWS]: false,
            [FLAG_EXPAND_ROWS]: false,
            [FLAG_HEAD_ROW]: true,

            model: new Testnet_order()

        };


    }

    permissionTestnet_orderView() {
        return Object.assign(
            ...Object.keys(this.lab_order_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
            ...Object.keys(this.lab_order_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
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
        this.table[STRUCT_TABLE][DATA_SPECIAL] = { [TESTNET_ORDER_ACTION]: rowData[TESTNET_RESULT_ID] };
        this.table.filter();
        this.table.map();

    }

    render() {
        return (
            <div className="modal fade" id={"add_row_modal" + this.id} onClick={() => { addClass($('body')[0], 'modal-open') }}>
                <div className="modal-dialog modal-lg modal-dialog-centered" style={{ maxWidth: '95%' }}>
                    <div className="modal-content">

                        <div className="modal-header">
                            <h4 className="modal-title">{get(this.props.title, lang("Add"))}</h4>
                            <button type="button" className="close" data-dismiss="modal">&times;</button>
                        </div>

                        <div className="modal-body">
                            <Table ref={c => this.table = c} table={this.lab_order_struct} autoload={false}>
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

export default TestnetOrderModal
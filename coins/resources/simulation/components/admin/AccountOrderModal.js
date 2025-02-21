import React, { Component } from 'react'
import Table from '../table/TableStatic'
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

import Lab_results from '../../model/admin/Lab_results'

class AccountOrderModal extends Component {

    constructor(props) {
        super(props);
        this.id = makeId();
        this.lab_order_struct = {};
        this.lab_order_struct[STRUCT_FILTERS] = {}
        this.lab_order_struct[STRUCT_COLUMNS] = {

            'time': {
                [COL_NAME]: 'Time',
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },

            },
            'symbol': {
                [COL_NAME]: 'Symbol',
                [COL_SORT]: true,
                [COL_STYLE]: {padding : 0},
                [COL_DECORATOR_IN]: (data) => {

                    return (
                        <table className="table table-bordered" style={{margin : 0}}>
                            <tbody>
                                {
                                    data.map(item => {
                                        return (
                                            <tr>
                                                <td style={{width : '25%'}}>{moment(item['startTime'], 'x').format(DATE_FORMAT)}</td>
                                                <td style={{width : '25%'}}>{moment(item['endTime'], 'x').format(DATE_FORMAT)}</td>
                                                <td style={{width : '20%'}}>{item['symbol']}</td>
                                                <td style={{width : '5%'}}>{item['phase']}</td>
                                                <td style={{width : '25%'}}>{item['flow']}</td>
                                            </tr>
                                        )
                                    })
                                }

                            </tbody>
                        </table>
                    )
                }

            },
            'total': {
                [COL_NAME]: 'Total',
                [COL_SORT]: true,
                // [COL_DECORATOR_IN]: (colId, rowId, data) => {
                //     var rowData = data[rowId];
                // 	var data = rowData['symbol'].length;
                //     return data
                // }

            },




        }
        this.lab_order_struct[STRUCT_FILTERS] = {

            'total': {
                [FILTER_NAME]: 'Total',
                [FILTER_TYPE]: 'number',
            },
            'time': {
                [FILTER_NAME]: 'time',
                [FILTER_TYPE]: 'date',
                [FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
                [FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },
            },

            // [LAB_ORDER_TYPE]: {
            //     [FILTER_NAME]: lang(LAB_ORDER_TYPE),
            //     [FILTER_TYPE]: 'select',
            // },


        }

        this.lab_order_struct[STRUCT_EDIT] = {




        }

        this.lab_order_struct[STRUCT_ROWS] = {
            [ROW_FUNCS]: (rowData) => {
                return <div className='box_flex' style={{ justifyContent: 'center' }}>
                    <FuncEditRow rowData={rowData} />
                </div>
            }
        };
        this.lab_order_struct[STRUCT_TABLE] = {
            [DATA_TABLE_ID]: 'Order',
            [DATA_FILTERS]: {},
            [DATA_HIDDEN_COL]: {},
            [DATA_PERMIT_COL]: this.permissionLab_orderView(),
            [DATA_KEY]: [],
            [DATA_SORT]: { 'time': 'desc' },
            [FLAG_FILTER]: true,
            [FLAG_FILTER_CHANGE]: true,
            [FLAG_MULTI_SORT]: false,
            [FLAG_RESIZABLE]: true,
            [FLAG_SELECT_ROWS]: false,
            [FLAG_SETTING_ROWS]: false,
            [FLAG_EXPAND_ROWS]: false,
            [FLAG_HEAD_ROW]: true,

            // model: new Lab_order()

        };


    }

    permissionLab_orderView() {
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

    async loadOrigin(account_id) {

        let modal = new Lab_results();

        modal.getByAccount(account_id).then(res => {
            if (res['result']) {
                res = res['data']

                let out = []


                for (let i = 0; i < res.length; i++) {
                    let startTime = Number(res[i][LAB_RESULT_CHART]);
                    let endTime = Number(res[i][LAB_RESULT_SELL_TIME]);
                    let phase = Number(res[i][LAB_RESULT_PHASE]);
                    let symbol = res[i][LAB_RESULT_SYMBOL];
                    let flow = res[i][LAB_RESULT_FLOW];

                    let outSymbol = [{
                        'startTime': startTime,
                        'endTime': endTime,
                        'symbol': symbol,
                        'phase': phase,
                        'flow': flow
                    }]

                    for (let x = i + 1; x < res.length; x++) {
                        let nextTime = Number(res[x][LAB_RESULT_CHART])
                        let nextEndTime = Number(res[x][LAB_RESULT_SELL_TIME])
                        let nextPhase = Number(res[x][LAB_RESULT_PHASE])
                        let nextFlow = res[x][LAB_RESULT_FLOW]
                        let symbolNext = res[x][LAB_RESULT_SYMBOL]

                        if (startTime > nextTime && startTime < nextEndTime) {
                            outSymbol.push({
                                'startTime': nextTime,
                                'endTime': nextEndTime,
                                'symbol': symbolNext,
                                'phase': nextPhase,
                                'flow': nextFlow
                            })
                        }
                    }
                    if (outSymbol.length != 1) {
                        out.push({
                            'time': startTime,
                            'symbol': outSymbol,
                            'total': outSymbol.length
                        })
                    }


                }

                console.log(out)
                this.table.setOrigin(out);

            }
        })



    }




    render() {
        return (
            <div className="modal fade" id={"add_row_modal" + this.id} onClick={() => { addClass($('body')[0], 'modal-open') }}>
                <div className="modal-dialog modal-lg modal-dialog-centered" style={{ maxWidth: '75%' }}>
                    <div className="modal-content">

                        <div className="modal-header">
                            <h4 className="modal-title">{get(this.props.title, lang("Add"))}</h4>
                            <button type="button" className="close" data-dismiss="modal">&times;</button>
                        </div>

                        <div className="modal-body">

                            <Table ref={c => this.table = c} table={this.lab_order_struct} autoload={false} loadOrigin={this.loadOrigin.bind(this)}>
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

export default AccountOrderModal
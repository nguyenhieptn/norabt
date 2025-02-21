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

import Lab_order from '../../model/admin/Lab_order'

class BalanceMaxModal extends Component {

    constructor(props) {
        super(props);
        this.id = makeId();
        this.lab_order_struct = {};
        this.lab_order_struct[STRUCT_FILTERS] = {}
        this.lab_order_struct[STRUCT_COLUMNS] = {

            'x': {
                [COL_NAME]: 'Time',
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },

            },
            'y': {
                [COL_NAME]: 'Value',
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => {
                    if (data == '') return data;
                    else return (data * 100).toFixed(2) + ' %';
                }


            },

            'Interval': {
                [COL_NAME]: 'Interval',
                [COL_SORT]: true,
               
                [COL_DECORATOR_IN]: (colId, rowId, data) => {
                    var rowData = data[rowId]
                    if(isset(rowData['right_x']) || isset(rowData['left_x'])){
                        var diff = Number(rowData['right_x']) - Number(rowData['left_x'])
                        diff = Math.round(diff / 1000);
     
                        var d = Math.floor(diff / (3600 * 24));
                        var h = Math.floor(diff % (3600 * 24) / 3600);
                        var m = Math.floor(diff % 3600 / 60);

                        var dDisplay = d > 0 ? d + 'd ' : "";
                        var hDisplay = h > 0 ? h + 'h ' : "";
                        var mDisplay = m > 0 ? m + 'm' : 0;
                        var color = '';
                     
                        var date = dDisplay + hDisplay + mDisplay;
                        return <b style={{ color: 'red' }}>{date}</b>;

                    }else{
                        return ''
                    }
                    
                }

            },
          
            'left_x': {
                [COL_NAME]: 'Time Left',
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },

            },
            'left_y': {
                [COL_NAME]: 'Value Left',
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => {
                    if(!data) return
                    if (data == '') return data;
                    else return (data * 100).toFixed(2) + ' %';
                }


            },

            'right_x': {
                [COL_NAME]: 'Time Right',
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },

            },
            'right_y': {
                [COL_NAME]: 'Value Right',
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => {
                    if(!data) return
                    if (data == '') return data;
                    else return (data * 100).toFixed(2) + ' %';
                }


            },

           




        }
        this.lab_order_struct[STRUCT_FILTERS] = {

            // [LAB_ORDER_SYMBOL]: {
            //     [FILTER_NAME]: lang(LAB_ORDER_SYMBOL),
            //     [FILTER_TYPE]: 'text',
            // },

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
            [DATA_TABLE_ID]: 'DD',
            [DATA_FILTERS]: {},
            [DATA_HIDDEN_COL]: {},
            [DATA_PERMIT_COL]: this.permissionLab_orderView(),
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

            model: new Lab_order()

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

    async loadOrigin() {




        this.table.setOrigin(App.dataMax);


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

export default BalanceMaxModal
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

import Max_pain from '../../model/admin/Max_pain';

class TableMaxPain extends Component {

    constructor(props) {
        super(props);
        this.id = makeId();



        this.max_pain_struct = {};
        this.max_pain_struct[STRUCT_COLUMNS] = {

            [MAX_PAIN_TIME]: {
                [COL_NAME]: 'Time',
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format("DD-MM-YYYY") },
				[COL_STYLE]: { whiteSpace: 'nowrap', textAlign: 'center' }

            },

            [MAX_PAIN_PRICE]: {
                [COL_NAME]: 'Price',
                [COL_SORT]: true,
                [COL_STYLE]: { textAlign: 'center' },
                [COL_DECORATOR_IN]: (data) => { 
                    return formatNumber(data);
                },
            },




        }
        this.max_pain_struct[STRUCT_FILTERS] = {


            // [BINANCE_ORDER_BINANCE]: {
            //     [FILTER_NAME]: lang(ORDER_BINANCE),
            //     [FILTER_TYPE]: 'text',
            // },

            // [BINANCE_ORDER_TIME]: {
            //     [FILTER_NAME]: lang(ORDER_TIME),
            //     [FILTER_TYPE]: 'date',

            // },
            // [BINANCE_ORDER_SYMBOL]: {
            //     [FILTER_NAME]: lang(ORDER_SYMBOL),
            //     [FILTER_TYPE]: 'text',
            // },


        }

        this.max_pain_struct[STRUCT_EDIT] = {




        }


        this.max_pain_struct[STRUCT_TABLE] = {
            [DATA_TABLE_ID]: '122323',
            [DATA_FILTERS]: {},
            [DATA_HIDDEN_COL]: {},
            [DATA_PERMIT_COL]: this.permissionOrdersBinanceView(),
            [DATA_KEY]: ['id'],
            [DATA_SORT]: { [MAX_PAIN_TIME] : 'desc'  },
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

    permissionOrdersBinanceView() {
        return Object.assign(
            ...Object.keys(this.max_pain_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
            ...Object.keys(this.max_pain_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
        )
    }

    componentDidMount(){
        this.loadOrigin();
    }



    async loadOrigin() {
        var MaxPain = new Max_pain();
        var maxPainData = await MaxPain.read({}, true, { orderBy: MAX_PAIN_TIME, sort: 'asc', });
       
        this.table.setOrigin(maxPainData['data']);
    }



    render() {


        return (
            <>


                <div >

                    <Table ref={c => this.table = c} table={this.max_pain_struct} autoload={false} loadOrigin={this.loadOrigin.bind(this)}>
                        <FuncBar
                            left={<>
                                <div className='box_flex'>
                                    <FuncHideCol />
                                </div>
                            </>}
                            	name={'Max Pain'}
                            right={<><FuncClear></FuncClear><FuncRefresh /><FuncExport /></>}></FuncBar>
                        <MainTable className='table table-bordered table-striped table-resizable' minHeight={0}></MainTable>
                        <Pagination></Pagination>

                    </Table>

                </div>



            </>
        )
    }





}
export default TableMaxPain
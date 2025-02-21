import React, { Component } from 'react';
import Input from '../../components/input/Input';

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
import Lab_candle_1d from '../../model/admin/Lab_candle_1d'
class Table_fluctuationView extends Component {
    constructor(props) {
        super(props);
        this.id = makeId();
        this.fluctuation_struct = {};
        this.fluctuation_struct[STRUCT_FILTERS] = {}
        this.fluctuation_struct[STRUCT_COLUMNS] = {


            'symbol': {
                [COL_NAME]: 'Symbol',
                [COL_SORT]: true,
 

            },
            'rank': {
                [COL_NAME]: 'Rank',
                [COL_SORT]: true,
             

            },

            'minTime': {
                [COL_NAME]: 'Start Time',
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },

            },
            'maxTime': {
                [COL_NAME]: 'Stop Time',
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },

            },
            'highlowavg': {
                [COL_NAME]: 'High - Low Avg',
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => {
                    if (data == '') return data;
                    return data.toFixed(3) + '%'
                },


            },
            'highhighavg': {
                [COL_NAME]: 'High - High Avg',
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => {
                    if (data == '') return data;
                    return data.toFixed(3) + '%'
                },


            },
            'lowlowavg': {
                [COL_NAME]: 'Low - Low Avg',
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => {
                    if (data == '') return data;
                    return data.toFixed(3) + '%'
                },


            },
            'max': {
                [COL_NAME]: 'Max',
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => {
                    if (data == '') return data;
                    data = Number(data)
                    return data.toFixed(3) + '%'
                },


            },
            'min': {
                [COL_NAME]: 'Min',
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => {
                    if (data == '') return data;
                    data = Number(data)
                    return data.toFixed(3) + '%'
                },


            },
          


        }
        this.fluctuation_struct[STRUCT_FILTERS] = {


            'symbol': {
                [FILTER_NAME]: 'symbol',
                [FILTER_TYPE]: 'text',
            },
            'minTime': {
                [FILTER_NAME]: 'minTime',
                [FILTER_TYPE]: 'date',
                [FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
                [FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },
            },
            'maxTime': {
                [FILTER_NAME]: 'maxTime',
                [FILTER_TYPE]: 'date',
                [FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
                [FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },
            },
           'highlowavg': {
                [FILTER_NAME]: 'highlowavg',
                [FILTER_TYPE]: 'number',
                [FILTER_LOGIC]: ['>=', '<='],
            },
           'lowlowavg': {
                [FILTER_NAME]: 'lowlowavg',
                [FILTER_TYPE]: 'number',
                [FILTER_LOGIC]: ['>=', '<='],
            },
           'highhighavg': {
                [FILTER_NAME]: 'highhighavg',
                [FILTER_TYPE]: 'number',
                [FILTER_LOGIC]: ['>=', '<='],
            },
           'max': {
                [FILTER_NAME]: 'max',
                [FILTER_TYPE]: 'number',
                [FILTER_LOGIC]: ['>=', '<='],
            },
           'min': {
                [FILTER_NAME]: 'min',
                [FILTER_TYPE]: 'number',
                [FILTER_LOGIC]: ['>=', '<='],
            },
           'rank': {
                [FILTER_NAME]: 'rank',
                [FILTER_TYPE]: 'number',
                [FILTER_LOGIC]: ['>=', '<='],
            },


        }

        this.fluctuation_struct[STRUCT_EDIT] = {




        }

        this.fluctuation_struct[STRUCT_ROWS] = {
            [ROW_FUNCS]: (rowData) => {
                return <div className='box_flex' style={{ justifyContent: 'center' }}>
                    <FuncEditRow rowData={rowData} />
                </div>
            }
        };
        this.fluctuation_struct[STRUCT_TABLE] = {
            [DATA_TABLE_ID]: 'fluctuation_table',
            [DATA_FILTERS]: {},
            [DATA_HIDDEN_COL]: {},
            [DATA_PERMIT_COL]: this.permissionLab_orderView(),
            [DATA_KEY]: [],
            [DATA_SORT]: { },
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

        this.model = new Lab_candle_1d()
    }

    permissionLab_orderView() {
        return Object.assign(
            ...Object.keys(this.fluctuation_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
            ...Object.keys(this.fluctuation_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
        )
    }

    async loadOrigin(data) {
        this.table.setOrigin(data);
    }

    loadData() {
        let data = {
            startTime: this.startInput.getValue(),
            stopTime: this.stopInput.getValue(),
            opt: this.selectedOpt.getValue(),
        }

        this.model.getFluctuation(data).then(res => {


            if (res['result']) {
                this.loadOrigin(res['data'])
            }
        })
    }


    render() {
        return (
            <div>
                <div style={{ display: 'flex' }}>
                    <Input ref={c => this.startInput = c} placeholder="Start Time" className='input' struct={{
                        [INPUT_TYPE]: 'date',

                    }}></Input>

                    &nbsp;
                    &nbsp;
                    &nbsp;

                    <Input ref={c => this.stopInput = c} placeholder="Stop Time" className='input' struct={{
                        [INPUT_TYPE]: 'date',
                    }}></Input>
                    &nbsp;
                    &nbsp;
                    &nbsp;

                    <Input ref={c => this.selectedOpt = c} className='input' struct={{
                        [INPUT_TYPE]: 'select',
                        [INPUT_DEFAULT]: '4h',
                        [INPUT_OPTION]: {
                            '4h': '4H',
                            '1d': '1D',
                        },
                    }}></Input>
                    &nbsp;
                    &nbsp;
                    &nbsp;
                    <button type="button" className="btn btn-primary" onClick={() => this.loadData()}>Load Data</button>
                </div>
                <div>
                    <Table ref={c => this.table = c} table={this.fluctuation_struct} autoload={false} loadOrigin={this.loadOrigin.bind(this)}>
                        <FuncBar
                            left={<FuncHideCol />}
                            right={<><FuncDel /><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
                        <MainTable className='table table-bordered table-striped table-resizable'></MainTable>
                        <Pagination></Pagination>

                    </Table>
                </div>
            </div>
        );
    }
}

export default Table_fluctuationView;
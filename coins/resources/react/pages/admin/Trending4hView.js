import React, { Component } from 'react';

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

import Candle_4h from '../../model/admin/Candle_4h';
import Lab_candle_4h from '../../../simulation/model/admin/Lab_candle_4h';


class Trending4hView extends Component {

    constructor(props) {
        super(props);
        this.id = makeId();
        this.table_wma_struct = {};
        this.table_wma_struct[STRUCT_FILTERS] = {}
        this.table_wma_struct[STRUCT_COLUMNS] = {

            'time': {
                [COL_NAME]: 'Time',
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
                [COL_STYLE]: { whiteSpace: 'nowrap', textAlign: 'center' }

            },
            'signal': {
                [COL_NAME]: 'Signal',
                [COL_SORT]: true,
                [COL_STYLE]: { textAlign: 'center' }

            },

            'wma_4h': {
                [COL_NAME]: 'WMA 4H',
                [COL_SORT]: true,
                [COL_STYLE]: { textAlign: 'center' }

            },
            // 'wma_1w': {
            //     [COL_NAME]: 'WMA 1W',
            //     [COL_SORT]: true,
            //     [COL_STYLE]: { textAlign: 'center' }

            // },

        }
        this.table_wma_struct[STRUCT_FILTERS] = {

            ['time']: {
				[FILTER_NAME]: lang('time'),
				[FILTER_TYPE]: 'date',
				[FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },
			},
            ['signal']: {
				[FILTER_NAME]: lang('signal'),
				[FILTER_TYPE]: 'number',
				[FILTER_LOGIC]: ['>=', '<='],
			},

            ['wma_4h']: {
                [FILTER_NAME]: lang('wma_4h'),
                [FILTER_TYPE]: 'number',
                [FILTER_LOGIC]: ['>=', '<='],
            },
        

        }


        this.table_wma_struct[STRUCT_EDIT] = {


        }

        this.table_wma_struct[STRUCT_ROWS] = {

        };
        this.table_wma_struct[STRUCT_TABLE] = {
            [DATA_TABLE_ID]: '1ass122344trending',
            [DATA_FILTERS]: {},
            [DATA_HIDDEN_COL]: {},
            [DATA_PERMIT_COL]: this.permissionTableAlertView(),
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



        };


    }
    permissionTableAlertView() {
        return Object.assign(
            ...Object.keys(this.table_wma_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
            ...Object.keys(this.table_wma_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
        )
    }
    componentDidMount() {
        this.loadOrigin();
    }
    async loadOrigin() {
        var model = new Lab_candle_4h();
        var testNetModel = new Candle_4h();

        var Candle_4hData = await model.getAll();



        var result = {};
        if (Candle_4hData['result']) {
            var datas = Candle_4hData['data'];

            for (let i = 0; i < datas.length; i++) {
                var data = datas[i];
                if (data['lab_candle_4h_rsi_wma']) {
                    var time = Number(data['lab_candle_4h_open_time']);
                    var value = Math.round(Number(data['lab_candle_4h_rsi_wma']) * 100) / 100;
                    var signal = Math.floor(Number(data['lab_candle_4h_signal']) ) ;


                    result[time] = {
                        'time': time,
                        'wma_4h': value,
                        'signal' : signal
                    }
                }


            }

            let maxTime = datas[datas.length -1]['lab_candle_4h_open_time']

            // [CANDLE_4H_SYMBOL]: 'BTCUSDT' , [CANDLE_4H_OPEN_TIME] > maxTime
       
            var TestNetCandle_4hData = await testNetModel.get([[
                [CANDLE_4H_SYMBOL, '=', 'BTCUSDT'],
                [CANDLE_4H_OPEN_TIME, '>', maxTime]
            ]]);
            if (TestNetCandle_4hData['result']) {
                var datas = TestNetCandle_4hData['data'];
    
                for (let i = 0; i < datas.length; i++) {
                    var data = datas[i];
                    if (data[CANDLE_4H_RSI_WMA]) {
                        var time = Number(data[CANDLE_4H_OPEN_TIME]);
                        var value = Math.round(Number(data[CANDLE_4H_RSI_WMA]) * 100) / 100;
                        var signal = Math.floor(Number(data[CANDLE_4H_SIGNAL]) ) ;
    
    
                        result[time] = {
                            'time': time,
                            'wma_4h': value,
                            'signal' : signal
                        }
                    }
    
    
                }
    
    
            }



        }



   


        

        this.table.setOrigin(Object.values(result));

    }
    render() {
        return (
            <div>
                <Table ref={c => this.table = c} table={this.table_wma_struct} autoload={false} loadOrigin={this.loadOrigin.bind(this)}>
                    <FuncBar
                        left={<>
                            <div className='box_flex'>
                                <FuncHideCol />
                            </div>
                        </>}
                        right={<>
                            <FuncClear></FuncClear><FuncRefresh /><FuncExport /></>}></FuncBar>
                    <MainTable className='table table-bordered table-striped table-resizable' minHeight={0}></MainTable>
                    <Pagination></Pagination>

                </Table>
            </div>
        );
    }
}

export default Trending4hView;
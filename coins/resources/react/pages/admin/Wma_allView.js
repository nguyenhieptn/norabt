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

import Candle_1d from '../../model/admin/Candle_1d';
import candle_1w from '../../model/admin/Candle_1w';
import Wma_45 from '../../model/admin/Wma_45';

class Wma_allView extends Component {

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

            'wma_1d': {
                [COL_NAME]: 'WMA 1D',
                [COL_SORT]: true,
                [COL_STYLE]: { textAlign: 'center' }

            },
            'wma_1w': {
                [COL_NAME]: 'WMA 1W',
                [COL_SORT]: true,
                [COL_STYLE]: { textAlign: 'center' }

            },

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

            ['wma_1d']: {
                [FILTER_NAME]: lang('wma_1d'),
                [FILTER_TYPE]: 'number',
                [FILTER_LOGIC]: ['>=', '<='],
            },
            ['wma_1w']: {
                [FILTER_NAME]: lang('wma_1w'),
                [FILTER_TYPE]: 'number',
                [FILTER_LOGIC]: ['>=', '<='],
            },

        }


        this.table_wma_struct[STRUCT_EDIT] = {


        }

        this.table_wma_struct[STRUCT_ROWS] = {

        };
        this.table_wma_struct[STRUCT_TABLE] = {
            [DATA_TABLE_ID]: '1ass122344',
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
        var model = new Candle_1d();

        var Candle_1m = await model.getAll();

        var result = {};
        var first1D = 0;
        var check1D = 0;
        var first1W = 0;
        var check1W = 0;
        if (Candle_1m['result']) {
            var datas = Candle_1m['data'];

            for (let i = 0; i < datas.length; i++) {
                var data = datas[i];
                if (data[CANDLE_1D_RSI_WMA]) {
                    var time = Number(data[CANDLE_1D_OPEN_TIME]);
                    var value = Math.round(Number(data[CANDLE_1D_RSI_WMA]) * 100) / 100;
                    var signal = Math.floor(Number(data[CANDLE_1D_SIGNAL]) ) ;

                    if (check1D == 0) {
                        first1D = time;
                        check1D = 1
                    }

                    result[time] = {
                        'time': time,
                        'wma_1d': value,
                        'signal' : signal
                    }
                }


            }


        }



        var model1w = new candle_1w();

        var Candle_1w = await model1w.getAll();


        if (Candle_1w['result']) {
            var datas = Candle_1w['data'];


            for (let i = 0; i < datas.length; i++) {
                var data = datas[i];

                if (data[CANDLE_1W_RSI_WMA]) {

                    var time = Number(data[CANDLE_1W_OPEN_TIME]);
                    var value = Math.round(Number(data[CANDLE_1W_RSI_WMA]) * 100) / 100;
                    if (check1W == 0) {
                        first1W = time;
                        check1W = 1
                    }

                    if (result[time]) {
                        result[time]['wma_1w'] = value
                    } else {
                        result[time] = {
                            'time': time,
                            'wma_1w': value,
                            
                        }
                    }
                }


            }

        }

        var modelWma45 = new Wma_45();

        var Wma45Data = await modelWma45.read({ 'orderBy': 'time', 'sort': 'desc' });

        if (Wma45Data['result']) {
            var datas = Wma45Data['data'];


            for (let i = 0; i < datas.length; i++) {
                let item = datas[i];
                let time = Number(item['time']) * 1000
                let wma1d = Math.round(Number(item['wma45_1D']) * 100) / 100;
                let wma1w = Math.round(Number(item['wma45_1W']) * 100) / 100;
                if (time < first1D && wma1d) {

                    if (result[time]) {
                        result[time]['wma_1d'] = wma1d
                    } else {
                        result[time] = {
                            'time': time,
                            'wma_1d': wma1d
                        }
                    }



                }
                if (time < first1W && wma1w) {

                    if (result[time]) {
                        result[time]['wma_1w'] = wma1w
                    } else {
                        result[time] = {
                            'time': time,
                            'wma_1w': wma1w
                        }
                    }


                }
            }

        }
 
        let out = Object.values(result)  ;
        out.sort((a, b) => (a.time > b.time) ? 1 : -1)

        for (let i = 0; i < out.length; i++) {
            let fill
            if(out[i]['wma_1w']){
                fill = out[i]['wma_1w']
                
            }
            if(i < out.length - 1){
                if(fill && !isset(out[i+1]['wma_1w'])){
                    out[i+1]['wma_1w'] = fill
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

export default Wma_allView;
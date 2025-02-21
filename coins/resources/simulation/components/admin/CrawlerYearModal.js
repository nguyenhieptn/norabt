import React, { Component } from 'react';


import Input from '../../components/input/Input';

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


class CrawlerYearModal extends Component {
    constructor(props) {
        super(props);
        this.id = makeId();
        this.state = {
            Log: []
        }

        this.table_crawler_year = {};
        this.table_crawler_year[STRUCT_FILTERS] = {}
        this.table_crawler_year[STRUCT_COLUMNS] = {

            'symbol': {
                [COL_NAME]: 'Symbol',
                [COL_SORT]: true,
                [COL_STYLE]: { textAlign: 'center' }

            },

        }
        
        this.table_crawler_year[STRUCT_FILTERS] = {

        }

        this.table_crawler_year[STRUCT_EDIT] = {

        }

        this.table_crawler_year[STRUCT_ROWS] = {

        };

        this.table_crawler_year[STRUCT_TABLE] = {
            [DATA_TABLE_ID]: '1ass122344',
            [DATA_FILTERS]: {},
            [DATA_HIDDEN_COL]: {},
            [DATA_PERMIT_COL]: this.permissionTableAlertView(),
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

        };

        this.table_crawler_year_tracking = {};
        this.table_crawler_year_tracking[STRUCT_FILTERS] = {}
        this.table_crawler_year_tracking[STRUCT_COLUMNS] = {

            [CRAWLER_YEAR_TRACKING_SYMBOL]: {
                [COL_NAME]: lang(CRAWLER_YEAR_TRACKING_SYMBOL),
                [COL_SORT]: true,
                [COL_STYLE]: { textAlign: 'center' , maxWidth : '500px' },
                // [COL_DECORATOR_IN]: (data) => {
                //     const myArray = data.split(",");
                //     return myArray.map(symbol => {
                //         return (
                //             <div>{symbol}</div>
                //         )
                //     })
                //     return data
                // },

            },
            'Total_symbol': {
                [COL_NAME]: 'Total Symbol',
                [COL_SORT]: true,
                [COL_STYLE]: { textAlign: 'center' },
                [COL_DECORATOR_IN]: (colid, rowid, data) => {
                    var rowData = data[rowid];
                    let a = rowData[CRAWLER_YEAR_TRACKING_SYMBOL]
                    const myArray = a.split(",");
                    return myArray.length
                },

            },
            [CRAWLER_YEAR_TRACKING_STATUS]: {
                [COL_NAME]: lang(CRAWLER_YEAR_TRACKING_STATUS),
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: data => {
                    return data == 'RUNNING' ? <div style={{ color: '#00e209', fontWeight: 'bold', textAlign: 'center' }}>Running</div> : <div style={{ color: 'red', fontWeight: 'bold', textAlign: 'center' }}>Done</div>
                }

            },
           
            [CRAWLER_YEAR_TRACKING_DB]: {
                [COL_NAME]: lang(CRAWLER_YEAR_TRACKING_DB),
                [COL_SORT]: true,
                [COL_STYLE]: { textAlign: 'center' }

            },
            [CRAWLER_YEAR_TRACKING_EXCHANGE]: {
                [COL_NAME]: lang(CRAWLER_YEAR_TRACKING_EXCHANGE),
                [COL_SORT]: true,
                [COL_STYLE]: { textAlign: 'center' }

            },
            [CRAWLER_YEAR_TRACKING_FRAME]: {
                [COL_NAME]: lang(CRAWLER_YEAR_TRACKING_FRAME),
                [COL_SORT]: true,
                [COL_STYLE]: { textAlign: 'center' }

            },
            [CRAWLER_YEAR_TRACKING_START_TIME]: {
                [COL_NAME]: lang(CRAWLER_YEAR_TRACKING_START_TIME),
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
                [COL_STYLE]: { textAlign: 'center' }

            },
            [CRAWLER_YEAR_TRACKING_END_TIME]: {
                [COL_NAME]: lang(CRAWLER_YEAR_TRACKING_END_TIME),
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
                [COL_STYLE]: { textAlign: 'center' }

            },
            [CRAWLER_YEAR_TRACKING_RUNNING]: {
                [COL_NAME]: lang(CRAWLER_YEAR_TRACKING_RUNNING),
                [COL_SORT]: true,
                [COL_STYLE]: { textAlign: 'center' }

            },
            [CRAWLER_YEAR_TRACKING_RESULT]: {
                [COL_NAME]: lang(CRAWLER_YEAR_TRACKING_RESULT),
                [COL_SORT]: false,
                [COL_STYLE]: { whiteSpace: 'break-spaces' , maxWidth:'unset'},
                [COL_DECORATOR_IN]: data => {
					try {
						if (!data || data == '') return ''
						data = JSON.parse(data)
						return JSON.stringify(data, null, 2)
					} catch (error) {
						return ''
					}

				}

            },
            'Total_symbol_run': {
                [COL_NAME]: 'Total Symbol Run',
                [COL_SORT]: true,
                [COL_STYLE]: { textAlign: 'center' },
                [COL_DECORATOR_IN]: (colid, rowid, data) => {
                    var rowData = data[rowid];
                    let result = rowData[CRAWLER_YEAR_TRACKING_RESULT]
                    try {
						if (!result || result == '') return ''
						result = JSON.parse(result)
						return Object.keys(result).length
					} catch (error) {
						return ''
					}
                },

            },


        }
        this.table_crawler_year_tracking[STRUCT_FILTERS] = {
            
        }


        this.table_crawler_year_tracking[STRUCT_EDIT] = {


        }

        this.table_crawler_year_tracking[STRUCT_ROWS] = {

        };
        this.table_crawler_year_tracking[STRUCT_TABLE] = {
            [DATA_TABLE_ID]: '1ass1223442',
            [DATA_FILTERS]: {},
            [DATA_HIDDEN_COL]: {},
            [DATA_PERMIT_COL]: this.permissionTableTrackingView(),
            [DATA_KEY]: [CRAWLER_YEAR_TRACKING_ID],
            [DATA_SORT]: { },
            [FLAG_FILTER]: true,
            [FLAG_FILTER_CHANGE]: true,
            [FLAG_MULTI_SORT]: false,
            [FLAG_RESIZABLE]: true,
            [FLAG_SELECT_ROWS]: true,
            [FLAG_SETTING_ROWS]: false,
            [FLAG_EXPAND_ROWS]: false,
            [FLAG_HEAD_ROW]: true,



        };
    }

    permissionTableAlertView() {
        return Object.assign(
            ...Object.keys(this.table_crawler_year[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
            ...Object.keys(this.table_crawler_year[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
        )
    }
    permissionTableTrackingView() {
        return Object.assign(
            ...Object.keys(this.table_crawler_year_tracking[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
            ...Object.keys(this.table_crawler_year_tracking[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
        )
    }



    modal(cmd = 'show') {
        if (cmd == 'hide') {
            $("#add_row_modal" + this.id).modal('hide');
            if (this.getBTCInterval) {
                clearInterval(this.getBTCInterval);
            }
            

        } else {
            $("#add_row_modal" + this.id).modal();
            this.getLog()
            this.getBTCInterval = setInterval(() => { this.getLog() }, 3000);
        }
    }

    componentWillUnmount() {
        if (this.getBTCInterval) {
            clearInterval(this.getBTCInterval);
        }
    }
    delTracking() {
        var dataSelect = this.tableTracking[STRUCT_TABLE][DATA_SELECT_ROWS];
        var id = [];
        for (let i in dataSelect) {
           id.push({
            [CRAWLER_YEAR_TRACKING_ID] : dataSelect[i][CRAWLER_YEAR_TRACKING_ID]
           });
        }

        if (id.length == 0) {
            showLog('Please select a symbol');
            return;
        }


        axios.request({
            url: `/admin/crawler_year/drops`,
            method: 'Post',
            data : {
                data : id
            }
        })
        .then(response => {
                this.getLog();
        })

        .catch((error) => {
            console.log(error);
            error_handle(error)
        })
    }

    getLog(loading) {

        axios.request({
            url: `/admin/crawler_year/getRuning`,
            method: 'Post',
        })
            .then(response => {

                response = response['data']['data'];
                response.reverse();
                console.log(response)
                this.loadOriginTracking(response);

            })

            .catch((error) => {
                console.log(error);
                error_handle(error)
            })
    }
    loadOriginTracking(data) {
        this.tableTracking.setOrigin(data);
    }

    loadOrigin(data) {
        this.table.setOrigin(data);

    }
    saveData() {
        var data = {};

        data['exchange'] = this.inputExchange.getValue();
        data['frame'] = this.inputFrame.getValue();
        data['reset'] = this.inputReset.getValue();

        var symbol = [];

        this.table[STRUCT_TABLE][DATA_TABLE].map(item => { symbol.push(item['symbol']) })


        data['symbol'] = symbol;

        App.loading(true);
        axios.request({
            url: `/admin/crawler_year/crawler`,
            method: 'Post',
            data: data
        })
            .then(response => {
                App.loading(false);
                response = response['data']['data'];
                // this.setState({
                //     Log
                // });

            })

            .catch((error) => {
                App.loading(false);
                console.log(error);
                error_handle(error)
            })
    }



    componentDidMount() {

    }

    render() {

        return (
            <div className="modal fade" id={"add_row_modal" + this.id} onClick={() => { addClass($('body')[0], 'modal-open') }}>
                <div className="modal-dialog modal-lg modal-dialog-centered" style={{ maxWidth: '95%' }}>
                    <div className="modal-content">

                        <div className="modal-header">
                            <h4 className="modal-title">{lang("Crawler")}</h4>
                            <button type="button" className="close" data-dismiss="modal">&times;</button>
                        </div>

                        <div className="modal-body" >
                            <div style={{ marginBottom: '15px' }} >

                                <Table ref={c => this.tableTracking = c} table={this.table_crawler_year_tracking} autoload={false} loadOrigin={this.loadOriginTracking.bind(this)}>
                                    <FuncBar
                                        left={<>
                                            <div className='box_flex'>
                                                <FuncHideCol />
                                            </div>
                                        </>}
                                        right={<>

                                            <div className="table_function">

                                                <div className="button" title={lang("Delete Row selected")} onClick={() => { this.delTracking() }} style={{ display: 'flex' }}>
                                                    <i className="fa fa-trash"></i>&nbsp;{lang('Delete')}
                                                </div>

                                            </div><FuncClear></FuncClear><FuncRefresh /><FuncExport /></>}></FuncBar>
                                    <MainTable className='table table-bordered table-striped table-resizable' minHeight={0}></MainTable>
                                    <Pagination></Pagination>

                                </Table>
                            </div>

                            <hr></hr>
                            <div style={{ display: 'flex', marginLeft: '3px' }}>
                                

                                <div style={{ display: 'flex ', alignItems: 'center', marginRight: '20px' }}>
                                    <span style={{ marginRight: '10px' }}>Exchange : </span>
                                    <Input ref={c => this.inputExchange = c} className='input' struct={{
                                        [INPUT_TYPE]: 'select',
                                        [INPUT_NULL]: true,
                                        [INPUT_OPTION]: {
                                            'future': 'future',
                                            'spot': 'spot',
                                        },
                                        [INPUT_DEFAULT]: 'future'
                                    }}></Input>
                                </div>

                                <div style={{ display: 'flex ', alignItems: 'center', marginRight: '20px' }}>
                                    <span style={{ marginRight: '10px' }}>Reset : </span>
                                    <Input ref={c => this.inputReset = c} className='input' struct={{
                                        [INPUT_TYPE]: 'select',
                                        [INPUT_NULL]: true,
                                        [INPUT_OPTION]: {
                                            '0': 'Continue',
                                            '1': 'Reset',
                                        },
                                        [INPUT_DEFAULT]: '0'
                                    }}></Input>
                                </div>

                                <div style={{ display: 'flex ', alignItems: 'center', marginRight: '20px' }}>
                                    <span style={{ marginRight: '10px' }}>Frame : </span>
                                    <Input ref={c => this.inputFrame = c} className='input' struct={{
                                        [INPUT_TYPE]: 'select',
                                        [INPUT_NULL]: true,
                                        [INPUT_OPTION]: {
                                            'all': 'all',
                                            '1m': '1m',
                                            '3m': '3m',
                                            '15m': '15m',
                                            '1d': '1d',
                                            '1h': '1h',
                                            '4h': '4h',
                                            '1w': '1w',

                                        },
                                        [INPUT_DEFAULT]: 'all'
                                    }}></Input>
                                </div>
                            </div>

                            <Table ref={c => this.table = c} table={this.table_crawler_year} autoload={false} loadOrigin={this.loadOrigin.bind(this)}>
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

                        <div className="modal-footer">
                            <button type="button" className="btn btn-warning" onClick={() => { this.saveData() }}>{lang('Crawler')}</button>
                            <button type="button" className="btn btn-danger" data-dismiss="modal">{lang('Close')}</button>
                        </div>
                    </div>
                </div>
            </div>
        );
    }
}

export default CrawlerYearModal;
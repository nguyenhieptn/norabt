import React, { Component } from 'react';
import Input from '../../components/input/Input'

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
import TopBTCModal from '../../components/admin/TopBTCModal';

import Top_BTC from '../../model/admin/Top_BTC'
class Top_btcView extends Component {

    constructor(props) {
        super(props);
        this.state = {
            totalBTC : 0
        }
        this.id = makeId();
        this.top_btc_struct = {};
        this.top_btc_struct[STRUCT_FILTERS] = {}
        this.top_btc_struct[STRUCT_COLUMNS] = {

            // [TOP_BTC_ID]:{
            //     [COL_NAME]: lang(TOP_BTC_ID),
            //     [COL_SORT]: true,

            // },

            [TOP_BTC_ADDRESS]: {
                [COL_NAME]: lang(TOP_BTC_ADDRESS),
                [COL_SORT]: false,
                [COL_DECORATOR_IN]: (data) => {

                    return <b style={{ cursor: 'pointer' }} onClick={() => { 
                        // this.TopBTCModal.modal(); this.TopBTCModal.getData(data) 
                      
                        var index = data.indexOf('wallet');
                        if(index > -1){
                            data = data.substring(0,index);
                        }
                        window.open(`https://bitinfocharts.com/bitcoin/address/${data}`, '_blank');
                    }}
                        >{data}</b>;
                },

            },
            [TOP_BTC_BTC]: {
                [COL_NAME]: lang(TOP_BTC_BTC),
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => {
                    var a = `${formatNumber(data)} BTC`;
                    return a;
                },


            },
            [TOP_BTC_USD]: {
                [COL_NAME]: lang(TOP_BTC_USD),
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => {
                    var a = `$${formatNumber(data)}`;
                    return a;
                },

            },
            [TOP_BTC_DENTAL_1W]: {
                [COL_NAME]: lang(TOP_BTC_DENTAL_1W),
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => {
                    if (data == null) return
                    var a;
                    var color;
                    if (data > 0) {
                        a = `+${data} BTC`;
                        color = '#438444';
                    } else {
                        color = '#b94a48';
                        a = `${data} BTC`
                    }
                    return <span style={{ color: color }} >{a}</span>;
                },

            },
            [TOP_BTC_DENTAL_1M]: {
                [COL_NAME]: lang(TOP_BTC_DENTAL_1M),
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => {
                    if (data == null) return
                    var a;
                    var color;
                    if (data > 0) {
                        a = `+${data} BTC`;
                        color = '#438444';
                    } else {
                        color = '#b94a48';
                        a = `${data} BTC`
                    }
                    return <span style={{ color: color }} >{a}</span>;
                },

            },
            [TOP_BTC_PERCENT]: {
                [COL_NAME]: lang(TOP_BTC_PERCENT),
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => {
                    var a = `${data}%`;
                    return a;
                },

            },
            [TOP_BTC_FIRST_IN]: {
                [COL_NAME]: lang(TOP_BTC_FIRST_IN),
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },

            },
            [TOP_BTC_LAST_IN]: {
                [COL_NAME]: lang(TOP_BTC_LAST_IN),
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },

            },
            [TOP_BTC_INS]: {
                [COL_NAME]: lang(TOP_BTC_INS),
                [COL_SORT]: true,

            },
            [TOP_BTC_FIRST_OUT]: {
                [COL_NAME]: lang(TOP_BTC_FIRST_OUT),
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => { if (data == '') return; else return moment(data, 'X').format(DATE_FORMAT) },

            },
            [TOP_BTC_LAST_OUT]: {
                [COL_NAME]: lang(TOP_BTC_LAST_OUT),
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => { if (data == '') return; else return moment(data, 'X').format(DATE_FORMAT) },

            },
            [TOP_BTC_OUTS]: {
                [COL_NAME]: lang(TOP_BTC_OUTS),
                [COL_SORT]: true,

            },

            [TOP_BTC_TIME]: {
                [COL_NAME]: lang(TOP_BTC_TIME),
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },

            },

        }
        this.top_btc_struct[STRUCT_FILTERS] = {
            [TOP_BTC_ADDRESS]: {
                [FILTER_NAME]: lang(TOP_BTC_ADDRESS),
                [FILTER_TYPE]: 'text',
      
            },
            [TOP_BTC_BTC]: {
                [FILTER_NAME]: lang(TOP_BTC_BTC),
                [FILTER_TYPE]: 'number',
                [FILTER_LOGIC]: ['>=', '<='],
            },

            [TOP_BTC_FIRST_IN]: {
                [FILTER_NAME]: lang(TOP_BTC_FIRST_IN),
                [FILTER_TYPE]: 'date',
                [FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
                [FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('X') },
            },
            [TOP_BTC_LAST_IN]: {
                [FILTER_NAME]: lang(TOP_BTC_LAST_IN),
                [FILTER_TYPE]: 'date',
                [FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
                [FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('X') },
            },

            [TOP_BTC_FIRST_OUT]: {
                [FILTER_NAME]: lang(TOP_BTC_FIRST_OUT),
                [FILTER_TYPE]: 'date',
                [FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
                [FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('X') },
            },
            [TOP_BTC_LAST_OUT]: {
                [FILTER_NAME]: lang(TOP_BTC_LAST_OUT),
                [FILTER_TYPE]: 'date',
                [FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format(DATE_FORMAT) },
                [FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('X') },
            },

            [TOP_BTC_TIME]: {
                [FILTER_NAME]: lang(TOP_BTC_TIME),
                [FILTER_TYPE]: 'date',
                [FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'X').format('DD/MM/YYYY') },
                [FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, 'DD/MM/YYYY').format('X') },
            },
        }


        this.top_btc_struct[STRUCT_EDIT] = {


        }

        this.top_btc_struct[STRUCT_ROWS] = {
            // [ROW_FOOTER]: (datas, visibleColumns) => {

            // 	var totalbtc = 0;
            //     // console.log(datas);
            // 	for (let i in datas) {
            // 		var data = datas[i];
            // 		totalbtc += Number(data[TOP_BTC_BTC]);
            // 	}
            // 	return <tr>
            // 		<td colSpan={2}></td>

            // 		<td colSpan={1} style={{ fontWeight: 'bold', color: (totalbtc > 0 ? "green" : "red"), }}>Total BTC: {formatNumber(totalbtc)}</td>

            // 		<td colSpan={visibleColumns.length - 3}></td>
            // 	</tr>

            // }

        };
        this.top_btc_struct[STRUCT_TABLE] = {
            [DATA_TABLE_ID]: '1ass122btc344',
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

            model: new Top_BTC()



        };


    }
    permissionTableAlertView() {
        return Object.assign(
            ...Object.keys(this.top_btc_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
            ...Object.keys(this.top_btc_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
        )
    }

    funcHandle(data, message) {
        // console.log(data);
        console.log(message);
        this.setState({
            totalBTC : message
        });
    }



    render() {
        return (
            <>



                <Table ref={c => this.table = c} table={this.top_btc_struct} autoload={true} onFilterSuccess={(data, message) => this.funcHandle(data, message)}
                >
                    <FuncBar
                        left={<>
                            <div className='box_flex'>
                                <FuncHideCol />
                                <span style={{ marginRight: '10px' }}>Total BTC :</span>
                                <span style={{ border : '1px solid black' , padding : '4px 20px 4px 4px', borderRadius : '4px'}}>{formatNumber(this.state.totalBTC.toFixed(2))} BTC</span>
                            </div>
                        </>}
                        right={<>

                            <FuncClear></FuncClear><FuncRefresh /><FuncExport /></>}></FuncBar>
                    <MainTable className='table table-bordered table-striped table-resizable' minHeight={0}></MainTable>
                    <Pagination></Pagination>

                </Table>

                <TopBTCModal ref={c => this.TopBTCModal = c}></TopBTCModal>
            </>

        );
    }
}

export default Top_btcView;
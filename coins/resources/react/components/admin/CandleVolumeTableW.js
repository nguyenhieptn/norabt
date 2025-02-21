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


import Watchlist from '../../model/admin/Watchlist'


class CandleVolumeTableW extends Component {

    constructor(props) {
        super(props);

        this.wma_24h_struct = {};
        this.wma_24h_struct[STRUCT_FILTERS] = {}
        this.wma_24h_struct[STRUCT_COLUMNS] = {

            'symbol': {
                [COL_NAME]: 'Symbol',
                [COL_SORT]: true,
            },

        }
        this.wma_24h_struct[STRUCT_FILTERS] = {

            'symbol': {
                [FILTER_NAME]: lang('symbol'),
                [FILTER_TYPE]: 'text',
            },
        }

        this.wma_24h_struct[STRUCT_EDIT] = {


        }

        this.wma_24h_struct[STRUCT_ROWS] = {
            // [ROW_FUNCS]: (rowData) => {
            //     return <div className='box_flex' style={{ justifyContent: 'center' }}>
            //         <FuncEditRow rowData={rowData} />
            //     </div>
            // }
        };
        this.wma_24h_struct[STRUCT_TABLE] = {
            [DATA_TABLE_ID]: FINANCE_TABLE,
            [DATA_FILTERS]: {},
            [DATA_HIDDEN_COL]: {},
            [DATA_PERMIT_COL]: this.permissionFinance_24hView(),
            [DATA_KEY]: [FINANCE_ID],
            [DATA_SORT]: {},
            [FLAG_FILTER]: true,
            [FLAG_FILTER_CHANGE]: true,
            [FLAG_MULTI_SORT]: false,
            [FLAG_RESIZABLE]: true,
            [FLAG_SELECT_ROWS]: true,
            [FLAG_SETTING_ROWS]: false,
            [FLAG_EXPAND_ROWS]: false,
            [FLAG_HEAD_ROW]: true,

            // model: new Candle_24h()



        };

        this.endData = 0;
        this.watchlistIcon = {};


    }

    permissionFinance_24hView() {
        return Object.assign(
            ...Object.keys(this.wma_24h_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
            ...Object.keys(this.wma_24h_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
        )
    }

    getIcon() {
		var watchlist = new Watchlist();

		return watchlist.getIcon();

	}

    componentDidMount() {

        this.getIcon().then(res => {
			this.watchlistIcon = res;
            this.loadOrigin();
		});
        // this.loadOrigin();

      
    }

    getData1M(){
        var url = '/admin/testnetchart/getCandleDataTable1M';
        return axios.request({
             url: url,
             method: 'POST',
             data: {}
         }).then(res => {
             res = res['data']['data'];

             var dataHandle ={};
             res.map(item => {
                 if (isset(dataHandle[item['candlestick_1M_symbol']])) {
                    
                    //  dataHandle[item['candlestick_1M_symbol']].push(item);
                     dataHandle[item['candlestick_1M_symbol']].unshift(item);
 
                 } else {
                     dataHandle[item['candlestick_1M_symbol']] = [];
                    //  dataHandle[item['candlestick_1M_symbol']].push(item);
                     dataHandle[item['candlestick_1M_symbol']].unshift(item);
 
                 }
             })

             var dataOk = [];
             Object.values(dataHandle).map(item => {
                 item.map(row => dataOk.push(row))
             })

             var tableData = {};
            //  var a = ['M5', 'M4', 'M3', 'M2', 'M1', 'M0'];
             var a = ['M0', 'M1', 'M2', 'M3', 'M4', 'M5'];
             var index = 0;
            dataOk.map(item => {
                 var spread = Number(item['candlestick_1M_close']) - item['candlestick_1M_open'];
                 if (spread < 0) spread = -spread;
 
 
                 if (isset(tableData[item['candlestick_1M_symbol']])) {
                     index = index + 1;
                     tableData[item['candlestick_1M_symbol']][a[index]] = Number(item['candlestick_1M_volume']) / spread;
 
                 } else {
                     index = 0;
                     tableData[item['candlestick_1M_symbol']] = { 'symbol': item['candlestick_1M_symbol'] };
                     tableData[item['candlestick_1M_symbol']][a[index]] = Number(item['candlestick_1M_volume']) / spread;
 
                 }
 
 
             })

              Object.values(tableData).map(row => {

                delete (row['M5'])
            })

            return tableData;

        })
    }


    getData1w(){
        var url = '/admin/testnetchart/getCandleDataTable1w';
       return axios.request({
            url: url,
            method: 'POST',
            data: {}
        }).then(res => {
            res = res['data']['data'];

            var dataHandle ={};
            res.map(item => {
                if (isset(dataHandle[item['candlestick_1w_symbol']])) {
                   
                    // dataHandle[item['candlestick_1w_symbol']].push(item);
                     dataHandle[item['candlestick_1w_symbol']].unshift(item);

                } else {
                    dataHandle[item['candlestick_1w_symbol']] = [];
                    // dataHandle[item['candlestick_1w_symbol']].push(item);
                     dataHandle[item['candlestick_1w_symbol']].unshift(item);

                }
            })

            var dataOk = [];
            Object.values(dataHandle).map(item => {
                item.map(row => dataOk.push(row))
            })

            // console.log(dataOk);
        
         
            var tableData = {};
            // var a = ['w5', 'w4', 'w3', 'w2', 'w1', 'w0'];
             var a = ['w0', 'w1', 'w2', 'w3', 'w4', 'w5'];
            var index = 0;
            dataOk.map(item => {
                var spread = Number(item['candlestick_1w_close']) - item['candlestick_1w_open'];
                if (spread < 0) spread = -spread;


                if (isset(tableData[item['candlestick_1w_symbol']])) {
                    index = index + 1;
                    tableData[item['candlestick_1w_symbol']][a[index]] = Number(item['candlestick_1w_volume']) / spread;

                } else {
                    index = 0;
                    tableData[item['candlestick_1w_symbol']] = { 'symbol': item['candlestick_1w_symbol'] };
                    tableData[item['candlestick_1w_symbol']][a[index]] = Number(item['candlestick_1w_volume']) / spread;

                }


            })


            Object.values(tableData).map(row => {

                delete (row['w5'])
            })


           return tableData;


        })
    }

    async loadOrigin() {

        var data1w = await this.getData1w();

       

        var data1M = await this.getData1M();
       
        var b = ['M4', 'M3', 'M2', 'M1', 'M0'];

        b.map(item => {
            Object.keys(data1w).map(key =>{
                data1w[key][item] = data1M[key][item]
            })
        })

      

        var a = ['w5', 'w4', 'w3', 'w2', 'w1', 'w0'];

        var structColumn = {

            'symbol': {
                [COL_NAME]: 'Symbol',
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: data => {

                    if (data === null) return '';
					var img = this.watchlistIcon[data];
					if (img == undefined) {
						img = '/assets/img/Eicon.png'
						// img = this.watchlistIcon['BTCUSDT']
					}
					return <b>
						<img style={{ width: '20px', height: '20px', marginRight: '10px' }} src={img}></img>
						{data}
					</b>

					if (data === null) return '';
					return <b>
						<img style={{ width: '20px', height: '20px', marginRight: '10px' }} src={this.watchlistIcon[data]}></img>
						{data}
					</b>
				}

            },



        }

        for (let i = a.length - 1; i >= 1; i--) {
            structColumn[a[i]] = {
                [COL_NAME]: a[i],
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => {
                    if(!data) return ''
                    return <span>{formatNumber(data.toFixed(2))}</span>
                },
                [COL_STYLE]: {textAlign : 'center'}
            }

            this.table[STRUCT_TABLE][DATA_PERMIT_COL][a[i]] = 'read';
        }

        for (let i = b.length - 1; i >= 0; i--) {
            structColumn[b[i]] = {
                [COL_NAME]: b[i],
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => {
                    if(!data) return ''
                    return <span>{formatNumber(data.toFixed(2))}</span>
                },
                [COL_STYLE]: {textAlign : 'center'}
            }

            this.table[STRUCT_TABLE][DATA_PERMIT_COL][b[i]] = 'read';
        }

        this.table[STRUCT_COLUMNS] = structColumn;

    

        this.table.setOrigin(Object.values(data1w));

     
    }


    render() {
        return (
            <div>
                <Table ref={c => this.table = c} table={this.wma_24h_struct} autoload={false} loadOrigin={this.loadOrigin.bind(this)}>
                    <FuncBar
                        left={<>
                            <div className='box_flex'>
                                <FuncHideCol />

                            </div>
                        </>}
                        name={'Candle Volume'}
                        right={<><FuncClear></FuncClear><FuncRefresh /><FuncExport /></>}></FuncBar>
                    <MainTable className='table table-bordered table-striped table-resizable' minHeight={0}></MainTable>
                    <Pagination></Pagination>

                </Table>




            </div>
        );
    }
}

export default CandleVolumeTableW
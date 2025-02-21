import React, { Component } from 'react'
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


import Finance from '../../model/admin/Finance'
import Finance_Future from '../../model/admin/Finance_Future'

import Input from '../../components/input/Input'
// import VolumeAlertModal from '../../components/analytics/VolumeAlertModal'

import candle_1d from '../../model/admin/Candle_1d';
import candle_1w from '../../model/admin/Candle_1w';

import Fear from '../../model/admin/Fear';
import TopSum from '../../model/admin/Top_Sum';
import Max_pain from '../../model/admin/Max_pain';

class WMA24hView extends Component {

    constructor(props) {
        super(props);

        this.wma_24h_struct = {};
        this.wma_24h_struct[STRUCT_FILTERS] = {}
        this.wma_24h_struct[STRUCT_COLUMNS] = {

            [FINANCE_NAME]: {
                [COL_NAME]: 'WMA',
                [COL_SORT]: true,
            },
        
        }
        this.wma_24h_struct[STRUCT_FILTERS] = {

            [FINANCE_NAME]: {
                [FILTER_NAME]: lang(FINANCE_NAME),
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
            [DATA_SORT]: {  },
            [FLAG_FILTER]: true,
            [FLAG_FILTER_CHANGE]: true,
            [FLAG_MULTI_SORT]: false,
            [FLAG_RESIZABLE]: true,
            [FLAG_SELECT_ROWS]: true,
            [FLAG_SETTING_ROWS]: false,
            [FLAG_EXPAND_ROWS]: false,
            [FLAG_HEAD_ROW]: true,

            // model: new Candle_24h()
            model: new Finance()
           

        };

        this.endData = 0;


    }

    permissionFinance_24hView() {
        return Object.assign(
            ...Object.keys(this.wma_24h_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
            ...Object.keys(this.wma_24h_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
        )
    }

    componentDidMount() {
        this.loadOrigin();
    }


    async loadOrigin() {
        var startDate = Number(this.startDate.getValue());
        var endDate = Number(this.endDate.getValue());
        this.endData = startDate;
      
        var dates = [startDate];

        var t = startDate;
        while (t < endDate) {
            t += 86400000;
            dates.push(t);
        }
 
    

        var model1d = new candle_1d();
        var Candle_1d = await model1d.getAll();
        var Candle_1d = Candle_1d['data'];
    
     
        
        var model1w = new candle_1w();
        var Candle_1w = await model1w.getAll();
        var Candle_1w = Candle_1w['data'];

        var dataCandle_1d = {};
        var trend1 = {}
        Candle_1d.map(item => {
            dataCandle_1d[item[CANDLE_1D_OPEN_TIME]] = Math.round(Number(item[CANDLE_1D_RSI_WMA]) * 100) / 100 
            trend1[item[CANDLE_1D_OPEN_TIME]] = Math.floor(Number(item[CANDLE_1D_SIGNAL]) )
        })


        var dataCandle_1w = {};
        Candle_1w.map(item => {
            dataCandle_1w[item[CANDLE_1W_OPEN_TIME]] = Math.round(Number(item[CANDLE_1W_RSI_WMA]) * 100) / 100 
        })

       

        var model = new Fear();
        var Fear_Data = await model.get(null, { limit: 1000, orderBy: FEAR_TIME, asc: false });
        var chartDataFear = {};
        if (Fear_Data['result']) {
            var datas = Fear_Data['data'];


            for (let i = datas.length - 1; i >= 0; i--) {
                var data = datas[i];
                // var time = data[FEAR_TIME] + 86399999;
                var time = data[FEAR_TIME] ;
                chartDataFear[time] = data[FEAR_VALUE]
            }

        }
       
        var TopSumModel = new TopSum();
        var topsumdata = await TopSumModel.get([], { 'orderBy': TOP_SUM_TIME, 'asc': true });
        topsumdata = topsumdata['data'];
        var dataTopSum = {};
        topsumdata.map(item => {
            var time = Number(item[TOP_SUM_TIME])  - 86400000 - 86399999;

            dataTopSum[time] = Number(item[TOP_SUM_BALANCE].toFixed(2))

        })


        var financeModel = new Finance();
        var financeData = await financeModel.get([], { 'orderBy': FINANCE_CLOSE_TIME, 'asc': true });
        financeData = financeData['data'];
      
        var dataFinanceDJIA = {};
        var dataFinanceNIKKEI = {};
        var dataFinanceGOLD = {};
        var dataFinanceNASDAQ = {};
        financeData.map(item => {
            var time = Number(item[FINANCE_CLOSE_TIME])  - 86399999 ;
            var per = Number(item[FINANCE_PERCENT]).toFixed(3)
            if(item[FINANCE_NAME] == "GOLD"){
                dataFinanceGOLD[time] =per

            } 
            
            if(item[FINANCE_NAME] == "DJIA"){
                dataFinanceDJIA[time] =per

            } 
            
            if(item[FINANCE_NAME] == "NASDAQ"){
                dataFinanceNASDAQ[time] =per

            } 
            
            if(item[FINANCE_NAME] == "NIKKEI"){
                dataFinanceNIKKEI[time] =per

            } 
            

           
        })

        var financeFutureModel = new Finance_Future();
        var financeFutureData = await financeFutureModel.get([], { 'orderBy': FIN_FU_TIME, 'asc': true });
        financeFutureData = financeFutureData['data'];
        var dataFinanceDOWFU = {};
        var dataFinanceSPFU = {};
        var dataFinanceNASFU = {};
        var dataFinanceOIL = {};

        financeFutureData.map(item => {
            var time = Number(item[FIN_FU_TIME])  - 86399999 ;
            var per = Number(item[FIN_FU_PERCENT])
            if(item[FIN_FU_NAME] == "DOW FUT"){
                dataFinanceDOWFU[time] =per

            } 
            
            if(item[FIN_FU_NAME] == "S&P FUT"){
                dataFinanceSPFU[time] =per

            } 
            
            if(item[FIN_FU_NAME] == "NAS FUT"){
                dataFinanceNASFU[time] =per

            } 
            
            if(item[FIN_FU_NAME] == "OIL"){
                dataFinanceOIL[time] =per

            } 
            

           
        })
       
  
        var tableData = {};

        for (let i in dates) {
            
            var startDate ;
      
            // startDate = dates[i] + 86399999  ;
            startDate = dates[i]  ;
         
            var sym = 'Trend 1';
            if (!isset(tableData[sym])) tableData[sym] = { [FINANCE_NAME]: sym };
            tableData[sym][dates[i]] =  dataCandle_1d[startDate];

            var sym13 = 'Trend 2';
            if (!isset(tableData[sym13])) tableData[sym13] = { [FINANCE_NAME]: sym13 };
            tableData[sym13][dates[i]] =  trend1[startDate];

            var sym1 = 'Season';
            if (!isset(tableData[sym1])) tableData[sym1] = { [FINANCE_NAME]: sym1 };
            tableData[sym1][dates[i]] =  dataCandle_1w[startDate - 604800000 ];

            var sym2 = 'Fear';
            if (!isset(tableData[sym2])) tableData[sym2] = { [FINANCE_NAME]: sym2 };
            tableData[sym2][dates[i]] =  chartDataFear[startDate];

            var sym3 = 'BTC Wallet';
            if (!isset(tableData[sym3])) tableData[sym3] = { [FINANCE_NAME]: sym3 };
            tableData[sym3][dates[i]] =  dataTopSum[startDate] ;
            var btcVolatility = Number(dataTopSum[Number(startDate) + 86400000]) -  Number(dataTopSum[startDate]);
            var sym4 = 'BTC Wallet Volatility';
            if (!isset(tableData[sym4])) tableData[sym4] = { [FINANCE_NAME]: sym4 };
            tableData[sym4][dates[i] + 86400000] =  Number(btcVolatility.toFixed(2) )  ;

            var sym5 = "NASDAQ";
            if (!isset(tableData[sym5])) tableData[sym5] = { [FINANCE_NAME]: sym5 };
            tableData[sym5][dates[i]] =  dataFinanceNASDAQ[startDate]  ;

            var sym6 = "DJIA";
            if (!isset(tableData[sym6])) tableData[sym6] = { [FINANCE_NAME]: sym6 };
            tableData[sym6][dates[i]] =  dataFinanceDJIA[startDate]  ;

            var sym7 = "NIKKEI";
            if (!isset(tableData[sym7])) tableData[sym7] = { [FINANCE_NAME]: sym7 };
            tableData[sym7][dates[i]] =  dataFinanceNIKKEI[startDate]  ;

            var sym8 = "GOLD";
            if (!isset(tableData[sym8])) tableData[sym8] = { [FINANCE_NAME]: sym8 };
            tableData[sym8][dates[i]] =  dataFinanceGOLD[startDate]  ;

            var sym9 = "DOW FUT";
            if (!isset(tableData[sym9])) tableData[sym9] = { [FINANCE_NAME]: sym9 };
            tableData[sym9][dates[i]] =  dataFinanceDOWFU[startDate]  ;

            var sym10 = "S&P FUT";
            if (!isset(tableData[sym10])) tableData[sym10] = { [FINANCE_NAME]: sym10 };
            tableData[sym10][dates[i]] =  dataFinanceSPFU[startDate]  ;

            var sym11 = "NAS FUT";
            if (!isset(tableData[sym11])) tableData[sym11] = { [FINANCE_NAME]: sym11 };
            tableData[sym11][dates[i]] =  dataFinanceNASFU[startDate]  ;

            var sym12 = "OIL";
            if (!isset(tableData[sym12])) tableData[sym12] = { [FINANCE_NAME]: sym12 };
            tableData[sym12][dates[i]] =  dataFinanceOIL[startDate]  ;
           
        }


   

        

      

        var structColumn = {

            [FINANCE_NAME]: {
                [COL_NAME]: 'Indicator',
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => {

                    return <b>{data}</b>
                }

            },

         

        }

        for (let i = dates.length - 1; i >= 0; i--) {
            structColumn[dates[i]] = {
                [COL_NAME]: moment(dates[i], 'x').format('DD/MM/YYYY'),
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (colId, rowId, data) => {
                    var cus = ['Trend 1', 'Trend 2', 'Season','Fear','BTC Wallet'];
                    var name = data[rowId]['finance_name'];
                    if(cus.includes(name)){
                        var endData = this.endData;
                        var curData = data[rowId][colId];
                        var preData = data[rowId][colId -86400000];
    
                        if(curData && preData == undefined && colId != endData ){
                            preData = data[rowId][colId -86400000 * 7];
    
                        }
    
                        var color = 'red';
                        if(curData - preData >= 0){
                            color = 'limegreen';
                        }
    
                        if(colId == endData){
                            color = ''
                        }
    
                       
    
                        if(!curData ){
                           return
                        }
     
                        return <span style={{ color : color}}>{ formatNumber(curData)}</span>
                    }else{
                        var data = data[rowId][colId];
                        var color = 'limegreen';
                        if(data < 0) color = 'red'

                        if(!data ){
                            return
                         }

                        return <span style={{ color : color}}>{ formatNumber(data)}</span>
                    }
                   
                }
            }

            this.table[STRUCT_TABLE][DATA_PERMIT_COL][dates[i]] = 'read';
        }

        this.table[STRUCT_COLUMNS] = structColumn;

 

        this.table.setOrigin(Object.values(tableData));


    }

    render() {
        return (
            <div>
                <Table ref={c => this.table = c} table={this.wma_24h_struct} autoload={false} loadOrigin={this.loadOrigin.bind(this)}>
                    <FuncBar
                        left={<>
                            <div className='box_flex'>
                                <FuncHideCol />

                              

                                <Input className='input' placeholder='Start Time' ref={c => this.startDate = c} struct={{
                                    [INPUT_TYPE]: 'date',
                                    [INPUT_FORMAT]: 'DD/MM/YYYY',
                                    [INPUT_DEFAULT]: moment().subtract(3, 'weeks').format('DD/MM/YYYY'),
                                    [INPUT_DECORATOR_IN]: data => data,
                                    [INPUT_DECORATOR_OUT]: (data) => moment.utc(data, 'DD/MM/YYYY').format('x'),
                                    [INPUT_ONCHANGE_BLUR]: () => { this.loadOrigin() }
                                }}></Input>&nbsp;
                                <Input className='input' placeholder='Stop Time' ref={c => this.endDate = c} struct={{
                                    [INPUT_TYPE]: 'date',
                                    [INPUT_FORMAT]: 'DD/MM/YYYY',
                                    [INPUT_DEFAULT]: moment().format('DD/MM/YYYY'),
                                    [INPUT_DECORATOR_IN]: data => data,
                                    [INPUT_DECORATOR_OUT]: (data) => moment.utc(data, 'DD/MM/YYYY').format('x'),
                                    [INPUT_ONCHANGE_BLUR]: () => { this.loadOrigin() }
                                }}></Input>
                            </div>
                        </>}
                        name={'Indicator tracking'}
                        right={<><FuncClear></FuncClear><FuncRefresh /><FuncExport /></>}></FuncBar>
                    <MainTable className='table table-bordered table-striped table-resizable' minHeight={0}></MainTable>
                    <Pagination></Pagination>

                </Table>


                {/* <VolumeAlertModal ref={c => this.vlAlertModal = c}></VolumeAlertModal> */}


            </div>
        );
    }
}

export default WMA24hView
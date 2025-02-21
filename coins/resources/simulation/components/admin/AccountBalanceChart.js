import React, { Component } from 'react';
import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official';
import Lab_track_blance from '../../model/admin/Lab_track_balance';
import Lab_results from '../../model/admin/Lab_results';
import BalanceMaxModal from './BalanceMaxModal';
import AccountStopLossModal from './AccountStopLossModal';
import AccountOrderModal from './AccountOrderModal';
import InvestMaxModal from './InvestMaxModal';
import AccountStopLoss2Modal from './AccountStopLoss2Modal';
import Lab_track_balance_gen from '../../model/admin/Lab_track_balance_gen ';
class AccountBalanceChart extends Component {
    constructor(props) {
        super(props);
        this.id = makeId();
        this.symbol = '',
            this.state = {

                account: {},

                maxPerInBa: 0,
                daymaxPerInBa: 0,
                maxPerUreBa: 0,
                daymaxPerUreBa: 0,

                Options: {
                    chart: {
                    }
                    ,
                    title: {
                        text: '',
                    },
                    xAxis: {
                    },
                    scrollbar: {
                        enabled: false
                    },
                    credits: {
                        enabled: false
                    },
                    yAxis: [
                        {
                            crosshair: true,
                            title: {
                                text: '<b></b>',
                            },

                            // startOnTick: false,

                            labels: {
                                align: 'left'
                            }

                        },

                    ],

                    chart: {
                        height: (6 / 16 * 100) + '%',
                        panning: {
                            enabled: true,
                            type: 'x'
                        },
                        panKey: 'shift',
                        zoomType: 'x'

                    },
                    legend: {
                        enabled: true,


                    },
                    plotOptions: {
                        series: {
                            dataLabels: {
                                enabled: false
                            },
                            lineWidth: 1,
                            maxPointWidth: 100,
                            turboThreshold: 0,

                            marker: {
                                enabled: false
                            }
                        }

                    },
                    tooltip: {
                        style: {
                            fontSize: '10px'
                        },
                        shared: true,
                        split: false,
                    },
                    rangeSelector: {
                        buttonPosition: {
                            align: 'left',
                            // x: '0',
                            y: '-1',
                        },
                        // selected: 4,

                        allButtonsEnabled: true,
                        buttons:
                            [
                                {
                                    text: '1M',
                                    type: 'day',
                                    count: 30,

                                },
                                {
                                    text: '2M',
                                    type: 'day',
                                    count: 60,

                                },
                                {
                                    text: '3M',
                                    type: 'day',
                                    count: 90,

                                },
                                {
                                    text: '6M',
                                    type: 'day',
                                    count: 180,

                                },
                                {
                                    text: '1Y',
                                    type: 'day',
                                    count: 365,

                                },
                                {
                                    type: 'all',
                                    text: 'All'
                                },
                            ],
                        inputEnabled: false,
                        buttonSpacing: 10,
                    },

                    series: [
                        {
                            name: 'Wallet Balance',
                            id: "balance",
                            data: [],
                        },
                        {
                            name: 'Invest',
                            id: "invest",
                            data: [],
                            color: 'blue'
                        },
                        {
                            name: 'Unrealize',
                            id: "unrealize",
                            data: [],
                            color: 'red'
                        },
                        {
                            name: 'Margin Balance',
                            id: 'margin_balance',
                            data: [],

                            color: 'limegreen'
                        },
                        {
                            name: 'Flag',
                            type: 'flags',
                            data: [],
                            onSeries: 'unrealize',
                            shape: 'flag'
                        },
                        {
                            name: 'FlagSL',
                            type: 'flags',
                            data: [],
                            onSeries: 'balance',
                            shape: 'flag',
                            color: 'red'
                        }

                    ]
                }
            }
        this.updateChartWidth = this.updateChartWidth.bind(this);

        this.colors = {};

        Highcharts.setOptions({
            time: {
                timezoneOffset: moment().utcOffset(),
                useUTC: false
            }
        });

        this.startTime = null;
        this.chartData = {};

        this.resetIndex = 0;

    }

    componentDidMount() {


        this.updateChartWidth();
        this.resize_ob = new ResizeObserver((entries) => {
            this.updateChartWidth()
        });
        this.resize_ob.observe(this.chartContainer);



    }

    componentWillUnmount() {

        if (this.resize_ob) this.resize_ob.unobserve(this.chartContainer);

    }

    updateChartWidth() {
        if (this.updateWidthTimeout) clearTimeout(this.updateWidthTimeout);
        this.updateWidthTimeout = setTimeout(() => {

            this.setState({
                Options: {
                    ...this.setState.Options,
                    chart: {
                        width: typeof (this.chartContainer) !== null && this.chartContainer.clientWidth,
                    }

                }
            })
        }, 500);
    }



    setRangeSelector() {

        console.log('Set rangselector to 4')

        this.setState({
            Options: { rangeSelector: { selected: 4 } },
        })

    }

    modal(cmd = 'show') {
        if (cmd == 'hide') {

            $("#edit_row_modal" + this.id).modal('hide');
        } else {
            $("#edit_row_modal" + this.id).modal();
        }
    }

    loadData(rowData) {
        this.setState({ account: rowData });
        this.getData(rowData[LAB_ACCOUNT_ID]);



    }

    render() {
        return (
            <>

                <div className="modal fade" id={"edit_row_modal" + this.id} onClick={() => { addClass($('body')[0], 'modal-open') }}>
                    <div className="modal-dialog modal-lg modal-dialog-centered" style={{ maxWidth: '95%' }}>
                        <div className="modal-content">

                            <div className="modal-header">
                                <h4 className="modal-title">{this.state.account[LAB_ACCOUNT_NAME]}</h4>
                                <button type="button" className="close" data-dismiss="modal">&times;</button>
                            </div>

                            <div className="modal-body" style={{ textAlign: 'initial' }}>

                                <div className='box_shadow cus-hide ' ref={c => this.chartContainer = c} style={{ position: 'relative', marginTop: 15, padding: 5 }}>
                                    <div style={{ display: 'flex', position: 'absolute', top: '12px', right: '30px', zIndex: 1000 }}>
                                        <div className='mr-3 '>
                                            <div>
                                                {/* <span> Max Unrealize profit / Balance : </span> */}
                                                <span> Max Drawdown V : </span>
                                                <span>{this.state.maxPerUreBa} %</span>
                                            </div>
                                            <div>{moment(this.state.daymaxPerUreBa, 'x').format(DATE_FORMAT)}</div>
                                        </div>
                                        <div className='mr-3 '>
                                            <div>
                                                {/* <span> Max invest / Balance : </span> */}
                                                <span> Max Invest : </span>
                                                <span>{this.state.maxPerInBa} %</span>
                                            </div>
                                            <div>{moment(this.state.daymaxPerInBa, 'x').format(DATE_FORMAT)}</div>
                                        </div>

                                        <button type="button" className="btn btn-info mr-3" onClick={() => {

                                            this.BalanceMaxModal.modal();
                                            this.BalanceMaxModal.loadOrigin();
                                        }}>DDV</button>

                                  

                                        <button type="button" className="btn btn-info mr-3" onClick={() => {

                                            this.InvestMaxModal.modal();
                                            this.InvestMaxModal.loadOrigin();
                                        }}>MI</button>


                                        <button type="button" className="btn btn-info mr-3" onClick={() => {

                                            this.AccountStopLossModal.modal('show', {});
                                            this.AccountStopLossModal.loadOrigin();
                                        }}>SL</button>

                                        <button type="button" className="btn btn-info mr-3" onClick={() => {

                                            this.AccountStopLossModal2.modal('show', {});
                                            this.AccountStopLossModal2.loadOrigin();
                                        }}>MD</button>


                                        <button type="button" className="btn btn-info mr-3" onClick={() => {

                                            this.AccountOrderModal.modal();
                                            this.AccountOrderModal.loadOrigin(this.state.account[LAB_ACCOUNT_ID]);
                                        }}>Order</button>
                                    </div>
                                    <HighchartsReact
                                        ref={c => this.chart = c}
                                        highcharts={Highcharts}
                                        options={this.state.Options}
                                        constructorType={'stockChart'}
                                    />




                                </div>



                            </div>

                            <div className="modal-footer">
                                {isset(this.props.extraFunction) ? this.props.extraFunction : ''}
                                <button type="button" className="btn btn-danger" data-dismiss="modal">{lang('Close')}</button>
                            </div>

                        </div>
                    </div>
                </div>

                <BalanceMaxModal ref={c => this.BalanceMaxModal = c} title='Max Unrealize profit / Balance'></BalanceMaxModal>
                <InvestMaxModal ref={c => this.InvestMaxModal = c} title="Max Invest / Balance"></InvestMaxModal>
                <AccountStopLossModal ref={c => this.AccountStopLossModal = c} title='SL'></AccountStopLossModal>
                <AccountStopLoss2Modal ref={c => this.AccountStopLossModal2 = c} title='SL'></AccountStopLoss2Modal>
                <AccountOrderModal ref={c => this.AccountOrderModal = c} title='Order' ></AccountOrderModal>


            </>
        );
    }




    async getData(accountId) {

        let modelData = new Lab_track_balance_gen()
        modelData.read({ 'account_id': accountId }).then(res => {

            if (res['result']) {
                if(res['data'].length == 0){
                    this.modal('hide');
                    showLog('No Data Gen balance');
                    return
                }
                res = res['data'][0]
                

                let max_drawdown = JSON.parse(res['lab_track_balance_gen_max_drawdown'])
                let max_invest = JSON.parse(res['lab_track_balance_gen_max_invest'])
    
                let top20Flag = JSON.parse(res['lab_track_balance_gen_top20FL'])
                let FlagSL = JSON.parse(res['lab_track_balance_gen_FlagSL'])
    
                
                App.dataMax = JSON.parse(res['lab_track_balance_gen_dd'])
                App.dataInvest = JSON.parse(res['lab_track_balance_gen_mi'])
                App.dataStopLossBalance = JSON.parse(res['lab_track_balance_gen_sl'])

                App.dataStopLossBalance2 = JSON.parse(res['lab_track_balance_gen_md'])
              
                var investDatas = [];
                var unrealizeDatas = [];
                var marginBalanceDatas = [];
                var balanceDatas = [];

                modelData.test({ 'account_id': accountId }).then(res => {
                    if(res['result']){
                        res['data']['invest'].map(item => {
                            if(item['x'] == '1618717019000'){
                                console.log(item)
                            }
                        })
                        investDatas = res['data']['invest']
                        unrealizeDatas = res['data']['unrelize']
                        marginBalanceDatas = res['data']['maginBalance']
                        balanceDatas = res['data']['balance']
                        this.setState({
                            maxPerUreBa : (max_drawdown['max_drawdown'] * 100).toFixed(2),
                            maxPerInBa: (max_invest['max_invest'] * 100).toFixed(2),
                            daymaxPerUreBa  : max_drawdown['day_max_drawdown'],
                            daymaxPerInBa : max_invest['day_max_invest'],
                            Options: {
                                series: [
                                    {
                                        data: balanceDatas
                                    },
                                    {
                                        data: investDatas
                                    },
                                    {
                                        data: unrealizeDatas
                                    },
                                    {
                                        data: marginBalanceDatas
                                    },
                                    {
                                        data: top20Flag
                                    },
                                    {
                                        data: FlagSL
                                    }
                                ]
                            }
        
                        })
    
                    }
                })
              
       
                

            }




        })

        return

        var investDatas = [];
        var unrealizeDatas = [];
        var marginBalanceDatas = [];
        var balanceDatas = [];

        var model = new Lab_track_blance();

        var result = await model.read({ [LAB_TRACK_BL_ACCOUNT]: accountId }, true, {
            // orderBy: LAB_TRACK_BL_TIME,
            // sort: 'asc'
        });




        let SLBalane = {}

        var maxPerUreBa;
        var daymaxPerUreBa;
        var maxPerInBa;
        var daymaxPerInBa;

        var top20Dic = {};
        var top20 = []

        let check = true;


        var top20DicInvest = {};
        var top20Invest = [];

        if (result['result']) {
            result = result['data'];
            // console.log(result)
            if (result.length == 0) {
                showLog('No data or balance tracking is disabled');
                // setTimeout(() => this.modal('hide'), 500)
            }
            for (let i in result) {
                let time = Number(result[i][LAB_TRACK_BL_TIME]);


                SLBalane[time] = {
                    'time': time,
                    'balance': Number(result[i][LAB_TRACK_BL_BALANCE])
                }


                investDatas.push({
                    x: time,
                    y: Number(result[i][LAB_TRACK_BL_INVEST])
                });
                unrealizeDatas.push({
                    x: time,
                    y: Number(result[i][LAB_TRACK_BL_UNREALIZE])
                });
                marginBalanceDatas.push({
                    x: time,
                    y: Number(result[i][LAB_TRACK_BL_MARGIN_BL])
                });
                balanceDatas.push({
                    x: time,
                    y: Number(result[i][LAB_TRACK_BL_BALANCE])
                });

                var perUreBa = Number(result[i][LAB_TRACK_BL_UNREALIZE]) / Number(result[i][LAB_TRACK_BL_BALANCE]);
                var perInBa = Number(result[i][LAB_TRACK_BL_INVEST]) / Number(result[i][LAB_TRACK_BL_BALANCE]);


                let startOfDay = Math.floor(time / 86400000) * 86400000
                if (!isset(top20Dic[startOfDay])) {
                    top20Dic[startOfDay] = {
                        x: time,
                        y: perUreBa
                    }
                } else {
                    if (perUreBa < top20Dic[startOfDay].y) {
                        top20Dic[startOfDay] = {
                            x: time,
                            y: perUreBa
                        }
                    }
                }


                if (!isset(top20DicInvest[startOfDay])) {
                    top20DicInvest[startOfDay] = {
                        x: time,
                        y: perInBa
                    }
                } else {
                    if (perInBa > top20DicInvest[startOfDay].y) {
                        top20DicInvest[startOfDay] = {
                            x: time,
                            y: perInBa
                        }
                    }
                }




                if (!isset(maxPerUreBa)) {
                    maxPerUreBa = perUreBa;
                    daymaxPerUreBa = time;
                    maxPerInBa = perInBa;
                    daymaxPerInBa = time;

                } else {
                    if (maxPerUreBa > perUreBa) {
                        maxPerUreBa = perUreBa;
                        daymaxPerUreBa = time;
                    }
                    if (maxPerInBa < perInBa) {
                        maxPerInBa = perInBa;
                        daymaxPerInBa = time;
                    }
                }


            }

            top20 = Object.values(top20Dic);
            top20 = top20.sort((a, b) => a.y - b.y).slice(0, 19)

            top20Invest = Object.values(top20DicInvest);
            top20Invest = top20Invest.sort((a, b) => b.y - a.y).slice(0, 19)
        }



        App.dataInvest = top20Invest
        var model1 = new Lab_results();

        var out = await model1.read({ [LAB_RESULT_ACCOUNT]: accountId, [LAB_RESULT_STATUS]: [LAB_RESULT_STATUS_STOPLOSS] });
        if (out['result']) {
            out = out['data'];
            let outT = structuredClone(out)

            for (let i in out) {
                let time = Number(out[i][LAB_RESULT_SELL_TIME]) - 60000;
                if (SLBalane[time]) {
                    out[i]['balance'] = SLBalane[time]['balance']
                    out[i]['per'] = out[i][LAB_RESULT_REAL_PNL] * 100 / (Number(SLBalane[time]['balance']))



                    // debugger
                    for (const item in SLBalane) {

                        if (Number(item) > time) {
                            // debugger
                            if (Number(SLBalane[item]['balance']) >= Number(SLBalane[time]['balance'])) {
                                out[i]['time_reach'] = item
                                out[i]['balance_reach'] = SLBalane[item]['balance']

                                break
                            }

                        }
                    }


                }


            }
            
            outT.sort(function (a, b) { return a.lab_result_sell_time - b.lab_result_sell_time })

            for (let i in outT) {
                
                if (i == 0) {
                    let time = Number(outT[i][LAB_RESULT_SELL_TIME]) - 60000;


                    if (SLBalane[time]) {
                        outT[i]['balance'] = SLBalane[time]['balance']
                        outT[i]['balancePre'] = SLBalane[time]['balance'] + Number(outT[i][LAB_RESULT_REAL_PNL])
                        outT[i]['timePre'] = outT[i][LAB_RESULT_SELL_TIME]
                        outT[i]['perT'] = outT[i][LAB_RESULT_REAL_PNL] * 100 / (Number(SLBalane[time]['balance']))

                        for (const item in SLBalane) {

                            if (Number(item) > time) {
                                if (Number(SLBalane[item]['balance']) >= Number(SLBalane[time]['balance'])) {
                                    outT[i]['time_reach'] = item
                                    outT[i]['balance_reach'] = SLBalane[item]['balance']

                                    break
                                }

                            }
                        }


                    }
                }else{
                    // debugger

                    let timeNow = Number(outT[i][LAB_RESULT_SELL_TIME]) ;
                    let timeNowSL = Number(outT[i][LAB_RESULT_SELL_TIME]) - 60000;
               
                    let isLoop = true
                    let step = 1
                    while(isLoop){
                        if(outT[i - step]['time_reach']){
                            
                            isLoop = false
                        }else{

                            step += 1
                        }
                        
                    }
                    let timePrevious = Number(outT[i - step]['time_reach'])
                    
                    if(timeNow < timePrevious){
                        
                        if(SLBalane[timeNowSL]){
                            
                            let balancePre = SLBalane[timeNowSL]['balance'] + Number(outT[i ][LAB_RESULT_REAL_PNL])
                            if(balancePre < Number(outT[i - step]['balancePre']) ){
                                // debugger    
                                outT[i - step]['balancePre'] = balancePre
                                outT[i - step]['timePre'] = outT[i][LAB_RESULT_SELL_TIME]
                            }
                        }
                    }else{
                        if (SLBalane[timeNowSL]) {
                            outT[i]['balance'] = SLBalane[timeNowSL]['balance']
                            outT[i]['balancePre'] = SLBalane[timeNowSL]['balance'] + Number(outT[i][LAB_RESULT_REAL_PNL])
                            outT[i]['timePre'] = outT[i][LAB_RESULT_SELL_TIME]
                            
                            outT[i]['perT'] = outT[i][LAB_RESULT_REAL_PNL] * 100 / (Number(SLBalane[timeNowSL]['balance']))
    
                            for (const item in SLBalane) {
    
                                if (Number(item) > timeNowSL) {
                                    if (Number(SLBalane[item]['balance']) >= Number(SLBalane[timeNowSL]['balance'])) {
                                        outT[i]['time_reach'] = item
                                        outT[i]['balance_reach'] = SLBalane[item]['balance']
    
                                        break
                                    }
    
                                }
                            }
    
    
                        }
                    }
                    
                    
                
                }



            }
            console.log(outT)
            App.dataStopLossBalance2 = outT
        }


        App.dataStopLossBalance = out
    

        var FlagSL = [];

        out.map(item => {
            FlagSL.push({
                x: item[LAB_RESULT_SELL_TIME],      // Point where the flag appears
                title: item['per'].toFixed(2) + '%', // Title of flag displayed on the chart 
                text: item['per'].toFixed(2) + '%'  // Text displayed when the flag are highlighted.
            })
        })
        App.dataMax = top20;


        let temp = top20.sort(function (a, b) { return a.x - b.x })


        if (result.length !== 0) {
            let timeT = []

            temp.map(item => {

                if (item['y'] < -10 / 100) {
                    timeT.push(item['x'])

                }
            })



            for (let i = 0; i < result.length - 1; i++) {

                let aIndex = timeT.indexOf(result[i][LAB_TRACK_BL_TIME])

                // if (aIndex > -1) {

                //     if (i !== 0 && i !== result.length - 1) {

                //         for (let y = i + 1; y < result.length - 1; y++) {

                //             var NowPerUreBa = Number(result[y][LAB_TRACK_BL_UNREALIZE]) / Number(result[y][LAB_TRACK_BL_BALANCE]);
                //             var NextPerUreBa = Number(result[y + 1][LAB_TRACK_BL_UNREALIZE]) / Number(result[y + 1][LAB_TRACK_BL_BALANCE]);

                //             if (NextPerUreBa - NowPerUreBa < 0) {
                //                 temp[aIndex]['right_y'] = NowPerUreBa
                //                 temp[aIndex]['right_x'] = result[y][LAB_TRACK_BL_TIME]
                //                 break
                //             }




                //         }
                //         for (let y = i - 1; y > 0; y--) {

                //             var NowPerUreBa = Number(result[y][LAB_TRACK_BL_UNREALIZE]) / Number(result[y][LAB_TRACK_BL_BALANCE]);
                //             var NextPerUreBa = Number(result[y - 1][LAB_TRACK_BL_UNREALIZE]) / Number(result[y - 1][LAB_TRACK_BL_BALANCE]);

                //             if (NowPerUreBa - NextPerUreBa  >= 0) {

                //                 temp[aIndex]['left_y'] = NowPerUreBa
                //                 temp[aIndex]['left_x'] = result[y][LAB_TRACK_BL_TIME]
                //                 break
                //             }




                //         }

                //     }

                // }

                if (aIndex > -1) {

                    if (i !== 0 && i !== result.length - 1) {

                        for (let y = i + 1; y < result.length - 1; y++) {

                            var NowPerUreBa = Number(result[y][LAB_TRACK_BL_UNREALIZE]) / Number(result[y][LAB_TRACK_BL_BALANCE]);
                            var NextPerUreBa = -10 / 100;

                            if (NextPerUreBa <= NowPerUreBa) {
                                temp.map(item => {
                                    if (item['x'] == result[i][LAB_TRACK_BL_TIME]) {
                                        item['right_y'] = NowPerUreBa
                                        item['right_x'] = result[y][LAB_TRACK_BL_TIME]
                                    }
                                })

                                break
                            }




                        }
                        for (let y = i - 1; y > 0; y--) {

                            var NowPerUreBa = Number(result[y][LAB_TRACK_BL_UNREALIZE]) / Number(result[y][LAB_TRACK_BL_BALANCE]);
                            var NextPerUreBa = -10 / 100;

                            if (NextPerUreBa <= NowPerUreBa) {

                                temp.map(item => {
                                    if (item['x'] == result[i][LAB_TRACK_BL_TIME]) {
                                        item['left_y'] = NowPerUreBa
                                        item['left_x'] = result[y][LAB_TRACK_BL_TIME]
                                    }
                                })

                                // temp[aIndex]['left_y'] = NowPerUreBa
                                // temp[aIndex]['left_x'] = result[y][LAB_TRACK_BL_TIME]
                                break
                            }




                        }

                    }

                }

            }


        }


        var top20Flag = [];

        temp.map(item => {
            top20Flag.push({
                x: item.x,      // Point where the flag appears
                title: (item.y * 100).toFixed(2) + "%", // Title of flag displayed on the chart 
                text: (item.y * 100).toFixed(2) + "%"  // Text displayed when the flag are highlighted.
            }
            )
        })



        // console.log(top20Flag)
        App.dataMax = temp;
        // console.log(temp)

        this.setState({
            maxPerInBa: (maxPerInBa * 100).toFixed(2),
            maxPerUreBa: (maxPerUreBa * 100).toFixed(2),
            daymaxPerInBa,
            daymaxPerUreBa,
            Options: {
                series: [
                    {
                        data: balanceDatas
                    },
                    {
                        data: investDatas
                    },
                    {
                        data: unrealizeDatas
                    },
                    {
                        data: marginBalanceDatas
                    },
                    {
                        data: top20Flag
                    },
                    {
                        data: FlagSL
                    }
                ]
            }

        })

    }




}

export default AccountBalanceChart;
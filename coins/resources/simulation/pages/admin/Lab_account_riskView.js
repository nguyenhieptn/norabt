import React, { Component } from 'react';
import InputV2 from '../../components/Input_v2/Input';
import Lab_account from '../../model/admin/Lab_account'

import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official';
import Lab_track_blance from '../../model/admin/Lab_track_balance';
import Lab_results from '../../model/admin/Lab_results';

import BalanceMaxModal from '../../components/admin/BalanceMaxModal';
import AccountStopLossModal from '../../components/admin/AccountStopLossModal';
import AccountOrderModal from '../../components/admin/AccountOrderModal';
import InvestMaxModal from '../../components/admin/InvestMaxModal';
class Lab_account_riskView extends Component {

    constructor(props) {
        super(props);

        this.state = {
            accountOpt: [],
            data: {},
            dataTemp: {},

            maxPerInBa: 0,
            daymaxPerInBa: 0,
            maxPerUreBa: 0,
            daymaxPerUreBa: 0,


            optSLAccount : {},

            Options: {

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
                        color : 'red'
                    }

                ]
            }
        }

        this.accountModel = new Lab_account();



        this.updateChartWidth = this.updateChartWidth.bind(this);
        Highcharts.setOptions({
            time: {
                timezoneOffset: moment().utcOffset(),
                useUTC: false
            }
        });
    }

    componentDidMount() {


        this.updateChartWidth();
        this.resize_ob = new ResizeObserver((entries) => {
            this.updateChartWidth()
        });
        this.resize_ob.observe(this.chartContainer);

        this.getLabAccount()

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
                        width: this.chartContainer.clientWidth,
                    }

                }
            })
        }, 500);
    }


    getLabAccount() {
        let opt = []
        let optSLAccount = {}
        this.accountModel.read().then(res => {

            if (res['result']) {
                res['data'].map(item => {
                    opt.unshift({
                        'value': item[LAB_ACCOUNT_ID],
                        'label': item[LAB_ACCOUNT_NAME]
                    })

                    optSLAccount[item[LAB_ACCOUNT_ID]] = item[LAB_ACCOUNT_NAME]
                })
            }

        })

        this.setState({
            accountOpt: opt,
            optSLAccount
        });
    }

    getNameAccount(accountId) {

        for (let index = 0; index < this.state.accountOpt.length; index++) {
            const item = this.state.accountOpt[index];
            if (item['value'] == accountId) {
                return item['label']
            }

        }

    }


    handleData() {
        let valueArr = [this.input1.getValue(), this.input2.getValue(), this.input3.getValue(), this.input4.getValue(), this.input5.getValue()]
        let data = {}

        Object.keys(this.state.dataTemp).map(k => {

            if (valueArr.includes(Number(k))) {
                data[k] = this.state.dataTemp[k]
            }
        })

        let tran1 = {}
        let tran2 = {}
        let tran3 = {}
        let tran4 = {}
        let tran5 = {}
        let timeUqi = []
        Object.keys(data).map((accountId, index) => {
            let dataAccountId = data[accountId]

            dataAccountId.map(item => {
                let time = Number(item[LAB_TRACK_BL_TIME]);

                if (!timeUqi.includes(time)) {
                    timeUqi.push(time)
                }

                if (index == 0) {
                    tran1[time] = {
                        [LAB_TRACK_BL_TIME]: time,
                        [LAB_TRACK_BL_BALANCE]: item[LAB_TRACK_BL_BALANCE],
                        [LAB_TRACK_BL_INVEST]: item[LAB_TRACK_BL_INVEST],
                        [LAB_TRACK_BL_MARGIN_BL]: item[LAB_TRACK_BL_MARGIN_BL],
                        [LAB_TRACK_BL_UNREALIZE]: item[LAB_TRACK_BL_UNREALIZE],
                    }
                } else if (index == 1) {
                    tran2[time] = {
                        [LAB_TRACK_BL_TIME]: time,
                        [LAB_TRACK_BL_BALANCE]: item[LAB_TRACK_BL_BALANCE],
                        [LAB_TRACK_BL_INVEST]: item[LAB_TRACK_BL_INVEST],
                        [LAB_TRACK_BL_MARGIN_BL]: item[LAB_TRACK_BL_MARGIN_BL],
                        [LAB_TRACK_BL_UNREALIZE]: item[LAB_TRACK_BL_UNREALIZE],
                    }
                } else if (index == 2) {
                    tran3[time] = {
                        [LAB_TRACK_BL_TIME]: time,
                        [LAB_TRACK_BL_BALANCE]: item[LAB_TRACK_BL_BALANCE],
                        [LAB_TRACK_BL_INVEST]: item[LAB_TRACK_BL_INVEST],
                        [LAB_TRACK_BL_MARGIN_BL]: item[LAB_TRACK_BL_MARGIN_BL],
                        [LAB_TRACK_BL_UNREALIZE]: item[LAB_TRACK_BL_UNREALIZE],
                    }
                } else if (index == 3) {
                    tran4[time] = {
                        [LAB_TRACK_BL_TIME]: time,
                        [LAB_TRACK_BL_BALANCE]: item[LAB_TRACK_BL_BALANCE],
                        [LAB_TRACK_BL_INVEST]: item[LAB_TRACK_BL_INVEST],
                        [LAB_TRACK_BL_MARGIN_BL]: item[LAB_TRACK_BL_MARGIN_BL],
                        [LAB_TRACK_BL_UNREALIZE]: item[LAB_TRACK_BL_UNREALIZE],
                    }
                } else if (index == 4) {
                    tran5[time] = {
                        [LAB_TRACK_BL_TIME]: time,
                        [LAB_TRACK_BL_BALANCE]: item[LAB_TRACK_BL_BALANCE],
                        [LAB_TRACK_BL_INVEST]: item[LAB_TRACK_BL_INVEST],
                        [LAB_TRACK_BL_MARGIN_BL]: item[LAB_TRACK_BL_MARGIN_BL],
                        [LAB_TRACK_BL_UNREALIZE]: item[LAB_TRACK_BL_UNREALIZE],
                    }
                }



            })
        })
        timeUqi.sort(function (a, b) { return a - b })


        let lastBalance = {
            tran1: 0,
            tran2: 0,
            tran3: 0,
            tran4: 0,
            tran5: 0,
        }
        let lastMarginBalance = {
            tran1: 0,
            tran2: 0,
            tran3: 0,
            tran4: 0,
            tran5: 0,
        }
        let out = []
        timeUqi.map(t => {
            // debugger
            let totalBalnace = 0
            let totalInvest = 0
            let totalMarginBalnce = 0
            let totalUrePro = 0

            if (tran1[t]) {
                totalBalnace += tran1[t][LAB_TRACK_BL_BALANCE]
                lastBalance['tran1'] = tran1[t][LAB_TRACK_BL_BALANCE]

                totalInvest += tran1[t][LAB_TRACK_BL_INVEST]
                totalMarginBalnce += tran1[t][LAB_TRACK_BL_MARGIN_BL]
                lastMarginBalance['tran1'] = tran1[t][LAB_TRACK_BL_MARGIN_BL]
                totalUrePro += tran1[t][LAB_TRACK_BL_UNREALIZE]
            } else {
                if (lastBalance['tran1'] > 0) {
                    totalBalnace += lastBalance['tran1']
                }
                if (lastMarginBalance['tran1'] > 0) {
                    totalMarginBalnce += lastMarginBalance['tran1']
                }
            }
            if (tran2[t]) {
                totalBalnace += tran2[t][LAB_TRACK_BL_BALANCE]
                lastBalance['tran2'] = tran2[t][LAB_TRACK_BL_BALANCE]

                totalInvest += tran2[t][LAB_TRACK_BL_INVEST]
                totalMarginBalnce += tran2[t][LAB_TRACK_BL_MARGIN_BL]
                lastMarginBalance['tran2'] = tran2[t][LAB_TRACK_BL_MARGIN_BL]
                totalUrePro += tran2[t][LAB_TRACK_BL_UNREALIZE]
            } else {
                if (lastBalance['tran2'] > 0) {
                    totalBalnace += lastBalance['tran2']
                }
                if (lastMarginBalance['tran2'] > 0) {
                    totalMarginBalnce += lastMarginBalance['tran2']
                }
            }
            if (tran3[t]) {
                totalBalnace += tran3[t][LAB_TRACK_BL_BALANCE]
                lastBalance['tran3'] = tran3[t][LAB_TRACK_BL_BALANCE]

                totalInvest += tran3[t][LAB_TRACK_BL_INVEST]
                totalMarginBalnce += tran3[t][LAB_TRACK_BL_MARGIN_BL]
                lastMarginBalance['tran3'] = tran3[t][LAB_TRACK_BL_MARGIN_BL]
                totalUrePro += tran3[t][LAB_TRACK_BL_UNREALIZE]
            } else {
                if (lastBalance['tran3'] > 0) {
                    totalBalnace += lastBalance['tran3']
                }
                if (lastMarginBalance['tran3'] > 0) {
                    totalMarginBalnce += lastMarginBalance['tran3']
                }
            }
            if (tran4[t]) {
                totalBalnace += tran4[t][LAB_TRACK_BL_BALANCE]
                lastBalance['tran4'] = tran4[t][LAB_TRACK_BL_BALANCE]

                totalInvest += tran4[t][LAB_TRACK_BL_INVEST]
                totalMarginBalnce += tran4[t][LAB_TRACK_BL_MARGIN_BL]
                lastMarginBalance['tran4'] = tran4[t][LAB_TRACK_BL_MARGIN_BL]
                totalUrePro += tran4[t][LAB_TRACK_BL_UNREALIZE]
            } else {
                if (lastBalance['tran4'] > 0) {
                    totalBalnace += lastBalance['tran4']
                }
                if (lastMarginBalance['tran4'] > 0) {
                    totalMarginBalnce += lastMarginBalance['tran4']
                }
            }
            if (tran5[t]) {
                totalBalnace += tran5[t][LAB_TRACK_BL_BALANCE]
                lastBalance['tran5'] = tran5[t][LAB_TRACK_BL_BALANCE]

                totalInvest += tran5[t][LAB_TRACK_BL_INVEST]
                totalMarginBalnce += tran5[t][LAB_TRACK_BL_MARGIN_BL]
                lastMarginBalance['tran5'] = tran5[t][LAB_TRACK_BL_MARGIN_BL]
                totalUrePro += tran5[t][LAB_TRACK_BL_UNREALIZE]
            } else {
                if (lastBalance['tran5'] > 0) {
                    totalBalnace += lastBalance['tran5']
                }
                if (lastMarginBalance['tran5'] > 0) {
                    totalMarginBalnce += lastMarginBalance['tran5']
                }
            }

            let add = {
                [LAB_TRACK_BL_TIME]: t,
                [LAB_TRACK_BL_BALANCE]: totalBalnace,
                [LAB_TRACK_BL_INVEST]: totalInvest,
                [LAB_TRACK_BL_MARGIN_BL]: totalMarginBalnce,
                [LAB_TRACK_BL_UNREALIZE]: totalUrePro,
            }

            out.push(add)
        })

        this.calChart(out, Object.keys(data))

    }


    async calChart(result, accountAr) {
        // console.log(result)

        App.loading(true, `Caling data`)



        var investDatas = [];
        var unrealizeDatas = [];
        var marginBalanceDatas = [];
        var balanceDatas = [];




        let SLBalane = {}

        var maxPerUreBa;
        var daymaxPerUreBa;
        var maxPerInBa;
        var daymaxPerInBa;

        var top20Dic = {};
        var top20 = []

        var top20DicInvest = {};
        var top20Invest = [];



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




        App.dataInvest = top20Invest


        let dataStopLossBalance = []
        var model1 = new Lab_results();
        for (let i = 0; i < accountAr.length; i++) {
            const accountId = accountAr[i];

            var out = await model1.read({ [LAB_RESULT_ACCOUNT]: accountId, [LAB_RESULT_STATUS]: [LAB_RESULT_STATUS_STOPLOSS] });

            if (out['result']) {
                out = out['data'];
                for (let i in out) {
                    let time = Number(out[i][LAB_RESULT_SELL_TIME]) - 60000;
                    if (SLBalane[time]) {
                        out[i]['balance'] = SLBalane[time]['balance']
                        out[i]['per'] = out[i][LAB_RESULT_REAL_PNL] * 100 / (Number(SLBalane[time]['balance']))

                        for (const item in SLBalane) {

                            if (Number(item) > time) {
                                if (Number(SLBalane[item]['balance']) >= Number(SLBalane[time]['balance'])) {
                                    out[i]['time_reach'] = item
                                    out[i]['balance_reach'] = SLBalane[item]['balance']

                                    break
                                }

                            }
                        }

                    }


                }

                dataStopLossBalance =  dataStopLossBalance.concat(out)
            }

        }


        App.dataStopLossBalance = dataStopLossBalance

        var FlagSL = [];

        dataStopLossBalance.map(item => {
            FlagSL.push({
                x: item[LAB_RESULT_SELL_TIME],      // Point where the flag appears
                title: item['per'].toFixed(2) + '%' , // Title of flag displayed on the chart 
                text:item['per'].toFixed(2) + '%'  // Text displayed when the flag are highlighted.
            })
        })

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

        App.dataMax = temp;

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

        App.loading(false)
    }



    async loadData() {
        let valueArr = [this.input1.getValue(), this.input2.getValue(), this.input3.getValue(), this.input4.getValue(), this.input5.getValue()]


        for (let i = 0; i < valueArr.length; i++) {
            const accountId = valueArr[i];
            if (accountId != '') {

                if (!this.state.dataTemp[accountId]) {
                    var model = new Lab_track_blance();

                    let name = this.getNameAccount(accountId)

                    App.loading(true, `Load data account ${name}`)
                    var result = await model.read({ [LAB_TRACK_BL_ACCOUNT]: accountId }, false, {});

                    App.loading(false)

                    if (result['result']) {
                        result = result['data'];
                        if (result.length == 0) {
                            showLog('No data or balance tracking is disabled');

                        }
                        let dataT = this.state.dataTemp

                        dataT[accountId] = result

                        this.setState({
                            dataTemp: dataT
                        });


                    }
                }
            }
        }

        this.handleData()


        // this.renderChartChild()


    }

    renderChartChild(){
        let valueArr = [this.input1.getValue(), this.input2.getValue(), this.input3.getValue(), this.input4.getValue(), this.input5.getValue()]

        console.log(valueArr)
    }

    render() {
        return (
            <div >
                <div style={{ display: 'flex', flexWrap: 'wrap' }}>
                    <div className='mr-3 mt-3'>
                        <InputV2
                            className='input '
                            placeholder={lang('--Select Account -- ')}
                            type="select"
                            ref={c => this.input1 = c}
                            Options={this.state.accountOpt}

                        >
                        </InputV2>
                    </div>
                    <div className='mr-3 mt-3'>
                        <InputV2
                            className='input '
                            placeholder={lang('--Select Account -- ')}
                            type="select"
                            ref={c => this.input2 = c}
                            Options={this.state.accountOpt}

                        >
                        </InputV2>
                    </div>
                    <div className='mr-3 mt-3'>
                        <InputV2
                            className='input '
                            placeholder={lang('--Select Account -- ')}
                            type="select"
                            ref={c => this.input3 = c}
                            Options={this.state.accountOpt}

                        >
                        </InputV2>
                    </div>
                    <div className='mr-3 mt-3'>
                        <InputV2
                            className='input '
                            placeholder={lang('--Select Account -- ')}
                            type="select"
                            ref={c => this.input4 = c}
                            Options={this.state.accountOpt}

                        >
                        </InputV2>
                    </div>
                    <div className='mr-3 mt-3'>
                        <InputV2
                            className='input '
                            placeholder={lang('--Select Account -- ')}
                            type="select"
                            ref={c => this.input5 = c}
                            Options={this.state.accountOpt}
                            OnChange={(value, obj) => {
                                console.log(value)
                            }}
                        >
                        </InputV2>
                    </div>

                    <div className='mt-3'>
                        <button type="button" className="btn btn-primary" onClick={() => this.loadData()}>Load Data</button>
                    </div>



                </div>

                <div className='box_shadow' ref={c => this.chartContainer = c} style={{ position: 'relative', marginTop: 15, padding: 5 }}>

                    <div style={{textAlign : 'center'}}>
                        <b>Total</b> 
                    </div>
                    <div style={{ display: 'flex', position: 'absolute', top: '20px', right: '30px', zIndex: 1000 }}>
                        <div className='mr-3 '>
                            <div>
                                {/* <span> Max Unrealize profit / Balance : </span> */}
                                <span> Max Drawdown : </span>
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
                        }}>DD</button>

                        <button type="button" className="btn btn-info mr-3" onClick={() => {

                            this.InvestMaxModal.modal();
                            this.InvestMaxModal.loadOrigin();
                        }}>MI</button>


                        <button type="button" className="btn btn-info mr-3" onClick={() => {

                            this.AccountStopLossModal.modal('show' , this.state.optSLAccount);
                            this.AccountStopLossModal.loadOrigin();
                        }}>SL</button>


                        {/* <button type="button" className="btn btn-info mr-3" onClick={() => {

                                this.AccountOrderModal.modal();
                                this.AccountOrderModal.loadOrigin(this.state.account[LAB_ACCOUNT_ID]);
                            }}>Order</button>  */}
                    </div>
                    <HighchartsReact
                        ref={c => this.chart = c}
                        highcharts={Highcharts}
                        options={this.state.Options}
                        constructorType={'stockChart'}
                    />




                </div>

                {/* {

                    this.renderChartChild()
                } */}


                <BalanceMaxModal ref={c => this.BalanceMaxModal = c} title='Max Unrealize profit / Balance'></BalanceMaxModal>
                <InvestMaxModal ref={c => this.InvestMaxModal = c} title="Max Invest / Balance"></InvestMaxModal>
                <AccountStopLossModal ref={c => this.AccountStopLossModal = c} title='SL'></AccountStopLossModal>
                {/* <AccountOrderModal ref={c => this.AccountOrderModal = c} title='Order' ></AccountOrderModal> */}
            </div>
        );
    }
}

export default Lab_account_riskView;
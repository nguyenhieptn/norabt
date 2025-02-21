
import React, { Component } from 'react';
import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official'

import Testnet_results from '../../../model/admin/Testnet_results';
import Watchlist from '../../../model/admin/Watchlist';
import Actions from '../../../model/admin/Actions';

import Input from '../../input/Input';
import Testnet_campaign from '../../../model/admin/Testnet_campaign';
class ChartProfitPerDay extends Component {
    constructor(props) {
        super(props);
        this.state = {
            start: '',
            stop: '',
            ALL: true,
            coin: [],
            selected: {},
            dateSeleted: 'day',
            Options: {
                chart: {}

                ,
                exporting: {
                    enabled: false
                },
                title: {
                    text: '<b>TOTAL PROFIT </b>',
                },

                xAxis: {

                },
                yAxis: [
                    {
                        // title: {
                        //     text: '<b>USDT</b>'
                        // },
                        startOnTick: true,
                        lineWidth: 1,

                        labels: {
                            align: 'left'
                        },


                    },

                    {
                        // title: {
                        //     text: '<b>%</b>'
                        // },
                        startOnTick: true,
                        opposite: false,
                        lineWidth: 2,

                    }
                ],

                chart: {
                    // height: (8 / 16 * 73) + '%'
                    height: 500,

                },
                legend: {
                    enabled: true,

                },
                navigator: {
                    enabled: false
                },
                scrollbar: {
                    enabled: false
                },
                plotOptions: {
                    series: {
                        dataLabels: {
                            enabled: true
                        },
                        maxPointWidth: 100
                    },
                    // column: {
                    //     zones: [{
                    //         value: 0,
                    //         color: 'red'
                    //     }, {
                    //         color: '#007bff'
                    //     }]
                    // }

                },
                tooltip: {
                    padding: 1,
                    style: {
                        fontSize: '10px',
                    }

                },

                rangeSelector: {

                    buttonPosition: {
                        align: 'left',
                        // x: '0',
                        y: '-1',
                    },

                    allButtonsEnabled: true,
                    buttons:
                        [
                            {
                                text: '3d',
                                type: 'day',
                                count: 3,

                            },
                            {
                                text: '1w',
                                type: 'week',
                                count: 1,

                            },
                            {
                                text: '1m',
                                type: 'month',
                                count: 1,

                            },
                            {
                                text: '3m',
                                type: 'month',
                                count: 3,
                            },
                            {
                                text: '6m',
                                type: 'month',
                                count: 6,

                            }, {
                                text: '1y',
                                type: 'year',
                                count: 1,

                            }, {
                                type: 'all',
                                text: 'All'
                            },
                        ],
                    inputEnabled: false,
                    // selected: 0,
                    buttonSpacing: 10,
                },
                series: [

                    {
                        type: 'column',
                        name: '$',
                        data: [],

                    },

                    {
                        yAxis: 1,
                        type: 'spline',
                        color: 'limegreen',
                        name: '%',
                        data: [],

                    }

                ]
            }
        }
        this.updateChartWidth = this.updateChartWidth.bind(this);

        this.colors = {};

    }
    componentDidMount() {
        var wlModel = new Watchlist();
        wlModel.getWatchlist(res => {
            if (res) {
                Object.values(res).map(item => {
                    var color = this.getRandomColor();
                    coin.push({ name: item[WL_SYMBOL], color: color });
                    selected.push(item[WL_SYMBOL]);
                })
                this.setState({ coin, selected, temponary: selected }, () => this.getData(true))
            }
        })

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
    getRandomColor(item) {
        if (isset(this.colors[item])) return this.colors[item];
        var letters = '0123456789ABCDEF';
        var color = '#';
        for (var i = 0; i < 6; i++) {
            color += letters[Math.floor(Math.random() * 16)];
        }
        this.colors[item] = color;
        return this.colors[item];
    }
    render() {
        return (
            <>
                <div className='p-col-12 p-md-12 ' >
                    <div className='box_shadow ' ref={c => this.chartContainer = c} style={{ position: 'relative' }}>

                        <div className='cus-hide' style={{ display: 'flex', alignItems: 'center', padding: 7, position: 'absolute', zIndex: 1, top: '35px', right: '30px' }}>

                            <Input ref={c => this.startInput = c} placeholder="Start Time" className='input' struct={{
                                [INPUT_TYPE]: 'date',
                                [INPUT_DEFAULT]: this.state.start != '' ? (this.state.start / 1000) : '',
                                [INPUT_ONCHANGE_BLUR]: (e, obj) => { this.setState({ start: obj.getValue() * 1000 }, () => this.getData(this.state.dateSeleted)) }
                            }}></Input>

                            &nbsp;

                            <Input ref={c => this.stopInput = c} placeholder="Stop Time" className='input' struct={{
                                [INPUT_TYPE]: 'date',
                                [INPUT_DEFAULT]: this.state.stop != '' ? (this.state.stop / 1000) : '',
                                [INPUT_ONCHANGE_BLUR]: (e, obj) => {
                                    this.setState({ stop: obj.getValue() * 1000 }, () => {
                                        this.getData(this.state.dateSeleted);

                                    })
                                }
                            }}></Input>
                            &nbsp;

                            <div>
                                <select className='input' onChange={(e) => { this.getData(e.target.value); this.setState({ dateSeleted: e.target.value }); }}>
                                    <option value="day" >Day</option>
                                    <option value="week">Week</option>
                                    <option value="month">Month</option>

                                </select>
                            </div>

                        </div>


                        <HighchartsReact
                            highcharts={Highcharts}
                            options={this.state.Options}
                            constructorType={'stockChart'}
                        />


                    </div>

                </div>
            </>
        );
    }

    async getData(option) {

        var a = {
            'day': 86400 * 1000,
            'week': 604800 * 1000,
            'month': 2592000 * 1000,
        };

        var distance = a[option];


        var resultModel = new Testnet_results();
        var symbols = {};

        var campaignModal = new Testnet_campaign();
        var campaignData = await campaignModal.read({ [TESTNET_ACCOUNT]: App.accountSelectorTestnet.selected() });
        var totalBuget = 0;
        if (campaignData['data']) {
            campaignData = campaignData['data'];

            for (let i in campaignData) {
                totalBuget += campaignData[i][TESTNET_BUDGET];



            }
        }


        // resultModel.getAll().then(res => {
        resultModel.getByAccountTestnet(App.accountSelectorTestnet.selected()).then(res => {

            if (res['data']) {
                res = res['data'];


                var data = [];
                var percent = [];

                // var limitTime = Number(moment().startOf('day').format('x'));


                // var limitTime = this.state.stop == '' ? Number(moment().startOf('day').format('x')) : this.state.stop;
                var limitTime = this.state.stop == '' ? Number(moment().startOf(option).format('x')) : this.state.stop;
                if (option == 'week') {
                    limitTime = this.state.stop == '' ? Number(moment().startOf(option).format('x')) + 86400000 : this.state.stop;
                }
                for (let i in res) {



                    if (res[i][TESTNET_RESULT_PENDING] == 1) continue;

                    var symbol = res[i][TESTNET_RESULT_SYMBOL];
                    symbols[symbol] = true;

                    if (!this.state.selected[symbol] && !this.state.ALL) continue;

                    var tempTime = Number(res[i][TESTNET_RESULT_SELL_TIME])
                    if (tempTime == 0) continue;
                    if (this.state.start !== '') {
                        if (tempTime < this.state.start) continue;
                    }
                    // var realPNL = Number(res[i][TESTNET_RESULT_REAL_PROFIT]) - Number(res[i][TESTNET_RESULT_COMMIT]);
                    var realPNL = Number(res[i][TESTNET_RESULT_REAL_PNL]);
                    // var realPNL =  1;

                    if (tempTime >= limitTime && isset(data[0])) {
                        // var xvalue = moment(limitTime, 'x').format("DD/MM/YYYY");
                        var xvalue = limitTime;
                        if (res[i][TESTNET_RESULT_PENDING] == 0 && res[i][TESTNET_RESULT_STATUS] != TESTNET_RESULT_STATUS_CANCLE) {
                            var yvaluePercent = Number(res[i][TESTNET_RESULT_PROFIT]) + Number(percent[0].y);
                            var yvalue = realPNL + Number(data[0].y);
                            data[0].y = Number(yvalue.toFixed(3));
                            data[0].color = yvalue > 0 ? 'dodgerblue' : 'red';
                            percent[0].y = Number(yvaluePercent.toFixed(3))

                        }
                    } else {
                        while (tempTime < limitTime) {
                            // limitTime -= 86400 * 1000;
                            if (option == 'month') {

                                distance = (new Date(moment(limitTime).year(), moment(limitTime).month(), 0)).getDate() * 86400000;

                            }
                            limitTime -= distance;

                        }
                        // var xvalue = moment(limitTime, 'x').format("DD/MM/YYYY");
                        var xvalue = limitTime;
                        if (res[i][TESTNET_RESULT_PENDING] == 0 && res[i][TESTNET_RESULT_STATUS] != TESTNET_RESULT_STATUS_CANCLE) {
                            var yvaluePercent = Number(res[i][TESTNET_RESULT_PROFIT]);
                            var yvalue = realPNL;
                        } else {
                            var yvalue = 0;
                            var yvaluePercent = 0;
                        }

                        data.unshift({
                            x: xvalue,
                            y: Number(yvalue.toFixed(3)),
                            color: yvalue > 0 ? 'dodgerblue' : 'red'
                        })

                        percent.unshift({
                            x: xvalue,
                            y: Number(yvaluePercent.toFixed(3))
                        })
                    }

                }

                console.log(totalBuget)

                var coin = Object.keys(symbols);

                var percent1 = [];

                data.map(item => {
                    percent1.push({
                        x: item.x,
                        y: Number(((item.y / totalBuget) * 100).toFixed(4))
                    })
                });






                this.setState({
                    coin: coin,
                    Options: {
                        series: [
                            {
                                data: data,
                            },

                            {
                                data: percent1,
                            }
                        ]
                        // xAxis: {
                        //     categories
                        // }

                    }
                })
            }
        })


        // for (var i = 0; i <= 14; i++) {
        //     var temponary = moment().subtract(i, 'days').format("DD/MM/YYYY");
        //     categories.unshift(temponary);

        //     var totalProfit = 0;

        //     Object.values(App.lab[i]).map(data => {
        //         var index = this.state.selected.indexOf(data.lab_symbol);
        //         if (index > -1) {
        //             if (data[LAB_PENDING] == 0) {
        //                 totalProfit += Number(data[LAB_PROFIT]) - 0.08;
        //             }
        //         }

        //     })

        //     series.unshift(Number(totalProfit.toFixed(4)));

        // }






    }
}

export default ChartProfitPerDay;
import React, { Component } from 'react';
import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official'

import Input from '../../input/Input';

import Testnet_results from '../../../model/admin/Testnet_results';
import Watchlist from '../../../model/admin/Watchlist';
import Actions from '../../../model/admin/Actions';
class ChartProfitPerDay extends Component {
    constructor(props) {
        super(props);
        this.state = {
            start: '',
            stop: '',
            ALL: true,
            coin: [],
            selected: {},
            Options: {
                chart: {}

                ,
                exporting: {
                    enabled: false
                },
                title: {
                    text: '<b>TOTAL PROFIT</b>',
                },

                xAxis: {

                },
                yAxis: [
                    {
                        startOnTick: true,
                        lineWidth: 1,
                        labels: {
                            align: 'left'
                        },
                    },
                    {
                        startOnTick: true,
                        opposite: false,
                        lineWidth: 1,
                    }
                ],

                chart: {
                    // height: (8 / 16 * 73) + '%'
                    height: 500,
                    events: {
                        redraw: () => {
                            this.CalTotalProfit()
                        },

                    }

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

    CalTotalProfit() {
        if (this.chart) {

            var arrayProfit = this.chart.chart.series[0].processedYData;

            var totalProfit = 0;
            arrayProfit.map(item => totalProfit += item);
            totalProfit = Math.round(totalProfit * 1000) / 1000;

            this.props.setTotalProfit(totalProfit);
        }
    }
    render() {
        return (
            <>
                <div className='p-col-12 p-md-12 mt-1' >
                    <div className='box_shadow ' ref={c => this.chartContainer = c} style={{ position: 'relative' }}>


                        <div className='cus-hide' style={{ display: 'flex', alignItems: 'center', padding: 7, position: 'absolute', zIndex: 1, top: '35px', right: '35px' }}>

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
                                        // if (obj.getValue() == '') this.startUpdate();
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
                            ref={c => this.chart = c}
                            highcharts={Highcharts}
                            options={this.state.Options}
                            constructorType={'stockChart'}
                        />


                    </div>

                </div>
            </>
        );
    }

    getData(option) {
        var a = {
            'day': 86400 * 1000,
            'week': 604800 * 1000,
            'month': 2592000 * 1000,
        };

        var distance = a[option];

        var resultModel = new Actions();
        var symbols = {};

        resultModel.getAll(App.accountSelector.selected()).then(res => {
            if (res['data']) {
                res = res['data'];
                var data = [];
                var percent = [];

                // var limitTime = Number(moment().startOf('day').format('x'));
                // var limitTime = this.state.stop == '' ? Number(moment().startOf('day').format('x')) : this.state.stop;
                var limitTime = this.state.stop == '' ? Number(moment().startOf(option).format('x')) : this.state.stop;
                if(option == 'week'){
                    limitTime = this.state.stop == '' ? Number(moment().startOf(option).format('x')) +86400000 : this.state.stop;
                }
                for (let i in res) {

                    if (res[i][ACTION_PENDING] == 1) continue;

                    var symbol = res[i][ACTION_SYMBOL];
                    symbols[symbol] = true;

                    if (!this.state.selected[symbol] && !this.state.ALL) continue;

                    var tempTime = Number(res[i][ACTION_SELL_TIME])

                    if (this.state.start !== '') {
                        if (tempTime < this.state.start) continue;
                    }
                    var realPNL = Number(res[i][ACTION_PNL]) - Number(res[i][ACTION_COMMIT]);

                    if (tempTime >= limitTime && isset(data[0])) {
                        // var xvalue = moment(limitTime, 'x').format("DD/MM/YYYY");
                        var xvalue = limitTime;
                        if (res[i][ACTION_PENDING] == 0 && res[i][ACTION_STATUS] != ACTION_STATUS_CANCLE) {
                            var yvaluePercent = Number(res[i][ACTION_TOTALPROFIT]) + Number(percent[0].y);
                            var yvalue = realPNL + Number(data[0].y);
                            data[0].y = Number(yvalue.toFixed(3));
                            data[0].color = yvalue > 0 ? 'dodgerblue' : 'red';
                            percent[0].y = Number(yvaluePercent.toFixed(3))

                        }
                    } else {
                        while (tempTime < limitTime) {
                            // limitTime -= 86400 * 1000;
                            if(option == 'month'){

                                distance = (new Date( moment(limitTime).year(),  moment(limitTime).month() , 0)).getDate() * 86400000;
                               
                            }
                            limitTime -= distance;
                        }
                        // var xvalue = moment(limitTime, 'x').format("DD/MM/YYYY");
                        var xvalue = limitTime;
                        if (res[i][ACTION_PENDING] == 0 && res[i][ACTION_STATUS] != ACTION_STATUS_CANCLE) {
                            var yvaluePercent = Number(res[i][ACTION_TOTALPROFIT]);
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

                var coin = Object.keys(symbols);

                var serial = [];
                var categories = [];



                this.setState({
                    coin: coin,
                    Options: {
                        series: [
                            {
                                data: data,
                            },

                            {
                                data: percent,
                            }
                        ]
                        // xAxis: {
                        //     categories
                        // }

                    }
                })
            }
        })








    }
}

export default ChartProfitPerDay;
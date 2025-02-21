import React, { Component } from 'react';
import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official'
import Price_1s from '../../model/admin/Price_1s';
import SelectSymbol from './SelectSymbol';
import Input from '../input/Input';
import SelectStrategy from './SelectStrategy';

require('highcharts/indicators/indicators')(Highcharts);
require('highcharts/indicators/ema')(Highcharts);

class TestnetChartLine extends Component {
    constructor(props) {
        super(props);

        this.state = {

            symbol: '',
            start: get(App.parsed['start'], ''),
            stop: get(App.parsed['stop'], ''),

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

                yAxis: [
                    {
                        crosshair: true,
                        title: {
                            text: '<b></b>',
                        },

                        startOnTick: false,

                        labels: {
                            align: 'left'
                        },
                        lineWidth : 1,

                    },

                    // {
                    //     title: {
                    //         text: '<b>%</b>',

                    //     },
                    //     max: 100,
                    //     min: 0,
                    //     startOnTick: false,


                    //     opposite: false,
                    // },

                ],

                chart: {
                    height: (8 / 16 * 100) + '%',
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

                    allButtonsEnabled: true,
                    buttons:
                        [
                            {
                                text: '30M',
                                type: 'minute',
                                count: 30,

                            },
                            {
                                text: '1H',
                                type: 'hour',
                                count: 1,

                            },
                            {
                                text: '2H',
                                type: 'hour',
                                count: 2,
                            },
                            {
                                text: '6H',
                                type: 'hour',
                                count: 6,

                            }, {
                                text: '12H',
                                type: 'hour',
                                count: 12,

                            }, {
                                text: '24H',
                                type: 'hour',
                                count: 24,

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
                        name: 'Price',
                        id: "price",
                    },
                    {
                        name: 'Price Step',
                        id: "enterbase",
                        lineWidth: 0,
                        marker: {
                            enabled: true,
                            radius: 3
                        },
                        tooltip: {
                            valueDecimals: 2
                        },
                    },
                    {
                        name: 'Profit Step',
                        id: "profitbase",
                        lineWidth: 0,
                        marker: {
                            enabled: true,
                            radius: 3
                        },
                        tooltip: {
                            valueDecimals: 2
                        },
                    },
                    {
                        type: 'flags',
                        name: 'Order',
                        shape: "circlepin",
                        id: "order",
                    },
                    {

                        type: 'flags',
                        shape: 'squarepin',
                        id: "position",
                        name: "Position",
                        onSeries: 'price'
                    },
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

    }
    componentDidMount() {

        this.startUpdate();
        this.updateChartWidth();
        this.resize_ob = new ResizeObserver((entries) => {
            this.updateChartWidth()
        });
        this.resize_ob.observe(this.chartContainer);

        var symbol = localStorage.getItem('lineChartSymbol');
        if (App.parsed['symbol']) {
            var symbol = App.parsed['symbol'];
        }
        if (symbol != '' && symbol != null) {
            this.symSelector.selectSymbol(symbol);
        }

        if (App.accountSelectorTestnet) {
            App.accountSelectorTestnet.register('testnes_line_chart', () => {
                this.getData(true);
            });
        }

        setTimeout(() => this.setRangeSelector(), 3000);


    }

    startUpdate() {
        if (this.updateInterval) clearInterval(this.updateInterval);
        this.updateInterval = setInterval(() => { this.getData(false, 10, false) }, 3000);
    }

    componentWillUnmount() {
        if (this.updateInterval) clearInterval(this.updateInterval);
        if (this.resize_ob) this.resize_ob.unobserve(this.chartContainer);
        App.accountSelectorTestnet.unregister('testnes_line_chart');
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


    setRangeSelector() {

        var max = this.state.stop;
        var min = this.state.start;

        // if (max > 0 && min > 0) {
        //     this.chart.chart.xAxis[0].setExtremes(min, max);
        // } else {
        console.log('Set rangselector to 4')
        this.setState({
            Options: { rangeSelector: { selected: 0 } },
        })

        // }
    }

    render() {
        return (
            <>
                <div className='p-col-12 p-md-12 cushide' >
                    <div className='box_shadow ' ref={c => this.chartContainer = c} style={{ position: 'relative' }}>

                        <div style={{ display: 'flex', alignItems: 'center', padding: 7 }}>
                            <SelectSymbol ref={c => this.symSelector = c} onSelect={sym => {
                                this.setState({ symbol: sym }, () => {
                                    this.getData(true)
                                });
                            }}></SelectSymbol>



                            &nbsp;

                            <Input ref={c => this.startInput = c} placeholder="Start Time" className='input' struct={{
                                [INPUT_TYPE]: 'date',
                                [INPUT_DEFAULT]: this.state.start != '' ? (this.state.start / 1000) : '',
                                [INPUT_ONCHANGE_BLUR]: (e, obj) => { this.setState({ start: obj.getValue() * 1000 }, () => this.getData(true)) }
                            }}></Input>

                            &nbsp;

                            <Input ref={c => this.stopInput = c} placeholder="Stop Time" className='input' struct={{
                                [INPUT_TYPE]: 'date',
                                [INPUT_DEFAULT]:  this.state.stop != '' ? (this.state.stop / 1000) : '',
                                [INPUT_ONCHANGE_BLUR]: (e, obj) => {
                                    this.setState({ stop: obj.getValue() * 1000 }, () => {
                                        this.getData(true);
                                        if (obj.getValue() == '') this.startUpdate();
                                    })
                                }
                            }}></Input>

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



    getData(reset = true, limit = 4000, loading = true) {

        // var strategy = App.strategySelector.selected();
        // if (!strategy) return;

        var account =App.accountSelectorTestnet.selected();
        if (!account) return;

        if (reset) {
            this.chartData = {};
            this.startTime = 1;
        }

        if(!this.startTime) return;

        var model = new Price_1s();

        var condition = [[
            PRICE_1S_SYMBOL, '=', this.state.symbol,
        ]]

        if (this.state.start != '') condition.push([PRICE_1S_TIME, '>=', this.state.start])
        if (this.state.stop != '') condition.push([PRICE_1S_TIME, '<=', this.state.stop])

        if (this.state.stop != '' && this.state.stop != null) {
            if (this.updateInterval) clearInterval(this.updateInterval);
        }

        this.getLineChart([condition], {
            orderBy: PRICE_1S_TIME,
            'asc': false,
            limit: limit,
            // strategy: strategy,
            account : account,
            symbol: this.state.symbol,
            startTime: this.startTime,
        }, loading).then(res => {

            if (res['result']) {
                var priceData = res['data']['price'];
                var postionData = res['data']['positions'];
                var orderData = res['data']['orders'];
                var enterbaseData = res['data']['enterbase'];
                var profitbaseData = res['data']['profitbase'];

                var chartIndexDatas = {};
                var positionIndexDatas = {};
                var orderIndexDatas = {};
                var enterBaseIndexDatas = {};
                var profitBaseIndexDatas = {};

                if (!reset) {

                    chartIndexDatas = get(this.chartData['price'], {});
                    positionIndexDatas = get(this.chartData['position'], {});
                    orderIndexDatas = get(this.chartData['order'], {});
                    enterBaseIndexDatas = get(this.chartData['enterbase'], {});
                    profitBaseIndexDatas = get(this.chartData['profitbase'], {});

                }

                for (let i = priceData.length - 1; i >= 0; i--) {
                    var data = priceData[i];
                    var time = Number(data[PRICE_1S_TIME]); // Math.floor(Number(data[PRICE_1S_TIME])/1000)*1000
                    chartIndexDatas[time] = { x: time, y: Number(data[PRICE_1S_CLOSE]) };
                }

                

                for (let i = postionData.length - 1; i >= 0; i--) {
                    var data = postionData[i];
                    positionIndexDatas[data[TESTNET_RESULT_CHART]] = {
                        x: Number(data[TESTNET_RESULT_CHART]), // Math.floor(Number(data[TESTNET_RESULT_CHART])/1000) * 1000,
                        title: (data[TESTNET_RESULT_TYPE] == TESTNET_RESULT_TYPE_LONG ? 'LONG' : 'SHORT')
                    };
                }

                for (let i = orderData.length - 1; i >= 0; i--) {
                    var data = orderData[i];
                    orderIndexDatas[data[TESTNET_ORDER_TIME]] = {
                        x:Number(data[TESTNET_ORDER_TIME]), // Math.floor(Number(data[TESTNET_ORDER_TIME])/1000) * 1000,
                        y: Number(data[TESTNET_ORDER_PRICE]),
                        title: (data[TESTNET_ORDER_TYPE] == '1' ? 'Buy' : 'Sell') + " " + data[TESTNET_ORDER_PHASE]
                    }
                }

                for (let i = enterbaseData.length - 1; i >= 0; i--) {
                    var data = enterbaseData[i];

                    var item = {
                        x: Number(data[ENTERBASE_TIME]), // Math.floor(Number(data[ENTERBASE_TIME])/1000) * 1000,
                        y: Number(data[ENTERBASE_PRICE]),
                    };

                    if (data[ENTERBASE_EVENT] == ENTERBASE_EVENT_MAKESTEP) {
                        item['color'] = 'red';
                        item['marker'] = { symbol: 'circle' }
                    }
                    if (data[ENTERBASE_EVENT] == ENTERBASE_EVENT_MAKEORDER) {
                        item['color'] = 'red';
                        item['marker'] = { symbol: 'triangle' }
                    }
                    if (data[ENTERBASE_EVENT] == ENTERBASE_EVENT_CANCLE) {
                        item['color'] = 'gray';
                        item['marker'] = { symbol: 'triangle' }
                    }
                    if (data[ENTERBASE_EVENT] == ENTERBASE_EVENT_WAITTING) {
                        item['color'] = 'limegreen';
                        item['marker'] = { symbol: 'square' }
                    }

                    enterBaseIndexDatas[data[ENTERBASE_TIME]] = item;
                }

                for (let i = profitbaseData.length - 1; i >= 0; i--) {
                    var data = profitbaseData[i];

                    var item = {
                        x: Number(data[PROFITBASE_TIME]), // Math.floor(Number(data[PROFITBASE_TIME])/1000) * 1000,
                        y: Number(data[PROFITBASE_PRICE]),
                    };

                    if (data[PROFITBASE_EVENT] == PROFITBASE_EVENT_MAKESTEP) {
                        item['color'] = 'red';
                        item['marker'] = { symbol: 'circle' }
                    }
                    if (data[PROFITBASE_EVENT] == PROFITBASE_EVENT_MAKEORDER) {
                        item['color'] = 'red';
                        item['marker'] = { symbol: 'triangle' }
                    }
                    if (data[PROFITBASE_EVENT] == PROFITBASE_EVENT_CANCLE) {
                        item['color'] = 'gray';
                        item['marker'] = { symbol: 'triangle' }
                    }
                    if (data[PROFITBASE_EVENT] == PROFITBASE_EVENT_WAITTING) {
                        item['color'] = 'limegreen';
                        item['marker'] = { symbol: 'square' }
                    }

                    profitBaseIndexDatas[data[PROFITBASE_TIME]] = item;
                }


                if (reset) {
                    this.chartData['price'] = chartIndexDatas
                    this.chartData['position'] = positionIndexDatas
                    this.chartData['order'] = orderIndexDatas
                    this.chartData['enterbase'] = enterBaseIndexDatas
                    this.chartData['profitbase'] = profitBaseIndexDatas
                }

                
                var chartDatas = Object.values(chartIndexDatas);
                if (chartDatas.length > 0) {
                    chartDatas[chartDatas.length - 1]["color"] = "blue";
                    chartDatas[chartDatas.length - 1]["marker"] = { enabled: true, symbol: 'circle', radius: 3 };
                    chartDatas[chartDatas.length - 1]["dataLabels"] = { enabled: true }
                    this.startTime = get(chartDatas[0]["x"], null);
                }

                this.setState({
                    Options: {
                        series: [
                            {
                                data: chartDatas
                            },
                            {
                                data: Object.values(enterBaseIndexDatas),

                            },
                            {
                                data: Object.values(profitBaseIndexDatas),

                            },
                            {
                                data: Object.values(orderIndexDatas),

                            },
                            {
                                data: Object.values(positionIndexDatas),

                            },


                        ]
                    }
                })
            }
        })


    }


    getLineChart(data, options, loading) {
        var url = '/admin/Price_1s/getLineChart';
        if (loading) App.loading(true);
        return axios.request({
            url: url,
            method: 'POST',
            data: {
                data: data,
                ...options
            }
        })

            .then(response => {
                if (loading) App.loading(false);
                response = response['data'];
                return response;
            });
    }




}

export default TestnetChartLine;
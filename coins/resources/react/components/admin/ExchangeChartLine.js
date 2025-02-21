import React, { Component } from 'react';
import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official'
import Price_1s from '../../model/admin/Price_1s';
import SelectSymbol from './SelectSymbol';
import Input from '../input/Input';

require('highcharts/indicators/indicators')(Highcharts);
require('highcharts/indicators/ema')(Highcharts);

class ExchangeChartLine extends Component {
    constructor(props) {
        super(props);

        this.symbol = '',
            this.start = get(App.parsed['start'], ''),
            this.stop = get(App.parsed['stop'], ''),

            this.state = {



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
                            // title: {
                            //     text: '<b></b>',
                            // },

                            startOnTick: false,

                            labels: {
                                align: 'left'
                            },
                            lineWidth: 1,
                            gridLineColor: '#ededed',

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

        this.resetIndex = 0;

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

        if (App.accountSelector) {
            App.accountSelector.register('exchange_line_chart', () => {
                this.getData(true);
            });
        }

        setTimeout(() => this.setRangeSelector(), 3000);


    }


    selectSymbol(symbol) {
        if (symbol != '' && symbol != null) {
            this.symSelector.selectSymbol(symbol, false);
            this.symbol = symbol;
        }
    }

    setTimeRange(start, stop) {
        if (start != '') start = start / 1000;
        if (stop != '') stop = stop / 1000;
        this.startInput.setValue(start);
        this.stopInput.setValue(stop);
        this.start = start * 1000;
        this.stop = stop * 1000;

    }

    startUpdate() {

        if (this.updateInterval) clearInterval(this.updateInterval);
        this.updateInterval = setInterval(() => { this.getData(false, 10, false) }, 3000);
    }

    componentWillUnmount() {
        if (this.updateInterval) clearInterval(this.updateInterval);
        if (this.resize_ob) this.resize_ob.unobserve(this.chartContainer);
        App.accountSelector.unregister('exchange_line_chart')
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

        var max = this.stop;
        var min = this.start;

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

                <div className='box_shadow cus-hide' ref={c => this.chartContainer = c} style={{ position: 'relative' }}>

                    <div style={{ display: 'flex', alignItems: 'center', padding: 7 }}>
                        <SelectSymbol ref={c => this.symSelector = c} onSelect={sym => {
                            this.symbol = sym;
                            this.getData(true)
                        }
                        }></SelectSymbol>



                        &nbsp;

                        <Input ref={c => this.startInput = c} placeholder="Start Time" className='input' struct={{
                            [INPUT_TYPE]: 'date',
                            [INPUT_DEFAULT]: this.start != '' ? (this.start / 1000) : '',
                            [INPUT_ONCHANGE_BLUR]: (e, obj) => { this.start = obj.getValue() * 1000; this.getData(true) }
                        }}></Input>

                        &nbsp;

                        <Input ref={c => this.stopInput = c} placeholder="Stop Time" className='input' struct={{
                            [INPUT_TYPE]: 'date',
                            [INPUT_DEFAULT]: this.stop != '' ? (this.stop / 1000) : '',
                            [INPUT_ONCHANGE_BLUR]: (e, obj) => {
                                this.stop = obj.getValue() * 1000;
                                this.getData(true);
                                if (obj.getValue() == '') this.startUpdate();
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


            </>
        );
    }



    getData(reset = true, limit = 4000, loading = true) {
      
        var account = App.accountSelectorTestnet.selected();
        if (!account) return;
       
        var resetIndex = this.resetIndex

        if (reset) {
            this.chartData = {};
            this.startTime = 1;
            this.resetIndex++;
        }

        if (!this.startTime) return;

        var model = new Price_1s();

        var condition = [[
            PRICE_1S_SYMBOL, '=', this.symbol,
        ]]

        if (this.start != '') condition.push([PRICE_1S_TIME, '>=', this.start])
        if (this.stop != '') condition.push([PRICE_1S_TIME, '<=', this.stop])

        if (this.stop != '' && this.stop != null) {
            if (this.updateInterval) clearInterval(this.updateInterval);
        }

        this.getLineChart([condition], {
            orderBy: PRICE_1S_TIME,
            'asc': false,
            limit: limit,
            account: account,
            symbol: this.symbol,
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

                    if (resetIndex < this.resetIndex) return;
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
                    positionIndexDatas[data[ACTION_CHART]] = {
                        x: Number(data[ACTION_CHART]), // Math.floor(Number(data[ACTION_CHART])/1000) * 1000,
                        y: Number(data[ACTION_ENTER_PRICE]),
                        title: (data[ACTION_TYPE] == ACTION_TYPE_LONG ? 'LONG' : 'SHORT')
                    };
                }

                for (let i = orderData.length - 1; i >= 0; i--) {
                    var data = orderData[i];
                    orderIndexDatas[data[ORDER_TIME]] = {
                        x: Number(data[ORDER_TIME]), // Math.floor(Number(data[ORDER_TIME])/1000) * 1000,
                        y: Number(data[ORDER_PRICE]),
                        title: data[ORDER_SIDE]
                    }
                }

                for (let i = enterbaseData.length - 1; i >= 0; i--) {
                    var data = enterbaseData[i];

                    var item = {
                        x: Number(data[LOG_ENTERBASE_TIME]), // Math.floor(Number(data[LOG_ENTERBASE_TIME])/1000) * 1000,
                        y: Number(data[LOG_ENTERBASE_PRICE]),
                    };

                    if (data[LOG_ENTERBASE_EVENT] == LOG_ENTERBASE_EVENT_MAKESTEP) {
                        item['color'] = 'red';
                        item['marker'] = { symbol: 'circle' }
                    }
                    if (data[LOG_ENTERBASE_EVENT] == LOG_ENTERBASE_EVENT_MAKEORDER) {
                        item['color'] = 'red';
                        item['marker'] = { symbol: 'triangle' }
                    }
                    if (data[LOG_ENTERBASE_EVENT] == LOG_ENTERBASE_EVENT_CANCLE) {
                        item['color'] = 'gray';
                        item['marker'] = { symbol: 'triangle' }
                    }
                    if (data[LOG_ENTERBASE_EVENT] == LOG_ENTERBASE_EVENT_WAITTING) {
                        item['color'] = 'limegreen';
                        item['marker'] = { symbol: 'square' }
                    }

                    enterBaseIndexDatas[data[LOG_ENTERBASE_TIME]] = item;
                }

                for (let i = profitbaseData.length - 1; i >= 0; i--) {
                    var data = profitbaseData[i];

                    var item = {
                        x: Number(data[LOG_PROFITBASE_TIME]), // Math.floor(Number(data[LOG_PROFITBASE_TIME])/1000) * 1000,
                        y: Number(data[LOG_PROFITBASE_PRICE]),
                    };

                    if (data[LOG_PROFITBASE_EVENT] == LOG_PROFITBASE_EVENT_MAKESTEP) {
                        item['color'] = 'red';
                        item['marker'] = { symbol: 'circle' }
                    }
                    if (data[LOG_PROFITBASE_EVENT] == LOG_PROFITBASE_EVENT_MAKEORDER) {
                        item['color'] = 'red';
                        item['marker'] = { symbol: 'triangle' }
                    }
                    if (data[LOG_PROFITBASE_EVENT] == LOG_PROFITBASE_EVENT_CANCLE) {
                        item['color'] = 'gray';
                        item['marker'] = { symbol: 'triangle' }
                    }
                    if (data[LOG_PROFITBASE_EVENT] == LOG_PROFITBASE_EVENT_WAITTING) {
                        item['color'] = 'limegreen';
                        item['marker'] = { symbol: 'square' }
                    }

                    profitBaseIndexDatas[data[LOG_PROFITBASE_TIME]] = item;
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

                // priceData = priceData.sort((a,b)=>Number(b[PRICE_1S_TIME])-Number(a[PRICE_1S_TIME]));
                //chartDatas = chartDatas.sort((a,b)=>a['x']-b['x']);


               
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
        var url = '/admin/Price_1s/getLineChartExchange';
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

export default ExchangeChartLine;
import React, { Component } from 'react';
import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official'
import Fear from '../../model/admin/Fear';
import Candle_1d from '../../model/admin/Candle_1d';
import candle_1w from '../../model/admin/Candle_1w';
import Wma_45 from '../../model/admin/Wma_45';


require('highcharts/indicators/indicators')(Highcharts);
require('highcharts/indicators/ema')(Highcharts);

class WMAChartLine extends Component {
    constructor(props) {
        super(props);

        this.symbol = '',
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
                                    text: '2Y',
                                    type: 'day',
                                    count: 730,

                                },
                                {
                                    text: '3Y',
                                    type: 'day',
                                    count: 1095,

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
                            name: 'F&G',
                            data: [],
                        },
                        {
                            name: 'F&G12343',
                            data: [],
                        },
                       
                        {
                            name: 'Season',
                            data: [],

                        },
                        {
                            name: 'WMA 1W1234',
                            data: [],

                        },
                        {
                            name: 'Trend 1',
                            data: [],
                        },
                        {
                            name: 'WMA 1D234',
                            data: [],
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


        this.updateChartWidth();
        this.resize_ob = new ResizeObserver((entries) => {
            this.updateChartWidth()
        });
        this.resize_ob.observe(this.chartContainer);

        // setTimeout(() => this.setRangeSelector(), 3000);

        this.getData();


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
            Options: { rangeSelector: { selected: 3 } },
        })

    }

    render() {
        return (
            <>

                <div className='box_shadow cus-hide ' ref={c => this.chartContainer = c} style={{ position: 'relative', marginTop: 15, padding: 5 }}>

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



    async getData() {
        var model = new Candle_1d();
        var model1w = new candle_1w();

        // var Candle_1m = await model.read({ [CANDLE_1D_SYMBOL]: 'BTCUSDT' }, { 'orderBy': CANDLE_1D_CLOSE_TIME, 'asc': true });
        var Candle_1m = await model.getAll();

        var chartData = [];
        if (Candle_1m['result']) {
            var datas = Candle_1m['data'];

            for (let i = datas.length - 1; i >= 0; i--) {
                var data = datas[i];
                if (data[CANDLE_1D_RSI_WMA]) {
                    var time = Number(data[CANDLE_1D_OPEN_TIME]);
                    var value = Math.round(Number(data[CANDLE_1D_RSI_WMA]) * 100) / 100;
                    chartData.unshift({ x: time, y: value , labelrank : 10 });

                    if (chartData.length > 0) {
                        chartData[chartData.length - 1]["color"] = chartData[chartData.length - 1].y > 50 ? "limegreen" : 'red';
                        chartData[chartData.length - 1]["marker"] = { enabled: true, symbol: 'circle', radius: 3 };
                        chartData[chartData.length - 1]["dataLabels"] = { enabled: true }
                    }
                }

            }


        }


        // var Candle_1w = await model1w.read({ [CANDLE_1W_SYMBOL]: 'BTCUSDT' }, { 'orderBy': CANDLE_1W_CLOSE_TIME, 'asc': true });
        var Candle_1w = await model1w.getAll();

        var chartData1W = [];

        if (Candle_1w['result']) {
            var datas = Candle_1w['data'];
            // console.log(datas)

            for (let i = datas.length - 1; i >= 0; i--) {
                var data = datas[i];
                if (data[CANDLE_1W_RSI_WMA]) {
                    var time = Number(data[CANDLE_1W_OPEN_TIME]);
                    var value = Math.round(Number(data[CANDLE_1W_RSI_WMA]) * 100) / 100;
                    chartData1W.unshift({ x: time, y: value });
                }
            }



            if (chartData1W.length > 0) {
                chartData1W[chartData1W.length - 1]["color"] = chartData1W[chartData1W.length - 1].y > 55 ? "limegreen" : 'red';
                chartData1W[chartData1W.length - 1]["marker"] = { enabled: true, symbol: 'circle', radius: 3 };
                chartData1W[chartData1W.length - 1]["dataLabels"] = { enabled: true }
            }
            

        }

        var model = new Fear();
        var Fear_Data = await model.get(null, { limit: 1000, orderBy: FEAR_TIME, asc: false });
        var chartDataFear = [];
        if (Fear_Data['result']) {
            var datas = Fear_Data['data'];


            for (let i = datas.length - 1; i >= 0; i--) {
                var data = datas[i];
                var time = Number(data[FEAR_TIME]);
                chartDataFear.push({ x: time, y: Number(data[FEAR_VALUE]) });
            }

            if (chartDataFear.length > 0) {
                chartDataFear[chartDataFear.length - 1]["color"] = chartDataFear[chartDataFear.length - 1].y > 50 ? "limegreen" : 'red';
                chartDataFear[chartDataFear.length - 1]["marker"] = { enabled: true, symbol: 'circle', radius: 3 };
                chartDataFear[chartDataFear.length - 1]["dataLabels"] = { enabled: true }
            }



            if (this.props.setFear) {
                // this.props.OrderTracking(chartDataFear[chartDataFear.length - 1].y);
                this.props.setFear(chartDataFear[chartDataFear.length - 1].y);
            }
            if (this.props.setData) {
                this.props.setData(chartDataFear[chartDataFear.length - 1].y);

            }

        }

        var modelWma45 = new Wma_45();

        var Wma45Data = await modelWma45.read({ 'orderBy': 'time', 'sort': 'desc' });

        if (Wma45Data['result']) {
            var datas = Wma45Data['data'];
            var lastWma1D = Number(chartData[0]['x'])
            var lastWma1W = Number(chartData1W[0]['x'])

            for (let i = 0; i < datas.length; i++) {
                let item = datas[i];
                let time = Number(item['time']) * 1000
                let wma1d = Math.round(Number(item['wma45_1D']) * 100) / 100;
                let wma1w = Math.round(Number(item['wma45_1W']) * 100) / 100;
                if (time < lastWma1D && wma1d) {

                    chartData.unshift({ x: time, y: wma1d , labelrank : 10});


                }
                if (time < lastWma1W && wma1w) {

                    chartData1W.unshift({ x: time, y: wma1w });


                }
            }

        }





        this.setState({
            Options: {
                series: [

                    {
                        data: chartDataFear,
                        type: 'area',
                        threshold: 50,
                        negativeColor: {
                            linearGradient: [0, 0, 0, 300],
                            stops: [
                                [0.5, '#ffffff00'],
                                [1, '#f0afaf']
                            ]
                        },
                        color: {
                            linearGradient: [0, 0, 0, 300],
                            stops: [
                                [0, 'limegreen'],
                                [0.5, '#ffffff00']
                            ]
                        },
                    },
                    {
                        // type : 'line',
                        data: chartDataFear,
                        threshold: 50,
                        negativeColor: 'red',
                        color: 'limegreen',
                        linkedTo: ':previous',
                        enableMouseTracking: false,
                    },
                    
                    {
                        data: chartData1W,
                        type: 'area',
                        threshold: 55,
                        negativeColor: {
                            linearGradient: [0, 0, 0, 300],
                            stops: [
                                [0.5, '#ffffff00'],
                                [1, '#f0afaf']
                            ]
                        },
                        color: {
                            linearGradient: [0, 0, 0, 300],
                            stops: [
                                [0, 'limegreen'],
                                [0.5, '#ffffff00']
                            ]
                        },
                    },
                    {
                        data: chartData1W,
                        threshold: 55,
                        negativeColor: 'red',
                        color: 'limegreen',
                        linkedTo: ':previous',
                        enableMouseTracking: false,
                    },
                    {
                        data: chartData,
                        type: 'area',
                        threshold: 50,
                        negativeColor: {
                            linearGradient: [0, 0, 0, 300],
                            stops: [
                                [0.5, '#ffffff00'],
                                [1, '#f0afaf']
                            ]
                        },
                        color: {
                            linearGradient: [0, 0, 0, 300],
                            stops: [
                                [0, 'limegreen'],
                                [0.5, '#ffffff00']
                            ]
                        },


                    },
                    {
                        data: chartData,
                        threshold: 50,
                        negativeColor: 'red',
                        color: 'limegreen',
                        linkedTo: ':previous',
                        enableMouseTracking: false,
                    },
                   
                   
                ]
            }

        }, () => this.setRangeSelector())








    }




}

export default WMAChartLine;
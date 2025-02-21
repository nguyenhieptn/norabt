import React, { Component } from 'react';
import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official'
import Change_24h from '../../../model/admin/Change_24h';

require('highcharts/indicators/indicators')(Highcharts);
require('highcharts/indicators/ema')(Highcharts);

class ChartChange24h extends Component {
    constructor(props) {
        super(props);
        this.state = {
            ALL: true,
            coin: [],
            selected: {},
            lastItem: {},
            Options2: {

                legend: {
                    enabled: false
                },
                title: {
                    text: '<b>CHANGE 24H</b>',
                },
                plotOptions: {
                    series: {
                        turboThreshold: 0,
                        dataLabels: {
                            enabled: true
                        },
                        maxPointWidth: 50
                    },
                },



            },
            Options: {
                chart: {

                }
                ,
                title: {
                    text: '<b>CHANGE 24H HISTORY</b>',
                },
                xAxis: {

                },
                yAxis: [
                    {
                        title: {
                            text: '<b>%</b>',
                        },
                        max: 100,
                        min: 0,
                        startOnTick: false,
                        // linkedTo: 0
                    },

                    {
                        title: {
                            text: '<b>%</b>',

                        },
                        max: 100,
                        min: 0,
                        startOnTick: false,


                        opposite: false,
                    },

                ],

                chart: {
                    height: (12 / 16 * 73) + '%'

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
                    { visible: false },
                    {   
                        id: 'altsup',
                        visible: true 
                    },
                    { visible: true },
                    { visible: true },
                    { visible: true },
                    {
                        yAxis: 1,
                        visible: false
                    },
                    { visible: false },
                    { visible: false },
                    { visible: false },
                    { visible: false },
                    { visible: false },
                    { visible: false },
                    { visible: false },
                    { visible: false },
                    { visible: false },
                    { visible: false },
                    { visible: false },
                    { visible: false },
                    { visible: false },
                    { visible: false },
                    { visible: false },
                    { visible: false },
                    { visible: false },
                    { visible: false },
                    { visible: false },
                    { visible: false },
                    { visible: false },
                    { visible: false },
                    { visible: false },
                    { visible: false },
                    { visible: false },
                   
                    
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

    }
    componentDidMount() {

        // this.updateInterval = setInterval(() => { this.getData() }, 2 * 60000);
        this.updateChartWidth();
        this.resize_ob = new ResizeObserver((entries) => {
            this.updateChartWidth()
        });
        this.resize_ob.observe(this.chartContainer);

        this.getData();

    }
    componentWillUnmount() {
        if (this.updateInterval) clearInterval(this.updateInterval);
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
                <div className='p-col-12 p-md-12 cushide' >
                    <div className='box_shadow ' ref={c => this.chartContainer = c} style={{ position: 'relative' }}>

                        <HighchartsReact
                            highcharts={Highcharts}
                            options={this.state.Options}
                            constructorType={'stockChart'}
                        />

                        <div style={{ marginBottom: 15 }}>
                            <HighchartsReact
                                highcharts={Highcharts}
                                options={this.state.Options2}

                            />
                            <br />
                            <div style={{ display: 'flex', height: 20, padding: '0px 25px' }}>
                                <div style={{ width: `${this.state.lastItem[CHANGE24H_UP]}%`, background: 'limegreen' }}></div>
                                <div style={{ width: `${this.state.lastItem[CHANGE24H_KEEP]}%`, background: 'darkgray' }}></div>
                                <div style={{ width: `${this.state.lastItem[CHANGE24H_DOWN]}%`, background: 'red' }}></div>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0px 30px' }}>
                                <div style={{ color: 'black', fontWeight: 'bold' }}>Price Up: {Math.round(this.state.lastItem[CHANGE24H_TOTAL] * this.state.lastItem[CHANGE24H_UP] / 100)}</div>
                                <div style={{ color: 'black', fontWeight: 'bold' }}>Price Down: {Math.round(this.state.lastItem[CHANGE24H_TOTAL] * this.state.lastItem[CHANGE24H_DOWN] / 100)}</div>
                            </div>
                        </div>






                    </div>

                </div>
            </>
        );
    }

    getData() {

        var resultModel = new Change_24h();



        resultModel.get([], { 'limit': 5000, 'orderBy': CHANGE24H_TIME, 'asc': false }).then(res => {
            if (res['result']) {
                var serialObject = {};
                for (let i in res['data']) {

                    var item = res['data'][i];
                    for (let column in item) {
                        if (column == CHANGE24H_TIME 
                            || column == CHANGE24H_TOTAL 
                            || column == CHANGE24H_ID
                            || column == CHANGE24H_UP_10
                            || column == CHANGE24H_UP_7_10
                            || column == CHANGE24H_UP_5_7
                            || column == CHANGE24H_UP_3_5
                            || column == CHANGE24H_UP_0_3
                            || column == CHANGE24H_DOWN_0_3
                            || column == CHANGE24H_DOWN_3_5
                            || column == CHANGE24H_DOWN_5_7
                            || column == CHANGE24H_DOWN_7_10
                            || column == CHANGE24H_DOWN_10
                            || column == CHANGE24H_5M_UP
                            || column == CHANGE24H_5M_DOWN
                            || column == CHANGE24H_15M_UP
                            || column == CHANGE24H_15M_DOWN
                            || column == CHANGE24H_1H_UP
                            || column == CHANGE24H_1H_DOWN
                            || column == CHANGE24H_4H_UP
                            || column == CHANGE24H_4H_DOWN
                        ) continue;
                        if (!isset(serialObject[column])) {
                            serialObject[column] = {
                                // type: 'line',
                                name: lang(column),
                                data: [{ x: item[CHANGE24H_TIME], y: item[column] }],
                                // visible: (column == CHANGE24H_UP || column == CHANGE24H_BTC_ASC) ? true : false,
                            }
                        } else {
                            serialObject[column]['data'].unshift({ x: item[CHANGE24H_TIME], y: item[column] });
                        }

                        
                    }

                    
                }

                // serialObject['ema5'] = {
                //     name : 'Ema5',
                //     type: 'ema',
                //     linkedTo: 'altsup',
                //     params: {
                //         period: 5
                //     }
                // }

                // serialObject['ema9'] = {
                //     name : 'Ema9',
                //     type: 'ema',
                //     linkedTo: 'altsup',
                //     params: {
                //         period: 9
                //     }
                // }
                
                // serialObject['ema13'] = {
                //     name : 'Ema13',
                //     type: 'ema',
                //     linkedTo: 'altsup',
                //     params: {
                //         period: 13
                //     }
                // }

                var lastItem = res['data'].shift();
                var categories = ['>10%', '7-10%', '5-7%', '3-5%', '0-3%', '0%', '0-3%', '3-5%', '5-7%', '7-10%', '>10%'];
                var colors = ['limegreen', 'limegreen', 'limegreen', 'limegreen', 'limegreen', 'darkgray', 'red', 'red', 'red', 'red', 'red'];
                var option2Data = [
                    Math.round(lastItem[CHANGE24H_TOTAL] * lastItem[CHANGE24H_UP_10] / 100),
                    Math.round(lastItem[CHANGE24H_TOTAL] * lastItem[CHANGE24H_UP_7_10] / 100),
                    Math.round(lastItem[CHANGE24H_TOTAL] * lastItem[CHANGE24H_UP_5_7] / 100),
                    Math.round(lastItem[CHANGE24H_TOTAL] * lastItem[CHANGE24H_UP_3_5] / 100),
                    Math.round(lastItem[CHANGE24H_TOTAL] * lastItem[CHANGE24H_UP_0_3] / 100),
                    Math.round(lastItem[CHANGE24H_TOTAL] * lastItem[CHANGE24H_KEEP] / 100),
                    Math.round(lastItem[CHANGE24H_TOTAL] * lastItem[CHANGE24H_DOWN_0_3] / 100),
                    Math.round(lastItem[CHANGE24H_TOTAL] * lastItem[CHANGE24H_DOWN_3_5] / 100),
                    Math.round(lastItem[CHANGE24H_TOTAL] * lastItem[CHANGE24H_DOWN_5_7] / 100),
                    Math.round(lastItem[CHANGE24H_TOTAL] * lastItem[CHANGE24H_DOWN_7_10] / 100),
                    Math.round(lastItem[CHANGE24H_TOTAL] * lastItem[CHANGE24H_DOWN_10] / 100),
                ]

                if (!this.firstTime) {
                    this.firstTime = true;
                    setTimeout(() => {
                        this.setState({
                            Options: {
                                rangeSelector: {
                                    selected: 4
                                }
                            }
                        })
                    }, 2000)
                }


                this.setState({
                    lastItem: lastItem,
                    Options: { series: Object.values(serialObject) },
                    Options2: {

                        xAxis: {
                            categories: categories,
                            crosshair: true
                        },

                        series: [{
                            type: 'column',
                            name: 'Change 24h',
                            data: option2Data
                        }],

                        plotOptions: {
                            series: {
                                colorByPoint: true,
                                colors: colors,
                            }
                        },
                    }
                });
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

export default ChartChange24h;
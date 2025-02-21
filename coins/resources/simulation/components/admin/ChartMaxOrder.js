import React, { Component } from 'react';
import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official'
import Lab_watchlist from '../../model/admin/Lab_watchlist';
import Lab_results from '../../model/admin/Lab_results';

class ChartMaxOrder extends Component {
    constructor(props) {
        super(props);
        this.state = {
            ALL: true,
            coin: [],
            selected: {},
            Options: {
                chart: {
                    height: (8 / 16 * 73) + '%',
                    panning: {
                        enabled: true,
                        type: 'x'
                    },
                    panKey: 'shift',
                    zoomType: 'x'
                }

                ,
                credits: {
                    enabled: false
                },
                title: {
                    text: '<b>MAX OPEN TRADES</b>',
                },
                xAxis: {
                    type: 'datetime',

                },
                yAxis: [
                    {
                        title: {
                            // text: '<b>Open Trades</b>'
                            text: '<b></b>'
                        },

                    }
                ],

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
                    buttonSpacing: 10,
                },


                legend: {
                    enabled: true,

                },
                plotOptions: {
                    series: {
                        dataLabels: {
                            enabled: true
                        },
                        maxPointWidth: 100,
                        turboThreshold: 0 // Comment out this code to display error
                    },

                    column: {
                        zones: [{
                            value: 0,
                            color: 'red'
                        }, {
                            color: '#007bff'
                        }]
                    },



                },
                tooltip: {
                    style: {
                        fontSize: '9px'
                    },

                },
                series: [
                    {
                        name: "Opening",
                        data: [],
                    },
                    {
                        name: "Phase 0",
                        data: [],
                    },
                    {
                        name: "Phase 1",
                        data: [],
                    },
                    {
                        name: "Phase 2",
                        data: [],
                    },
                    {
                        name: "Phase 3",
                        data: [],
                        color: 'red'
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
                        <div style={{ display: 'flex', alignItems: 'center', position: 'absolute', top: 5, left: 5, zIndex: 100 }}>
                            <div className='button btn' style={{  borderRadius: 0, padding: '2px 5px', fontWeight: (this.state.ALL == true ? 'bold' : '100'), background: (this.state.ALL == true ? 'rgb(230, 235, 245)' : '#f7f7f7') }}  onClick={() => {
                                this.getData();
                            }}>Calculate</div>
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

    getData() {

        if (!App.accountSelectorLab || App.accountSelectorLab.selected() == null) return;

        var resultModel = new Lab_results();
        var maxOrder = {};
        var maxPha0 = {};
        var maxPha1 = {};
        var maxPha2 = {};
        var maxPha3 = {};

        // resultModel.get([[[LAB_RESULT_STRATEGY, '=', App.accountSelectorLab.selected()]]], { 'orderBy': LAB_RESULT_CHART, 'asc': false }).then(res => {
        resultModel.get([[[LAB_RESULT_ACCOUNT, '=', App.accountSelectorLab.selected()]]], { 'orderBy': LAB_RESULT_CHART, 'asc': false }).then(res => {
            if (res['data']) {
                res = res['data'];

                for (let i in res) {

                    if (res[i][LAB_RESULT_STATUS] == LAB_RESULT_STATUS_CANCLE) continue;
                    var phase = res[i][LAB_RESULT_PHASE];

                    var start = Number(res[i][LAB_RESULT_CHART]);
                    if (!isset(maxOrder[start])) maxOrder[start] = 0;
                    if (!isset(maxPha0[start])) maxPha0[start] = 0;
                    if (!isset(maxPha1[start])) maxPha1[start] = 0;
                    if (!isset(maxPha2[start])) maxPha2[start] = 0;
                    if (!isset(maxPha3[start])) maxPha3[start] = 0;


                    for (let j in maxOrder) {
                        if (j >= start) {
                            maxOrder[j]++;
                            if (phase == 0) {
                                maxPha0[j]++;
                            } else if (phase == 1) {
                                maxPha1[j]++;
                            } else if (phase == 2) {
                                maxPha2[j]++;
                            } else if (phase == 3) {
                                maxPha3[j]++;
                            }
                        }
                    }

                }

                res = res.sort((a, b) => Number(a[LAB_RESULT_SELL_TIME]) - Number(b[LAB_RESULT_SELL_TIME]))

                for (let i in res) {

                    if (res[i][LAB_RESULT_STATUS] == LAB_RESULT_STATUS_CANCLE) continue;

                    var phase = res[i][LAB_RESULT_PHASE];

                    var stop = Number(res[i][LAB_RESULT_SELL_TIME]);
                    if (stop == 0) continue;
                    for (let j in maxOrder) {
                        if (j >= stop) {
                            maxOrder[j]--;
                            if (phase == 0) {
                                maxPha0[j]--;
                            } else if (phase == 1) {
                                maxPha1[j]--;
                            } else if (phase == 2) {
                                maxPha2[j]--;
                            } else if (phase == 3) {
                                maxPha3[j]--;
                            }
                        }
                    }

                }

                var maxOrderData = [];
                for (let j in maxOrder) {
                    maxOrderData.unshift({
                        x: Number(j),
                        y: maxOrder[j],
                    })
                }
                var maxOrderDataPhase0 = [];
                for (let j in maxPha0) {
                    maxOrderDataPhase0.unshift({
                        x: Number(j),
                        y: maxPha0[j],
                    })
                }
                var maxOrderDataPhase1 = [];
                for (let j in maxPha1) {
                    maxOrderDataPhase1.unshift({
                        x: Number(j),
                        y: maxPha1[j],
                    })
                }
                var maxOrderDataPhase2 = [];
                for (let j in maxPha2) {
                    maxOrderDataPhase2.unshift({
                        x: Number(j),
                        y: maxPha2[j],
                    })
                }
                var maxOrderDataPhase3 = [];
                for (let j in maxPha3) {
                    maxOrderDataPhase3.unshift({
                        x: Number(j),
                        y: maxPha3[j],
                    })
                }

                this.setState({
                    Options: {
                        series: [
                            {
                                data: maxOrderData
                            },
                            {
                                data: maxOrderDataPhase0
                            },
                            {
                                data: maxOrderDataPhase1
                            },
                            {
                                data: maxOrderDataPhase2
                            },
                            {
                                data: maxOrderDataPhase3
                            }
                        ]

                    }
                })
            }
        })



    }
}

export default ChartMaxOrder;
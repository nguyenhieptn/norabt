import React, { Component } from 'react';
import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official'


import Binance_track_balance from '../../../model/admin/Binance_track_balance';
class ChartBalance extends Component {
    constructor(props) {
        super(props);

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
                        text: 'Balance',
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

    render() {
        return (
            <>
            <div className='p-col-12 p-md-12 ' >
                <div className='box_shadow ' ref={c => this.chartContainer = c} style={{ position: 'relative' }}>
                    <div className='cus-hide' style={{ display: 'flex', position: 'absolute', top: '38px', right: '60px', zIndex: 1000 }}>
                        <div className='mr-3 '>
                            <div>
                                <span> Max Unrealize profit / Balance : </span>
                                <span>{this.state.maxPerUreBa} %</span>
                            </div>
                            <div>{moment(this.state.daymaxPerUreBa, 'x').format(DATE_FORMAT)}</div>
                        </div>
                        <div>
                            <div>
                                <span> Max invest / Balance : </span>
                                <span>{this.state.maxPerInBa} %</span>
                            </div>
                            <div>{moment(this.state.daymaxPerInBa, 'x').format(DATE_FORMAT)}</div>
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

    async getData() {

        var investDatas = [];
        var unrealizeDatas = [];
        var marginBalanceDatas = [];
        var balanceDatas = [];

        var model = new Binance_track_balance();

        var result = await model.read({ [BINANCE_TRACK_BL_ACCOUNT]: App.accountSelector.selected() }, true, {
            orderBy: BINANCE_TRACK_BL_TIME,
            sort: 'desc',
            limit: 1000,
        });

        var maxPerUreBa;
        var daymaxPerUreBa;
        var maxPerInBa;
        var daymaxPerInBa;

        if (result['result']) {
            result = result['data'];


            for (let i in result) {
                let time = Number(result[i][BINANCE_TRACK_BL_TIME]);
                investDatas.unshift({
                    x: time,
                    y: Number(result[i][BINANCE_TRACK_BL_INVEST])
                });
                unrealizeDatas.unshift({
                    x: time,
                    y: Number(result[i][BINANCE_TRACK_BL_UNREALIZE])
                });
                marginBalanceDatas.unshift({
                    x: time,
                    y: Number(result[i][BINANCE_TRACK_BL_MARGIN_BL])
                });
                balanceDatas.unshift({
                    x: time,
                    y: Number(result[i][BINANCE_TRACK_BL_BALANCE])
                });

                var perUreBa = Number(result[i][BINANCE_TRACK_BL_UNREALIZE]) / Number(result[i][BINANCE_TRACK_BL_BALANCE]);
                var perInBa = Number(result[i][BINANCE_TRACK_BL_INVEST]) / Number(result[i][BINANCE_TRACK_BL_BALANCE]);
                if (!isset(maxPerUreBa)) {
                    maxPerUreBa = perUreBa;
                    daymaxPerUreBa = Number(result[i][BINANCE_TRACK_BL_TIME]);
                    maxPerInBa = perInBa;
                    daymaxPerInBa = Number(result[i][BINANCE_TRACK_BL_TIME]);

                } else {
                    if (maxPerUreBa > perUreBa) {
                        maxPerUreBa = perUreBa;
                        daymaxPerUreBa = Number(result[i][BINANCE_TRACK_BL_TIME]);
                    }
                    if (maxPerInBa < perInBa) {
                        maxPerInBa = perInBa;
                        daymaxPerInBa = Number(result[i][BINANCE_TRACK_BL_TIME]);
                    }
                }
            }
        }

        this.setState({
            maxPerInBa: (maxPerInBa * 100).toFixed(2),
            maxPerUreBa: (maxPerUreBa * 100).toFixed(2),
            daymaxPerInBa ,
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
                    }
                ]
            }

        })

        setTimeout(() => this.setRangeSelector(), 3000);

    }
}

export default ChartBalance;
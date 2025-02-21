import React, { Component } from 'react';
import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official'

import Lab_track_blance from '../../model/admin/Lab_track_balance';
import BalanceMaxModal from '../admin/BalanceMaxModal';


class ChartBalance extends Component {

    constructor(props) {
        super(props);
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
                    text: '<b>Balance</b>',
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
                        },
                        lineWidth: 1,

                    },

                ],

                chart: {
                    height: 600,
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
                credits: {
                    enabled: false
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
                    }

                ]
            }
        }
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
    render() {
        return (
            <>
                <div className='p-col-12 p-md-12 ' >
                    <div className='box_shadow ' ref={c => this.chartContainer = c} style={{ position: 'relative' }}>

                        {!App.isMobile() &&
                            <div style={{ display: 'flex', position: 'absolute', top: '38px', right: '70px', zIndex: 1000 }}>

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
                                <button type="button" className="btn btn-info" onClick={() => {

                                    this.BalanceMaxModal.modal();
                                    this.BalanceMaxModal.loadOrigin();
                                }}>Info</button>
                            </div>
                        }

                        <HighchartsReact
                            highcharts={Highcharts}
                            options={this.state.Options}
                            constructorType={'stockChart'}
                        />

                        <BalanceMaxModal ref={c => this.BalanceMaxModal = c} title='Max Unrealize profit / Balance'></BalanceMaxModal>




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

        var model = new Lab_track_blance();

        var result = await model.read({ [LAB_TRACK_BL_ACCOUNT]: App.accountSelectorLab.selected() }, true, {
            // orderBy: LAB_TRACK_BL_TIME,
            // sort: 'asc'
        });

        var maxPerUreBa;
        var daymaxPerUreBa;
        var maxPerInBa;
        var daymaxPerInBa;

        var top20Dic = {};
        var top20 = []
        
        let check = true;

        if (result['result']) {
            result = result['data'];


            
            for (let i in result) {
                let time = Number(result[i][LAB_TRACK_BL_TIME]);
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


                let startOfDay = Math.floor(time/86400000)*86400000
                if(!isset(top20Dic[startOfDay])){
                    top20Dic[startOfDay] = {
                        x: time,
                        y: perUreBa
                    }
                }else{
                    if(perUreBa < top20Dic[startOfDay].y){
                        top20Dic[startOfDay] = {
                            x: time,
                            y: perUreBa
                        }
                    }
                }

                // if (top20.length < 20) {

                //     top20.push({
                //         x: time,
                //         y: perUreBa
                //     })

                // } else if (top20.length == 20) {
                //     if (check) {
                //         top20.sort(function (a, b) {
                //             return a.y - b.y;
                //         });

                //         check = false
                //     }
                //     else {
                //         if (perUreBa <= top20[0].y) {
                //             top20.unshift({
                //                 x: time,
                //                 y: perUreBa
                //             });
                //             top20.pop()
                //         } else {
                //             for (let i = top20.length - 1; i >= 0; i--) {
                //                 let value = top20[i].y;
                //                 if (perUreBa <= value) continue;

                //                 if (i !== 19) {
                //                     top20.splice(i + 1, 0, {
                //                         x: time,
                //                         y: perUreBa
                //                     });
                //                     top20.pop()
                //                 }
                //                 break

                //             }
                //         }


                //     }

                // }



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
            top20 = top20.sort((a,b)=>a.y - b.y).slice(0, 19)
        }

        var top20Flag = [];
        top20.map(item => {
            top20Flag.push({
                x: item.x,      // Point where the flag appears
                title: (item.y * 100).toFixed(2) + "%", // Title of flag displayed on the chart 
                text: (item.y * 100).toFixed(2) + "%"  // Text displayed when the flag are highlighted.
            })
        })
        App.dataMax = top20;

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
                    }
                ]
            }

        })

        // setTimeout(() => this.setRangeSelector(), 3000);

    }


}

export default ChartBalance;
import React, { Component } from 'react';
import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official'

import Lab_track_blance from '../../model/admin/Lab_track_balance';


class ChartBalanceMax extends Component {

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
                    text: '<b>Max</b>',
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
                        name: 'Max ',
                        id: "balance",
                        data: [],
                    },
                   

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
    componentDidMount(){
      this.getData()
    }
    render() {
        return (
            <>
                <div className='p-col-12 p-md-12 ' >
                    <div className='box_shadow ' ref={c => this.chartContainer = c} style={{ position: 'relative' }}>

                
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

        if(App.dataMax){
            console.log(App.dataMax)
        }

    }


}

export default ChartBalanceMax;
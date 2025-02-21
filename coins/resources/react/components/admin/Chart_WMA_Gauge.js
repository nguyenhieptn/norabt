import React, { Component } from 'react';

import Input from '../input/Input'

import Highcharts from 'highcharts';
import highchartsMore from "highcharts/highcharts-more.js"
import HighchartsReact from 'highcharts-react-official'
import solidGauge from "highcharts/modules/solid-gauge.js";


// import Liquidation from '../../model/admin/Liquidation';
import Order_track from '../../model/admin/Order_track';
highchartsMore(Highcharts);
solidGauge(Highcharts);

class Chart_WMA_Gauge extends Component {

    constructor(props) {
        super(props);
        this.state = {

            Options1D: {
                exporting: {
                    enabled: false
                },
                title: {
                    text: undefined,
                },
                pane: {
                    center: ['50%', '85%'],
                    size: '140%',
                    startAngle: -90,
                    endAngle: 90,
                    background: {
                        backgroundColor:
                            Highcharts.defaultOptions.legend.backgroundColor || '#EEE',
                        innerRadius: '60%',
                        outerRadius: '100%',
                        shape: 'arc'
                    }
                },
                credits: {
                    enabled: false
                },
                scrollbar: {
                    enabled: false
                },

                xAxis: {

                },
                yAxis: {
                    plotBands: [
                        {
                        from: 0,
                        to: 25,
                        color: 'orange',
                        thickness: '40%',
                        label: {
                            text: 'Plot band',
                            align: 'right',
                            x: 30,
                            verticalAlign: 'middle',
                            rotation: -65
                        }
                    },
                        {
                        from: 25,
                        to: 50,
                        color: 'red',
                        thickness: '40%',
                        label: {
                            text: 'Plot band',
                            align: 'right',
                            x: 35,
                            y:20,
                            rotation: -25,
                            verticalAlign: 'middle'
                        }
                    },
                        {
                        from: 50,
                        to: 100,
                        color: 'green',
                        thickness: '40%',
                        label: {
                            text: 'Plot band',
                            // align: 'right',
                            x: -40,
                            rotation: 37,
                            verticalAlign: 'middle'
                        }
                    },

                ],
                    min: 0,
                    max: 100,
                    stops: [
                        [0.25, 'orange'], // green
                        [0.5, 'red'], // yellow
                        [1, 'green'] // red
                    ],
                    lineWidth: 0,
                    tickWidth: 0,
                    minorTickInterval: null,
                    tickAmount: 2,
                    title: {
                        // y: -70,
                        text: 'WMA 1D'
                    },
                    labels: {
                        y: 16
                    }
                },

                chart: {
                    height: 300,
                    type: 'solidgauge'

                },
                legend: {
                    enabled: true,

                },
                navigator: {
                    enabled: true
                },

                plotOptions: {
                    solidgauge: {
                        dataLabels: {
                            y: 5,
                            borderWidth: 0,
                            useHTML: true
                        }
                    }
                },


                series: [
                    {
                    name: '1D',
                    data: [0],
                    dataLabels: {
                        format:
                            '<div style="text-align:center">' +
                            '<span style="font-size:25px ; margin-left : 12px">{y}</span><br/>' +
                           
                            '</div>'
                    },
                },
                {
                    name: '',
                    isRectanglePoint: true,
                    type: 'gauge',
                    data: [10],
                    // dial: {
                    //   backgroundColor: Highcharts.getOptions().colors[1],
                    //   rearLength: '-121%'
                    // },
                    dataLabels: {
                      enabled: false
                    },
                    tooltip :{
                        enabled: false
                    },
                    pivot: {
                        radius: 0
                    }
                  }
            ]
            },
            Options1W: {
                exporting: {
                    enabled: false
                },
                title: {
                    text: undefined,
                },
                pane: {
                    center: ['50%', '85%'],
                    size: '140%',
                    startAngle: -90,
                    endAngle: 90,
                    background: {
                        backgroundColor:
                            Highcharts.defaultOptions.legend.backgroundColor || '#EEE',
                        innerRadius: '60%',
                        outerRadius: '100%',
                        shape: 'arc'
                    }
                },
                credits: {
                    enabled: false
                },
                scrollbar: {
                    enabled: false
                },

                xAxis: {

                },
                yAxis: {
                    plotBands: [
                        {
                        from: 0,
                        to: 50,
                        color: 'red',
                        thickness: '40%'
                    },
                        {
                        from: 50,
                        to: 55,
                        color: 'orange',
                        thickness: '40%'
                    },
                        {
                        from: 55,
                        to: 100,
                        color: 'green',
                        thickness: '40%'
                    },],
                    min: 0,
                    max: 100,
                    stops: [
                        [0.1, '#55BF3B'], // green
                        [0.4, '#DDDF0D'], // yellow
                        [0.9, '#DF5353'] // red
                    ],
                    lineWidth: 0,
                    tickWidth: 0,
                    minorTickInterval: null,
                    tickAmount: 2,
                    title: {
                        // y: -70,
                        text: 'WMA 1W'
                    },
                    labels: {
                        y: 16
                    }
                },

                chart: {
                    height: 300,
                    type: 'solidgauge'

                },
                legend: {
                    enabled: true,

                },
                navigator: {
                    enabled: true
                },

                plotOptions: {
                    solidgauge: {
                        dataLabels: {
                            y: 5,
                            borderWidth: 0,
                            useHTML: true
                        }
                    }
                },


                series: [{
                    name: '1W',
                    data: [],
                    dataLabels: {
                        format:
                            '<div style="text-align:center">' +
                            '<span style="font-size:25px">{y}</span><br/>' +
                            '</div>'
                    },
                   
                }]
            }
        }
        this.updateChartWidth = this.updateChartWidth.bind(this);


    }



    componentDidMount() {
        // this.updateChartWidth();
        // this.resize_ob = new ResizeObserver((entries) => {
        //     this.updateChartWidth()
        // });
        // this.resize_ob.observe(this.chartContainer);


        // this.getData();

        // this.getBTCData()

        // this.getBTCInterval = setInterval(() => { this.getBTCData() }, 300000);

    }

    componentWillUnmount() {
        if (this.getBTCInterval) {
            clearInterval(this.getBTCInterval);
        }
    }


    getBTCData() {
        var model = new Order_track();
        model.read({ [ORDER_TRACK_SYMBOL]: 'BTCUSDT' }).then(res => {
            if (res['result']) {
                var data = res['data'];

                if (isset(data[0])) {
                    let wma1D = [Number(data[0][ORDER_TRACK_1D_RSI_WMA].toFixed(2))];
                    let wma1w = [Number(data[0][ORDER_TRACK_1W_RSI_WMA].toFixed(2))];
                    this.setState({
                        Options1D : {
                            series: [
                                {
                                data: wma1D,
                               
                            }
                        ]
                        },
                        Options1W : {
                            series: [
                                {
                                data: wma1w,
                               
                            }
                        ]
                        }

                    });
                }
            }
        })
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

                <div className='box_shadow mt-2 row' ref={c => this.chartContainer = c}>
                    <div className='text-center col-12 p-0' style={{fontSize : '16px' , fontWeight : 'bold'}}>
                        WMA
                    </div>
                    <div className='col-6 p-0'>

                        <HighchartsReact
                            highcharts={Highcharts}
                            options={this.state.Options1D}
                        />
                    </div>

                    <div className='col-6 p-0'>

                        <HighchartsReact
                            highcharts={Highcharts}
                            options={this.state.Options1W}
                        />
                    </div>

                </div>




            </>

        );
    }


    async getData() {

        var LiquidationModel = new Liquidation();

        var liquidata = await LiquidationModel.read({}, true, { orderBy: LIQUIDATION_TIME, sort: 'asc', });



        var dataShorts = [];
        var dataLongs = [];
        var dataPrice = [];
        if (liquidata['data']) {
            liquidata = liquidata['data'];



            liquidata.map(item => {
                var time = Number(item[LIQUIDATION_TIME]);


                dataShorts.push({
                    x: time,
                    y: Number(item[LIQUIDATION_BUYVOLUSD].toFixed(2))
                });
                dataLongs.push({
                    x: time,
                    y: Number(item[LIQUIDATION_SELLVOLUSD].toFixed(2))
                });
                dataPrice.push({
                    x: time,
                    y: Number(item[LIQUIDATION_PRICE].toFixed(2))
                });
            })
        }

        this.setState({
            Options: {
                series: [
                    {
                        data: dataShorts,
                    },
                    {
                        data: dataLongs,
                    },
                    {
                        data: dataPrice,
                    },
                ],


            }
        })



    }
}

export default Chart_WMA_Gauge;
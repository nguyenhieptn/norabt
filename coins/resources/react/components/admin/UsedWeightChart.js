import React, { Component } from 'react';
import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official'
import Used_weight from '../../model/admin/Used_weight';

class UsedWeightChart extends Component {
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
                            title: {
                                text: '<b></b>',
                            },

                            startOnTick: false,

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
                            name: 'Weight',
                            id: "fandg",
                            data: [],
                        }
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

        setTimeout(() => this.setRangeSelector(), 3000);

        this.getData();

        this.interval = setInterval(()=>{
            this.getData(false)
        }, 60000)


    }

    componentWillUnmount() {

        if (this.resize_ob) this.resize_ob.unobserve(this.chartContainer);

        if(this.interval){
            clearInterval(this.interval)
        }

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

        console.log('Set rangselector to 4')

        this.setState({
            Options: { rangeSelector: { selected: 4 } },
        })

    }

    render() {
        return (
            <>

                <div className='box_shadow cus-hide ' ref={c => this.chartContainer = c} style={{ position: 'relative', marginTop: 15, padding: 5 }}>
                    <div style={{textAlign:'center', fontSize:14}}><b>Used Weight</b></div>
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



    getData(loading = true) {
        var model = new Used_weight();
        model.read({[USED_W_DOMAIN]: 'https://fapi.binance.com'}, loading, { 
            limit: 1000, 
            orderBy: USED_W_TIME, 
            sort: 'desc',
            select: [USED_W_TIME, USED_W_VALUE]
        }).then(res => {
            if (res['result']) {
                var datas = res['data'];

                var chartData = [];
                for (let i = datas.length - 1; i >= 0; i--) {
                    var data = datas[i];
                    var time = Number(data[USED_W_TIME]);
                    chartData.push({ x: time, y: Number(data[USED_W_VALUE]) });
                }
               
                if (chartData.length > 0) {
                    chartData[chartData.length - 1]["color"] = "blue";
                    chartData[chartData.length - 1]["marker"] = { enabled: true, symbol: 'circle', radius: 3 };
                    chartData[chartData.length - 1]["dataLabels"] = { enabled: true }
                }

                this.setState({
                    Options: {
                        series: [{
                            data: chartData
                        }]
                    }

                })

            }
        })

    }




}

export default UsedWeightChart;
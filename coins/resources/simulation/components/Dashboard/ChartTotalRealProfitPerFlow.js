import React, { Component } from 'react';
import Highcharts from 'highcharts';
import HighchartsReact from 'highcharts-react-official'

import Testnet_results from '../../model/admin/Lab_results';




class ChartTotalRealProfitPerFlow extends Component {
    constructor(props) {
        super(props);
        this.state = {

            ALL: true,


            start: 0,
            stop: moment().format('x'),
            frameSelect: 'All',

            chartOptions: {
                chart: {

                },
                exporting: {
                    enabled: false
                },
                title: {
                    text: '<b>Total Percent Per Flow </b>',
                    align: 'center',
                    margin: 45

                },
                xAxis: {
                    labels: {
                        style: {
                            color: 'blue',
                            fontWeight: 'bold',
                            fontSize: 10
                        }
                    }
                },
                yAxis: [
                    {
                        title: {
                            text: '<b></b>'
                        },
                        startOnTick: true,
                        opposite: true,
                        lineWidth: 1,


                    },

                    {
                        title: {
                            text: '<b></b>'
                        },
                        startOnTick: true,
                        lineWidth: 1,

                    }
                ],
                credits: {
                    enabled: false
                },

                chart: {
                    height: 600,
                    type: 'column'

                },
                tooltip: {
                    style: {
                        fontSize: '10px'
                    },
                    headerFormat: '',
                    shared: true
                },
                plotOptions: {
                    series: {
                        dataLabels: {
                            enabled: true,
                            formatter: function () {
                                return formatNumber(this.y.toFixed(3));
                            }
                        },
                        maxPointWidth: 50
                    },
                },

                legend: {
                    enabled: true,
                },

                series: []
            }
        }
        this.updateChartWidth = this.updateChartWidth.bind(this);

        this.colors = {};


    }
    componentDidMount() {

        // this.getData();
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
            if (!this.chartContainer) return;
            this.setState({
                chartOptions: {
                    ...this.setState.chartOptions,
                    chart: {
                        width: this.chartContainer ? this.chartContainer.clientWidth : 0,
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

                        <HighchartsReact
                            ref={c => this.chart = c}
                            highcharts={Highcharts}
                            options={this.state.chartOptions}
                        />

                    </div>

                </div>
            </>
        );
    }



    async getData() {



        var resultModel = new Testnet_results();


        var res = await resultModel.getByAccount();

        if (res['data']) {
            res = res['data'];

            let categories = flowStrategy(res)
            let stopLossResult = []
            let takeprofitResult = []

            for (let index = 0; index < categories.length; index++) {
                stopLossResult.push(0)
                takeprofitResult.push(0)
                
            }

            for (let i in res) {
                var flow = res[i][LAB_RESULT_FLOW]
                var realProfit = res[i][LAB_RESULT_REAL_PROFIT]
                var index = categories.indexOf(flow);

                if (index >= 0) {

                    if (res[i][LAB_RESULT_STATUS] == [LAB_RESULT_STATUS_TAKEPROFIT]) {
                        takeprofitResult[index]+= realProfit;

                    }
                    if (res[i][LAB_RESULT_STATUS] == [LAB_RESULT_STATUS_STOPLOSS]) {
                        stopLossResult[index]+=realProfit;
                    }

                }
            }




            this.setState({
                chartOptions: {
                    series: [
                        {
                            name: 'Take Profit',
                            type: 'column',
                            data: takeprofitResult,
                            color: '#28a745'

                        },
                        {
                            name: 'Stop Loss',
                            type: 'column',
                            data: stopLossResult,
                            color: 'red'

                        }
                    ],
                    xAxis: {
                        categories: categories
                    }
                },

            })
        }



    }





}

export default ChartTotalRealProfitPerFlow;
import React, { Component } from 'react';
import Highcharts from 'highcharts';
import HighchartsReact from 'highcharts-react-official'

import Testnet_results from '../../model/admin/Lab_results';




class ChartTotalRealPNLPerFlowPerStrategy extends Component {
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
                    text: '<b>Total Profit Per Strategy </b>',
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

    getRandomColor() {

        var letters = '0123456789ABCDEF';
        var color = '#';
        for (var i = 0; i < 6; i++) {
            color += letters[Math.floor(Math.random() * 16)];
        }
        return color
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

        var mapping = await resultModel.map();
        var mapping = mapping['data'];


        var res = await resultModel.getByAccount();

        // resultModel.getByAccount().then(res => {
        if (res['data']) {
            res = res['data'];

            // let categories = ['15m-Long', '1h-Long', '4H-NW-H50', '1D-NW-H50', '4H-NW-L50', '4H-W-H50', '1D-W-H50', '4H-W-L50']
            let categories = flowStrategy(res)
            let result = {}
            for (let i in res) {
                var strategy = res[i][LAB_RESULT_STRATEGY]
                var flow = res[i][LAB_RESULT_FLOW]
                var realProfit = res[i][LAB_RESULT_REAL_PNL]

                if (!result[strategy]) {
                    result[strategy] = {}
                    result[strategy]['dataTakeProfit'] = []
                    result[strategy]['dataStopLoss'] = []

                    for (let index = 0; index < categories.length; index++) {
                        result[strategy]['dataTakeProfit'].push(0)
                        result[strategy]['dataStopLoss'].push(0)
        
                    }
                }
                var index = categories.indexOf(flow);

                if (index >= 0) {

                    if (res[i][LAB_RESULT_STATUS] == [LAB_RESULT_STATUS_TAKEPROFIT]) {
                        result[strategy]['dataTakeProfit'][index] += realProfit;

                    }
                    if (res[i][LAB_RESULT_STATUS] == [LAB_RESULT_STATUS_STOPLOSS]) {
                        result[strategy]['dataStopLoss'][index] += realProfit;
                    }

                }
            }

    
            let out = []
            Object.keys(result).map(strategy => {
                out.push({

                    name: `${mapping[LAB_RESULT_STRATEGY][strategy]} Takeprofit`,
                    type: 'column',
                    data: result[strategy]['dataTakeProfit'],
                    // color: '#28a745',
                    color: this.getRandomColor(),

                })
                out.push({

                    name: `${mapping[LAB_RESULT_STRATEGY][strategy]} StopLoss`,
                    type: 'column',
                    data: result[strategy]['dataStopLoss'],
                    color: 'red'

                })

                out.sort((a,b)=>{ return a.name > b.name ? 1 : -1})
            })



            this.setState({
                chartOptions: {
                    series: out,
                    xAxis: {
                        categories: categories
                    }
                },

            })
        }



    }




}

export default ChartTotalRealPNLPerFlowPerStrategy;
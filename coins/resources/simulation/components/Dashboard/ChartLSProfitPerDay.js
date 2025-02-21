import React, { Component } from 'react';
import Highcharts from 'highcharts';
import HighchartsReact from 'highcharts-react-official'

class ChartLSProfitPerDay extends Component {
    constructor(props) {
        super(props);
        this.state = {
            ALL: true,
            coin: [],
            selected: true,
            temponary: [],
            Options: {
                chart: {}

                ,
                title: {
                    text: '<b> Total orders per coin</b>',
                },
                xAxis: {
                    categories: [


                    ],

                },
                yAxis: [
                    {
                        title: {
                            text: '<b></b>'
                        },
                        lineWidth : 1,
                        opposite : true,
                    }
                ],

                chart: {
                    height: 600

                },
                legend: {
                    enabled: true,

                },
                credits: {
                    enabled: false
                  },

                plotOptions: {
                    series: {
                        dataLabels: {
                            enabled: true
                        },
                        label: {
                            connectorAllowed: false
                        },
                    },

                },
                tooltip: {
                    style: {
                        fontSize: '9px'
                    },
                    pointFormat: '<div>{series.name} : <b>{point.y}</b></div>'

                },
                series: []
            }
        }
        this.updateChartWidth = this.updateChartWidth.bind(this);

    }
    componentDidMount() {

        this.getData();
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
                        <div style={{ display: 'flex', alignItems: 'center', position: 'absolute', top: 5, left: 5, zIndex: 100 }}>
                            <div className='button btn'  style={{  borderRadius: 0, padding: '2px 5px', fontWeight: (this.state.selected == true ? 'bold' : '100'), background: (this.state.selected == true ? 'rgb(230, 235, 245)' : '#f7f7f7') }} onClick={() => {
                                this.setState({ selected: !this.state.selected },
                                    () => this.dislegend()
                                );
                            }}>ALL</div>
                        </div>
                        <HighchartsReact
                            highcharts={Highcharts}
                            options={this.state.Options}
                        />

                    </div>

                </div>
            </>
        );
    }
    getData() {

        var res = App.getStrategy;
        if (res == undefined) return;

        var coin = [];
        var total = [];
        var totalTakeProfit = [];
        var totalStopLoss = [];
        Object.values(res).map(item => {
            var index = coin.indexOf(item[LAB_RESULT_SYMBOL]);


            if (index >= 0) {
                total[index]++;
                if (item[LAB_RESULT_STATUS] == [LAB_RESULT_STATUS_TAKEPROFIT]) {
                    totalTakeProfit[index]++;

                }
                if (item[LAB_RESULT_STATUS] == [LAB_RESULT_STATUS_STOPLOSS]) {
                    totalStopLoss[index]++;
                }

            } else {
                coin.push(item[LAB_RESULT_SYMBOL]);
                total.push(1);
                if (item[LAB_RESULT_STATUS] == [LAB_RESULT_STATUS_TAKEPROFIT]) {
                    totalTakeProfit.push(1);

                } else {
                    totalTakeProfit.push(0);
                }
                if (item[LAB_RESULT_STATUS] == [LAB_RESULT_STATUS_STOPLOSS]) {
                    totalStopLoss.push(1);

                } else {
                    totalStopLoss.push(0);
                }



            }


        })

       



        var objectdata = [];
        coin.map( (item,index) => {
            objectdata.push({
                'symbol' : item,
                'total' : total[index],
                'takeProfit' : totalTakeProfit[index],
                'stopLoss' : totalStopLoss[index],
            })
        })

        objectdata.sort(function(a, b){return a.total - b.total});

       

        

        var coin1 = [];
        var total1 = [];
        var totalTakeProfit1 = [];
        var totalStopLoss1 = [];

       objectdata.map(item => {
            coin1.push(item['symbol']);
            total1.push(item['total']);
            totalTakeProfit1.push(item['takeProfit']);
            totalStopLoss1.push(item['stopLoss']);
        })
  

        this.setState({
            temponary: [
                {
                    name: 'Long Short',
                    type: 'column',
                    data: total1,
                    color: '#007bff'
                }, {
                    name: 'Take Profit',
                    type: 'column',
                    data: totalTakeProfit1,
                    color: '#28a745'
                },
                , {
                    name: 'Stop Loss',
                    type: 'column',
                    data: totalStopLoss1,
                    color: 'red'
                }
            ],
            Options: {
                series: [
                    {
                        name: 'Long Short',
                        type: 'column',
                        data: total1,
                        color: '#007bff'
                    }, {
                        name: 'Take Profit',
                        type: 'column',
                        data: totalTakeProfit1,
                        color: '#28a745'
                    },
                    , {
                        name: 'Stop Loss',
                        type: 'column',
                        data: totalStopLoss1,
                        color: 'red'
                    }
                ],
                xAxis: {
                    categories: coin1
                }

            }
        })




    }

    dislegend() {
        if (this.state.selected) {
            Object.values(this.state.temponary).map(item => {
                item.visible = true
            })
        } else {
            Object.values(this.state.temponary).map(item => {
                item.visible = false
            })
        }

        this.setState({
            Options: {
                series: this.state.temponary
            }
        })
    }
}

export default ChartLSProfitPerDay;
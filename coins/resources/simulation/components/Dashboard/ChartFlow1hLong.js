import React, { Component } from 'react';
import Highcharts from 'highcharts';
import HighchartsReact from 'highcharts-react-official'

import Lab_results from '../../model/admin/Lab_results';

class ChartFlow1hLong extends Component {
    constructor(props) {
        super(props);
        this.state = {
            selected: true,
            seristemponary: [],
            strategyOptions: {},
            strategy: 0,
            ChartOptions: {
                chart: {
                    type: 'column',
                    height : 600
                },
                title: {
                    // text: '<b> Flow Risky3</b>',
                    text: '<b> 1h-Long</b>',
                    // align: 'left',
                    // x: 60,
                    // y: 18
                },
                xAxis: {
                    // categories: ['4h-Risky3', '1d-Risky3'],
                    categories: ['1h-Long'],
                },
                yAxis: {

                    title: {
                        text: '<b></b>'
                    },
                    lineWidth : 1,
                    opposite : true,
                },
                credits: {
                    enabled: false
                },
                tooltip: {
                    style: {
                        fontSize: '10px'
                    },
                    headerFormat: '',
                },
                plotOptions: {
                    series: {
                        dataLabels: {
                            enabled: true,
                            // formatter: function () {
                            //     return formatNumber(this.y);
                            // }
                        },
                        // groupPadding: 0,
                        // pointPadding: 0.1,
                    }
                },
                series: []
            }
        }
        this.updateChartWidth = this.updateChartWidth.bind(this);
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

            this.setState({
                ChartOptions: {
                    ...this.setState.ChartOptions,
                    chart: {
                        width: this.chartContainer ? this.chartContainer.clientWidth : 0,
                    }

                }
            })
        }, 500);
    }



    render() {
        return (
            <div className='p-col-12 p-md-12 ' >
                <div className='box_shadow ' ref={c => this.chartContainer = c} style={{ width: '100%', background: 'white', position: 'relative' }}>
                    <div style={{ display: 'flex', alignItems: 'center', position: 'absolute', top: 5, left: 5, zIndex: 100 }}>
                        <div className='button btn'  style={{  borderRadius: 0, padding: '2px 5px', fontWeight: (this.state.selected == true ? 'bold' : '100'), background: (this.state.selected == true ? 'rgb(230, 235, 245)' : '#f7f7f7') }} onClick={() => {
                            this.setState({ selected: !this.state.selected },
                                () => this.dislegend()
                            );
                        }}>ALL</div>

                    </div>
                    <HighchartsReact
                        highcharts={Highcharts}
                        options={this.state.ChartOptions}
                    />

                </div>

            </div>
        );
    }

    getData() {


        var resultModel = new Lab_results();
        var symbols = {};


       
        resultModel.getByAccount().then(res => {
            if (res['data']) {
                res = res['data'];
                var datasymbol = [];
                // var data1D = [];
                var data4H = [];


                res.map(item => {

                    var symbol = item[LAB_RESULT_SYMBOL];
                    var flow = item[LAB_RESULT_FLOW]

                    var index = datasymbol.indexOf(symbol);
                    if (index > -1) {
                        if (flow == '1h-Long') {

                            data4H[index] += 1;
                        } 

                    } else {
                        datasymbol.push(symbol);
                        if (flow == '1h-Long') {
                        
                            data4H.push(1);
                        } else {
                            data4H.push(0);
                           
                        }

                    }


                })

                var series = [];

                // datasymbol.map((total, index) => {
                //     var obj = {};
                //     obj['name'] = datasymbol[index];
                //     obj['data'] = [data4H[index], data1D[index]];
                //     series.push(obj);
                // })
                datasymbol.map((total, index) => {
                    var obj = {};
                    obj['name'] = datasymbol[index];
                    obj['data'] = [data4H[index]];
                    series.push(obj);
                })


                series.sort((a, b) => a.data[0] - b.data[0]);



                this.setState({
                    seristemponary: series,
                    ChartOptions: {
                        series
                    }
                })
            }
        })


    }

    dislegend() {
        if (this.state.selected) {
            this.state.seristemponary.map(item => {
                item.visible = true
            })
        } else {
            this.state.seristemponary.map(item => {
                item.visible = false
            })
        }

        this.setState({
            ChartOptions: {
                series: this.state.seristemponary
            }
        })
    }
}

export default ChartFlow1hLong;
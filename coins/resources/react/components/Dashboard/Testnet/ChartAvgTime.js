import React, { Component } from 'react';
import Highcharts from 'highcharts';
import HighchartsReact from 'highcharts-react-official'


import Testnet_results from '../../../model/admin/Testnet_results';

class ChartAvgTime extends Component {
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
                    // text: '<b> Avg Coin</b>',
                    // text: '<b>Total Orders 4H and 1D</b>',
                    text: '<b>Avg Time Orders 4H And 1D</b>',
                    // align: 'left',
                    // x: 60,
                    // y: 18
                },
                xAxis: {
                    categories: ['4h', '1d'],
                },
                yAxis: {

                    title: {
                        text: '<b></b>'
                    },
                    opposite : true,
                    startOnTick: true,
                    lineWidth: 1,
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

                        },
                        // groupPadding: 0,
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

        // if (!App.strategySelector || App.strategySelector.selected() == null) return;

        var resultModel = new Testnet_results();



        // resultModel.get([[[TESTNET_RESULT_STRATEGY, '=', App.strategySelector.selected()]]], { 'orderBy': TESTNET_RESULT_SELL_TIME, 'asc': false }).then(res => {
        // resultModel.getByStrategy( App.strategySelector.selected()).then(res => {
        resultModel.getByAccountTestnet(App.accountSelectorTestnet.selected()).then(res => {
            if (res['data']) {
                res = res['data'];
                var datasymbol = [];
                var data1D = [];
                var data4H = [];
                var count1D = [];
                var count4H = [];

                for (let i in res) {

                    var symbol = res[i][TESTNET_RESULT_SYMBOL];
                    var flow = res[i][TESTNET_RESULT_FLOW];

                    var sell_time = moment(res[i][TESTNET_RESULT_SELL_TIME], 'x');
                    var enter_time = moment(res[i][TESTNET_RESULT_CHART], 'x');

                    if (isNaN(sell_time) || isNaN(enter_time)) continue;

                    var diff = sell_time.diff(enter_time, 'minutes');

                    var index = datasymbol.indexOf(symbol);

                    if (index > -1) {
                        if (flow.startsWith('1D')) {
                            data1D[index] += diff;
                            count1D[index] += 1;
                        } else if (flow.startsWith('4H')) {
                            data4H[index] += diff;
                            count4H[index] += 1;
                        }

                    } else {
                        datasymbol.push(symbol);
                        if (flow.startsWith('1D')) {
                            data1D.push(diff);
                            data4H.push(0);
                            count1D.push(1);
                            count4H.push(0);
                        } else if (flow.startsWith('4H')) {
                            data4H.push(diff);
                            data1D.push(0);
                            count1D.push(0);
                            count4H.push(1);
                        } else {
                            data4H.push(0);
                            data1D.push(0);
                            count1D.push(0);
                            count4H.push(0);
                        }

                    }

                }


                var series = [];

                datasymbol.map((total, index) => {
                    var obj = {};
                    obj['name'] = datasymbol[index];
                    obj['data'] = [Math.floor(data4H[index] / count4H[index]), Math.floor(data1D[index] / count1D[index])];
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

export default ChartAvgTime;
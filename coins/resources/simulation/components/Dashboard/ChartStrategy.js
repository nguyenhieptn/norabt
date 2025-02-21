import React, { Component } from 'react';
import Highcharts from 'highcharts';
import HighchartsReact from 'highcharts-react-official'
class ChartStrategy extends Component {
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
                    // text: '<b>CRYPTO STRATEGY</b>',
                    // text: '<b>CRYPTO ACCOUNT</b>',
                    text: '<b>Total Profit Per Coin</b>',
                    // align: 'left',
                    // x: 60,
                    // y: 18,
                    margin : 45
                },
                xAxis: {

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
                            formatter: function () {
                                return formatNumber(this.y);
                            }
                        },
                        // maxPointWidth: 100,
                        // label: {
                        //     connectorAllowed: false
                        // },
                        pointWidth: 20,
                        groupPadding: 0,
                        //pointPadding: 0.1,
                        //	borderWidth: 0
                    }
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
                ChartOptions: {
                    ...this.setState.ChartOptions,
                    chart: {
                        width: this.chartContainer? this.chartContainer.clientWidth : 0,
                    }

                }
            })
        }, 500);
    }



    render() {
        return (
            <div className='' >
                <div className='box_shadow ' ref={c => this.chartContainer = c} style={{ width: '100%', background: 'white', position: 'relative' }}>
                    <div style={{ display: 'flex', alignItems: 'center', position: 'absolute', top: 8, left: 5, zIndex: 100 }}>
                        <div className='button btn' style={{  borderRadius: 0, padding: '2px 5px', fontWeight: (this.state.selected == true ? 'bold' : '100'), background: (this.state.selected == true ? 'rgb(230, 235, 245)' : '#f7f7f7') }} onClick={() => {
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

    async getData() {
        var res = App.getStrategy;
        if (res == undefined) return;
        var series = [];
        var coin = [];
        var total = [];


        Object.values(res).map(item => {
            var index = coin.indexOf(item[LAB_RESULT_SYMBOL]);

            // var profit = Number(item[LAB_RESULT_REAL_PROFIT]);
            var profit = Number(item[LAB_RESULT_REAL_PNL]);

            if (index >= 0) {
                if (item[LAB_RESULT_PENDING] == 0) {

                    total[index] += profit;
                }

            } else {
                coin.push(item[LAB_RESULT_SYMBOL]);
                total.push(profit);

            }


        })


        total.map((total, index) => {
            var obj = {};
            obj['name'] = coin[index];
            obj['data'] = [Number(total.toFixed(2))];
            series.push(obj);
        })

        series.sort(function (a, b) {
            return a.data[0] - b.data[0];
        });
   

        this.setState({
            seristemponary: series,
            ChartOptions: {
                series
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

export default ChartStrategy;
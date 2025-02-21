import React, { Component } from 'react';
import Highcharts from 'highcharts';
import HighchartsReact from 'highcharts-react-official'
class LSPerDay extends Component {
    constructor(props) {
        super(props);
        this.state = {
            selected: true,
            seriestemponary: [],
            chartOptions: {
                chart: {

                },
                title: {
                    text: '<b>LONG SHORT PER DAY </b>'
                },
                xAxis: {
                },
                yAxis: [
                    {
                        title: {
                            text: '<b>LONG SHORT</b>'
                        }
                    }
                ],
                chart: {
                    height: (8 / 16 * 80) + '%'

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
                            enabled: true
                        },
                        label: {
                            connectorAllowed: false
                        },
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
                chartOptions: {
                    ...this.setState.chartOptions,
                    chart: {
                        width: typeof (this.chartContainer) !== null && this.chartContainer.clientWidth,
                    }

                }
            })
        }, 500);
    }


    render() {
        return (
            <div className='p-col-12 p-md-12' >
                <div className='box_shadow ' ref={c => this.chartContainer = c} style={{ position: 'relative' }}>
                    <div style={{ display: 'flex', alignItems: 'center', position: 'absolute', top: 10, left: 5, zIndex: 100 }}>
                        <div className='button btn' style={{ border: 'solid thin darkgray', borderRadius: 5, padding: '2px 5px', fontWeight: 'bold', background: (this.state.selected ? '#28a745' : 'none') }} onClick={() => {
                            this.setState({ selected: !this.state.selected },
                                () => this.dislegend()
                            );
                        }}>ALL</div>


                    </div>
                    <HighchartsReact

                        highcharts={Highcharts}
                        options={this.state.chartOptions}
                    />
                </div>

            </div>
        );
    }

    dislegend() {
        if (this.state.selected) {
            this.state.seriestemponary.map(item => {
                item.visible = true
            })
        } else {
            this.state.seriestemponary.map(item => {
                item.visible = false
            })
        }

        this.setState({
            chartOptions: {
                series: this.state.seriestemponary
            }
        })
    }

    getData(data) {
        if (App.watchlist == undefined) return;
        var coin = [];
        var total = [];
        var series = [];
        var data;
        if (App.CryptoLsPerDay == undefined) {
            data = App.lab[0];
        } else {
            data = App.CryptoLsPerDay
        }
        Object.values(data).map(item => {
            var index = coin.indexOf(item.lab_symbol);
            if (index >= 0) {
                if (item[LAB_PENDING] == 0) {
                    total[index]++;
                }
            } else {
                coin.push(item.lab_symbol);
                total.push(1);
            }
        })
        total.map((total, index) => {
            var obj = {};
            obj['name'] = coin[index];
            obj['data'] = [Number(total.toFixed(4))];
            obj['type'] = 'column'
            series.push(obj);
        })
        series.sort(function (a, b) {
            return a.data[0] - b.data[0];
        });
        this.setState({
            seriestemponary: series,
            chartOptions: {
                series
            }
        })

    }
}

export default LSPerDay;
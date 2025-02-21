import React, { Component } from 'react';
import Highcharts from 'highcharts/highstock'
import HighchartsReact from 'highcharts-react-official'
// Load Highcharts modules
require('highcharts/indicators/indicators')(Highcharts)
require('highcharts/indicators/pivot-points')(Highcharts)
require('highcharts/indicators/macd')(Highcharts)
require('highcharts/modules/exporting')(Highcharts)
require('highcharts/modules/map')(Highcharts)
require('../../components/Dashboard/hollowcandlestick')(Highcharts)

import Lab from '../../model/admin/Lab'

class ChartTopCoin extends Component {
    constructor(props) {
        super(props);
        this.state = {
            increse: '1d',
            decrese: '1d',
            selected: true,
            selectedDecrease: true,
            seriusIncrease: [],
            seriusDecrease: [],
            ColumnProfitIncrease: {
                chart: {
                    type: 'column'
                },
                title: {
                    text: '<b>TOP UP</b>',
                    align: 'right',
                    x: -50,
                    y: 18
                },

                yAxis: {
                    min: 0,
                    title: {
                        text: '<b>PROFIT</b>'
                    }
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
            },
            ColumnProfitDecrease: {
                chart: {
                    type: 'column'
                },
                title: {
                    text: '<b>TOP DOWN</b>',
                    align: 'right',
                    x: -50,
                    y: 18

                },

                yAxis: {

                    title: {
                        text: '<b>PROFIT</b>'
                    }
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
            },
        }
        this.increse = ['1d', '2d', '3d', '1w', '1m', 'All'];
        this.updateChartWidth = this.updateChartWidth.bind(this)
    }
    componentDidMount() {
        this.getData('All', '1d');
        this.updateChartWidth();
        this.resize_ob_Increase = new ResizeObserver((entries) => {
            this.updateChartWidth()
        });
        this.resize_ob_Decrease = new ResizeObserver((entries) => {
            this.updateChartWidth()
        });
        this.resize_ob_Increase.observe(this.chartContainerIncrease);
        this.resize_ob_Decrease.observe(this.chartContainerDecrease);
    }
    componentWillUnmount() {
        if (this.resize_ob_Decrease) this.resize_ob_Decrease.unobserve(this.chartContainerDecrease);
        if (this.resize_ob_Increase) this.resize_ob_Increase.unobserve(this.chartContainerIncrease);
    }
    updateChartWidth() {
        if (this.updateWidthTimeout) clearTimeout(this.updateWidthTimeout);
        this.updateWidthTimeout = setTimeout(() => {

            this.setState({
                ColumnProfitIncrease: {
                    ...this.setState.ColumnProfitIncrease,
                    chart: {
                        width: this.chartContainerIncrease.clientWidth
                    }

                },
                ColumnProfitDecrease: {
                    ...this.setState.ColumnProfitDecrease,
                    chart: {
                        width: this.chartContainerDecrease.clientWidth
                    }

                },

            })
        }, 500);
    }

    getData(value, date) {
        var labModel = new Lab();
        var start = moment().format('X');

        var end;
        if (date == '1d') {
            end = moment().startOf("day").format('X');
        } else if (date == '2d') {
            end = moment().startOf("day").subtract(2, 'days').format('X');
        } else if (date == '3d') {
            end = moment().startOf("day").subtract(3, 'days').format('X');
        } else if (date == '1w') {
            end = moment().subtract(1, 'weeks').format('X');
        } else if (date == '1m') {
            end = moment().subtract(1, 'months').format('X');
        }
        if (date == 'All') {
            labModel.read().then(resLab => {

                var coin = [];
                var total = [];

                Object.values(resLab.data).map(item => {
                    var index = coin.indexOf(item.lab_symbol);

                    var profit = Number(item[LAB_PROFIT]) - 0.08;

                    if (index >= 0) {
                        if (item[LAB_PENDING] == 0) {

                            total[index] += profit;
                        }

                    } else {
                        coin.push(item.lab_symbol);
                        total.push(profit);

                    }
                })

                var increse = [];
                var decrese = [];

                total.map((total, index) => {
                    if (total >= 0) {
                        var obj = {};
                        obj['name'] = coin[index];
                        obj['data'] = [Number(total.toFixed(4))];
                        increse.push(obj);
                    } else {
                        var obj = {};
                        obj['name'] = coin[index];
                        obj['data'] = [Number(total.toFixed(4))];
                        decrese.push(obj);
                    }
                })

                increse.sort(function (a, b) {
                    return b.data[0] - a.data[0];
                });


                decrese.sort(function (a, b) {
                    return a.data[0] - b.data[0];
                });

                if (increse.length <= 20) {
                    increse.length = 8;
                } else {
                    increse.length = 10;
                }

                if (decrese.length <= 20) {
                    decrese.length = 8;
                } else {
                    decrese.length = 10;
                }

                increse.sort(function (a, b) {
                    return a.data[0] - b.data[0];
                });


                decrese.sort(function (a, b) {
                    return b.data[0] - a.data[0];
                });

                if (value == 1) {

                    this.setState({
                        seriusIncrease: increse,
                        ColumnProfitIncrease: {
                            series: increse
                        }
                    })
                } else if (value == 2) {
                    this.setState({
                        seriusDecrease: decrese,
                        ColumnProfitDecrease: {
                            series: decrese
                        }
                    })
                } else {
                    this.setState({
                        seriusIncrease: increse,
                        ColumnProfitIncrease: {
                            series: increse
                        },
                        seriusDecrease: decrese,
                        ColumnProfitDecrease: {
                            series: decrese
                        }
                    })
                }

            })




        } else {

            labModel.get([[[LAB_TIME, '>', end], [LAB_TIME, '<', start]]]).then(resLab => {

                var coin = [];
                var total = [];

                Object.values(resLab.data).map(item => {
                    var index = coin.indexOf(item.lab_symbol);

                    var profit = Number(item[LAB_PROFIT]) - 0.08;

                    if (index >= 0) {
                        if (item[LAB_PENDING] == 0) {

                            total[index] += profit
                        }


                    } else {
                        coin.push(item.lab_symbol);
                        total.push(profit);

                    }
                })


                var increse = [];
                var decrese = [];

                total.map((total, index) => {
                    if (total >= 0) {
                        var obj = {};
                        obj['name'] = coin[index];
                        obj['data'] = [Number(total.toFixed(4))];;
                        increse.push(obj);
                    } else {
                        var obj = {};
                        obj['name'] = coin[index];
                        obj['data'] = [Number(total.toFixed(4))];;
                        decrese.push(obj);
                    }
                })

                increse.sort(function (a, b) {
                    return b.data[0] - a.data[0];
                });

                decrese.sort(function (a, b) {
                    return a.data[0] - b.data[0];
                });

                if (increse.length <= 20) {
                    increse.length = 8;
                } else {
                    increse.length = 10;
                }

                if (decrese.length <= 20) {
                    decrese.length = 8;
                } else {
                    decrese.length = 10;
                }
                increse.sort(function (a, b) {
                    return a.data[0] - b.data[0];
                });


                decrese.sort(function (a, b) {
                    return b.data[0] - a.data[0];
                });

                if (value == 1) {

                    this.setState({
                        seriusIncrease: increse,
                        ColumnProfitIncrease: {
                            series: increse
                        }
                    })
                } else if (value == 2) {
                    this.setState({
                        seriusDecrease: decrese,
                        ColumnProfitDecrease: {
                            series: decrese
                        }
                    })
                } else {
                    this.setState({
                        seriusIncrease: increse,
                        ColumnProfitIncrease: {
                            series: increse
                        },
                        seriusDecrease: decrese,
                        ColumnProfitDecrease: {
                            series: decrese
                        }
                    })
                }

            })





        }
    }

    dislegend(value) {
        if (value == 1) {
            if (this.state.selected) {
                this.state.seriusIncrease.map(item => {
                    item.visible = true
                })
            } else {
                this.state.seriusIncrease.map(item => {
                    item.visible = false
                })
            }

            this.setState({
                ColumnProfitIncrease: {
                    series: this.state.seriusIncrease
                }
            })
        } else {
            if (this.state.selectedDecrease) {
                this.state.seriusDecrease.map(item => {
                    item.visible = true
                })
            } else {
                this.state.seriusDecrease.map(item => {
                    item.visible = false
                })
            }

            this.setState({
                ColumnProfitDecrease: {
                    series: this.state.seriusDecrease
                }
            })
        }
    }

    render() {
        return (
            <>
                {/* increse */}
                <div className='p-col-12 p-md-6 ' >
                    <div className='box_shadow ' ref={c => this.chartContainerIncrease = c} style={{ position: 'relative' }}>
                        <div style={{ display: 'flex', alignItems: 'center', position: 'absolute', top: 10, left: 5, zIndex: 100 }}>
                            <div className='button btn' style={{ border: 'solid thin darkgray', borderRadius: 5, padding: '2px 5px', fontWeight: 'bold', background: (this.state.selected ? '#28a745' : 'none') }} onClick={() => {
                                this.setState({ selected: !this.state.selected },
                                    () => this.dislegend(1)
                                );
                            }}>ALL</div>

                            {this.increse.map(item => {
                                return <div key={item} className='button btn' style={{ border: 'solid thin darkgray', borderRadius: 5, padding: '2px 5px', fontWeight: 'bold', background: (this.state.increse == item ? 'orange' : 'none') }} onClick={() => {
                                    this.setState({ increse: item },
                                        () => this.getData(1, item)
                                    );
                                }}>{item.toUpperCase()}</div>
                            })}


                        </div>
                        <HighchartsReact
                            highcharts={Highcharts}
                            options={this.state.ColumnProfitIncrease}
                        />
                    </div>

                </div>
                {/* decrease */}
                <div className='p-col-12 p-md-6' >
                    <div className='box_shadow ' ref={c => this.chartContainerDecrease = c} style={{ position: 'relative' }}>
                        <div style={{ display: 'flex', alignItems: 'center', position: 'absolute', top: 10, left: 5, zIndex: 100 }}>
                            <div className='button btn' style={{ border: 'solid thin darkgray', borderRadius: 5, padding: '2px 5px', fontWeight: 'bold', background: (this.state.selectedDecrease ? '#28a745' : 'none') }} onClick={() => {
                                this.setState({ selectedDecrease: !this.state.selectedDecrease },
                                    () => this.dislegend(2)
                                );
                            }}>ALL</div>

                            {this.increse.map(item => {
                                return <div key={item} className='button btn' style={{ border: 'solid thin darkgray', borderRadius: 5, padding: '2px 5px', fontWeight: 'bold', background: (this.state.decrese == item ? 'orange' : 'none') }} onClick={() => {
                                    this.setState({ decrese: item },
                                        () => this.getData(2, item)
                                    );
                                }}>{item.toUpperCase()}</div>
                            })}

                        </div>
                        <HighchartsReact
                            highcharts={Highcharts}
                            options={this.state.ColumnProfitDecrease}
                        />
                    </div>

                </div>
            </>
        );
    }
}

export default ChartTopCoin;
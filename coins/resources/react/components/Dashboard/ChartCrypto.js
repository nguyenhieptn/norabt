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
import Watchlist from '../../model/admin/Watchlist'
class ChartCrypto extends Component {
    constructor(props) {
        super(props);
        this.state = {
            line: '1d',
            coin: [],
            selected: true,
            seristempanary: [],
            LineChart: {
                title: {
                    text: '<b>TOTAL PROFIT PER CRYPTO</b>',
                    align: 'right',
                    x: -50,
                    y: 18
                },
                tooltip: {
                    style: {
                        fontSize: '10px'
                    },
                    shared: true,
                    split: false,
                    formatter: function () {

                        var tmp = this.points,
                            txt = '<b>' + moment(this.x).format("dddd, MMM DD, k:mm:ss") + '</b>';
                        tmp.sort(function (a, b) {
                            return b.y - a.y;
                        });

                        $.each(tmp, function (i, point) {
                            txt += '<br/><span style="color:' + point.color + '">\u25CF</span> ' + point.series.name + ': ' + ': <b> ' + point.y + '</b> ';
                        });

                        return txt;
                    }
                },
                yAxis: [

                    {

                        labels: {
                            align: 'auto',
                            style: {
                                fontSize: "10px"
                            }
                        },

                        title: {
                            text: '<b>TOTAL PROFIT PER CRYPTO</b>',
                            x: 15
                        },

                        height: '100%',
                        lineWidth: 2,
                        resize: {
                            enabled: true
                        }
                    },

                ],
                chart: {
                    height: (8 / 16 * 83) + '%', // 16:9 ratio

                },
                legend: {
                    enabled: true
                },
                plotOptions: {
                    series: {
                        label: {
                            connectorAllowed: false
                        },
                    }
                },

                rangeSelector: {
                    buttonPosition: {
                        align: 'left',
                        y: '-1',
                    },

                    allButtonsEnabled: true,
                    buttons:
                        [
                            {
                                text: '1D',
                                type: 'day',
                                count: 1,

                            },
                            {
                                text: '2D',
                                type: 'day',
                                count: 2,
                            },
                            {
                                text: '1W',
                                type: 'week',
                                count: 6,

                            },
                            {
                                type: 'all',
                                text: 'All'
                            },
                        ],
                    inputEnabled: false,
                    selected: 0,
                    buttonSpacing: 10,
                },

                series: [],

            }
        }
        this.lineOption = ['1d', '2d', '3d', '4d', '5d', '6d', '1w', '2w', '1m'];
        this.updateChartWidth = this.updateChartWidth.bind(this);


        Highcharts.setOptions({
            time: {
                timezoneOffset: moment().utcOffset(),
                useUTC: false
            }
        });

    }

    componentDidMount() {
        if (App.watchlist == undefined) return;
        if (App.lab == undefined) return;
        var coin = [];
        Object.values(App.watchlist).map(item => {
            coin.push(item.wl_symbol);
        })
        this.setState({ coin }, () => this.getDataLineChart('1d'))

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
                LineChart: {
                    ...this.setState.LineChart,
                    chart: {
                        width: this.chartContainer? this.chartContainer.clientWidth : 0,
                        // height: this.chartContainer.clientHeight

                    }

                }
            })
        }, 500);
    }
    dislegend() {

        var temponary;
        if (this.state.LineChart.series == undefined) {
            temponary = this.state.seristempanary
        } else {
            temponary = [... this.state.LineChart.series]
        };

        if (this.state.selected) {
            temponary.map((item, index) => {
                item.visible = true
            })
        } else {
            temponary.map((item, index) => {
                if (index > 2) {
                    item.visible = false
                }
            })
        }
        this.setState({
            LineChart: {
                series: temponary
            }
        })
    }
    render() {
        return (
            <div className='p-col-12 p-md-12 cushide' >
                <div className='box_shadow ' ref={c => this.chartContainer = c} style={{ width: '100%', background: 'white', position: 'relative' }}>
                    <div style={{ display: 'flex', alignItems: 'center', position: 'absolute', top: 5, left: 5, zIndex: 100 }}>
                        <div className='button btn' style={{ border: 'solid thin darkgray', borderRadius: 5, padding: '2px 5px', fontWeight: 'bold', background: (this.state.selected ? '#28a745' : 'none') }} onClick={() => {
                            this.setState({ selected: !this.state.selected },
                                () => this.dislegend()
                            );
                        }}>ALL</div>

                        {this.lineOption.map(item => {
                            return <div key={item} className='button btn' style={{ border: 'solid thin darkgray', borderRadius: 5, padding: '2px 5px', fontWeight: 'bold', background: (this.state.line == item ? 'orange' : 'none') }} onClick={() => {
                                this.setState({ line: item },
                                    () => this.getDataLineChart(item)
                                );
                            }}>{item.toUpperCase()}</div>
                        })}

                    </div>
                    <HighchartsReact
                        highcharts={Highcharts}
                        options={this.state.LineChart}
                        constructorType={'stockChart'}
                    />
                </div>

            </div>
        );
    }

    async getDataLineChart(date) {
        var labModel = new Lab();
        var series = [];

        this.state.coin.map(coin => {
            series.push({
                name: coin,
                data: [],
                lineWidth: 0.8,
            })
        })




        if (date == '1d') {


            for (i = 0; i <= 9; i++) {


                var time = moment().endOf('day').subtract(i, 'days').format('X') * 1000;

                var coin = [];
                var total = [];


                Object.values(App.lab[i]).map(item => {
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





                if (coin.length > 0) {

                    Object.keys(series).map((keys) => {
                        var item = series[keys];

                        var index = coin.indexOf(item.name);
                        if (index >= 0) {
                            var value = total[index].toFixed(6);
                            series[keys].data.unshift([time, Number(value)]);
                        } else {
                            series[keys].data.unshift([time, 0]);
                        }


                    })

                } else {

                    Object.keys(series).map((keys) => {

                        series[keys].data.unshift([time, 0]);

                    })
                }


            }

            this.setState({
                seristempanary: series,
                LineChart: {
                    series: series,
                }
            })

        } else if (date == '2d') {
            var start;
            var end;
            for (i = 0; i <= 18; i = i + 2) {

                if (i == 0) {
                    start = moment().startOf("day").format('X');
                    end = moment().format('X');
                } else {
                    start = moment().startOf("day").subtract(i, 'days').format('X');
                    end = moment().startOf("day").subtract(i - 2, 'days').format('X');
                }

                if (i == 0) {
                    var time = moment().endOf('day').subtract(i, 'days').format('X') * 1000;

                } else {
                    var time = moment().endOf('day').subtract(i - 1, 'days').format('X') * 1000;

                }


                var resLab = await labModel.get([[[LAB_TIME, '>', start], [LAB_TIME, '<', end]]]);


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


                if (coin.length > 0) {

                    Object.keys(series).map((keys) => {
                        var item = series[keys];

                        var index = coin.indexOf(item.name);
                        if (index >= 0) {
                            var value = total[index].toFixed(6);
                            series[keys].data.unshift([time, Number(value)]);
                        } else {
                            series[keys].data.unshift([time, 0]);
                        }


                    })

                } else {

                    Object.keys(series).map((keys) => {

                        series[keys].data.unshift([time, 0]);

                    })
                }


            }


            this.setState({
                LineChart: {
                    series: series,
                }
            })


        } else if (date == '3d') {
            var start;
            var end;
            for (i = 0; i <= 27; i = i + 3) {

                if (i == 0) {
                    start = moment().startOf("day").format('X');
                    end = moment().format('X');
                } else {
                    start = moment().startOf("day").subtract(i, 'days').format('X');
                    end = moment().startOf("day").subtract(i - 3, 'days').format('X');
                }

                if (i == 0) {
                    var time = moment().endOf('day').subtract(i, 'days').format('X') * 1000;
                } else {
                    var time = moment().endOf('day').subtract(i - 2, 'days').format('X') * 1000;
                }
                var resLab = await labModel.get([[[LAB_TIME, '>', start], [LAB_TIME, '<', end]]]);


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



                if (coin.length > 0) {

                    Object.keys(series).map((keys) => {
                        var item = series[keys];

                        var index = coin.indexOf(item.name);
                        if (index >= 0) {
                            var value = total[index].toFixed(6);
                            series[keys].data.unshift([time, Number(value)]);
                        } else {
                            series[keys].data.unshift([time, 0]);
                        }


                    })

                } else {

                    Object.keys(series).map((keys) => {

                        series[keys].data.unshift([time, 0]);

                    })
                }

            }

            this.setState({
                LineChart: {
                    series: series,
                }
            })
        } else if (date == '4d') {
            var start;
            var end;
            for (i = 0; i <= 36; i = i + 4) {

                if (i == 0) {
                    start = moment().startOf("day").format('X');
                    end = moment().format('X');
                } else {
                    start = moment().startOf("day").subtract(i, 'days').format('X');
                    end = moment().startOf("day").subtract(i - 4, 'days').format('X');
                }

                if (i == 0) {
                    var time = moment().endOf('day').subtract(i, 'days').format('X') * 1000;
                } else {
                    var time = moment().endOf('day').subtract(i - 3, 'days').format('X') * 1000;
                }

                var resLab = await labModel.get([[[LAB_TIME, '>', start], [LAB_TIME, '<', end]]]);


                var coin = [];
                var total = [];


                Object.values(resLab.data).map(item => {
                    var index = coin.indexOf(item.lab_symbol);

                    var profit = Number(item[LAB_PROFIT]) - 0.08

                    if (index >= 0) {
                        if (item[LAB_PENDING] == 0) {

                            total[index] += profit

                        }

                    } else {
                        coin.push(item.lab_symbol);
                        total.push(profit);

                    }
                })



                if (coin.length > 0) {

                    Object.keys(series).map((keys) => {
                        var item = series[keys];

                        var index = coin.indexOf(item.name);
                        if (index >= 0) {
                            var value = total[index].toFixed(6);
                            series[keys].data.unshift([time, Number(value)]);
                        } else {
                            series[keys].data.unshift([time, 0]);
                        }


                    })

                } else {

                    Object.keys(series).map((keys) => {

                        series[keys].data.unshift([time, 0]);

                    })
                }

            }

            this.setState({
                LineChart: {
                    series: series,
                }
            })
        } else if (date == '5d') {
            var temponary;
            var start;
            var end;
            for (i = 0; i <= 45; i = i + 5) {
                if (i == 0) {
                    start = moment().startOf("day").format('X');
                    end = moment().format('X');
                } else {
                    start = moment().startOf("day").subtract(i, 'days').format('X');
                    end = moment().startOf("day").subtract(i - 5, 'days').format('X');
                }

                if (i == 0) {
                    var time = moment().endOf('day').subtract(i, 'days').format('X') * 1000;
                } else {
                    var time = moment().endOf('day').subtract(i - 4, 'days').format('X') * 1000;
                }

                var resLab = await labModel.get([[[LAB_TIME, '>', start], [LAB_TIME, '<', end]]]);


                var coin = [];
                var total = [];


                Object.values(resLab.data).map(item => {
                    var index = coin.indexOf(item.lab_symbol);

                    var profit = Number(item[LAB_PROFIT]) - 0.08

                    if (index >= 0) {
                        if (item[LAB_PENDING] == 0) {

                            total[index] += profit

                        }

                    } else {
                        coin.push(item.lab_symbol);
                        total.push(profit);

                    }
                })



                if (coin.length > 0) {

                    Object.keys(series).map((keys) => {
                        var item = series[keys];

                        var index = coin.indexOf(item.name);
                        if (index >= 0) {
                            var value = total[index].toFixed(6);
                            series[keys].data.unshift([time, Number(value)]);
                        } else {
                            series[keys].data.unshift([time, 0]);
                        }


                    })

                } else {

                    Object.keys(series).map((keys) => {

                        series[keys].data.unshift([time, 0]);

                    })
                }

            }


            this.setState({
                LineChart: {
                    series: series,

                }
            })
        } else if (date == '6d') {

            var start;
            var end;

            for (i = 0; i <= 54; i = i + 6) {

                if (i == 0) {
                    start = moment().startOf("day").format('X');
                    end = moment().format('X');
                } else {
                    start = moment().startOf("day").subtract(i, 'days').format('X');
                    end = moment().startOf("day").subtract(i - 6, 'days').format('X');
                }
                if (i == 0) {
                    var time = moment().endOf('day').subtract(i, 'days').format('X') * 1000;
                } else {
                    var time = moment().endOf('day').subtract(i - 5, 'days').format('X') * 1000;
                }

                var resLab = await labModel.get([[[LAB_TIME, '>', start], [LAB_TIME, '<', end]]]);


                var coin = [];
                var total = [];


                Object.values(resLab.data).map(item => {
                    var index = coin.indexOf(item.lab_symbol);

                    var profit = Number(item[LAB_PROFIT]) - 0.08

                    if (index >= 0) {
                        if (item[LAB_PENDING] == 0) {

                            total[index] += profit

                        }

                    } else {
                        coin.push(item.lab_symbol);
                        total.push(profit);

                    }
                })



                if (coin.length > 0) {

                    Object.keys(series).map((keys) => {
                        var item = series[keys];

                        var index = coin.indexOf(item.name);
                        if (index >= 0) {
                            var value = total[index].toFixed(6);
                            series[keys].data.unshift([time, Number(value)]);
                        } else {
                            series[keys].data.unshift([time, 0]);
                        }


                    })

                } else {

                    Object.keys(series).map((keys) => {

                        series[keys].data.unshift([time, 0]);

                    })
                }

            }

            this.setState({
                LineChart: {
                    series: series,
                }
            })
        } else if (date == '1w') {
            var start;
            var end;

            for (i = 0; i <= 9; i++) {

                if (i == 0) {
                    start = moment().startOf("week").format('X');
                    end = moment().format('X');
                } else {
                    start = moment().startOf("week").subtract(i, 'weeks').format('X');
                    end = moment().startOf("week").subtract(i - 1, 'weeks').format('X');


                }
                if (i == 0) {
                    var time = moment().endOf('day').subtract(i, 'days').format('X') * 1000;


                } else {
                    var time = moment().endOf("week").subtract(i, 'weeks').format('X') * 1000;


                }

                var resLab = await labModel.get([[[LAB_TIME, '>', start], [LAB_TIME, '<', end]]]);


                var coin = [];
                var total = [];


                Object.values(resLab.data).map(item => {
                    var index = coin.indexOf(item.lab_symbol);

                    var profit = Number(item[LAB_PROFIT]) - 0.08

                    if (index >= 0) {
                        if (item[LAB_PENDING] == 0) {

                            total[index] += profit

                        }

                    } else {
                        coin.push(item.lab_symbol);
                        total.push(profit);

                    }
                })



                if (coin.length > 0) {

                    Object.keys(series).map((keys) => {
                        var item = series[keys];

                        var index = coin.indexOf(item.name);
                        if (index >= 0) {
                            var value = total[index].toFixed(6);
                            series[keys].data.unshift([time, Number(value)]);
                        } else {
                            series[keys].data.unshift([time, 0]);
                        }


                    })

                } else {

                    Object.keys(series).map((keys) => {

                        series[keys].data.unshift([time, 0]);

                    })
                }
            }
            this.setState({
                LineChart: {
                    series: series,

                }
            })
        } else if (date == '2w') {

            var start;
            var end;


            for (i = 0; i <= 18; i = i + 2) {


                if (i == 0) {
                    start = moment().startOf("week").format('X');
                    end = moment().format('X');
                } else {
                    start = moment().startOf("week").subtract(i, 'weeks').format('X');
                    end = moment().startOf("week").subtract(i - 2, 'weeks').format('X');

                }
                if (i == 0) {
                    var time = moment().endOf('day').subtract(i, 'days').format('X') * 1000;
                } else {
                    var time = moment().endOf('week').subtract(i - 1, 'weeks').format('X') * 1000;
                }

                var resLab = await labModel.get([[[LAB_TIME, '>', start], [LAB_TIME, '<', end]]]);


                var coin = [];
                var total = [];


                Object.values(resLab.data).map(item => {
                    var index = coin.indexOf(item.lab_symbol);

                    var profit = Number(item[LAB_PROFIT]) - 0.08

                    if (index >= 0) {
                        if (item[LAB_PENDING] == 0) {

                            total[index] += profit

                        }

                    } else {
                        coin.push(item.lab_symbol);
                        total.push(profit);

                    }
                })



                if (coin.length > 0) {

                    Object.keys(series).map((keys) => {
                        var item = series[keys];

                        var index = coin.indexOf(item.name);
                        if (index >= 0) {
                            var value = total[index].toFixed(6);
                            series[keys].data.unshift([time, Number(value)]);
                        } else {
                            series[keys].data.unshift([time, 0]);
                        }


                    })

                } else {

                    Object.keys(series).map((keys) => {

                        series[keys].data.unshift([time, 0]);

                    })
                }
            }

            this.setState({
                LineChart: {
                    series: series,

                }
            })
        } else if (date == '1m') {

            var start;
            var end;


            for (var i = 0; i <= 9; i++) {



                if (i == 0) {
                    start = moment().startOf("months").format('X');
                    end = moment().format('X');
                } else {
                    start = moment().startOf("months").subtract(i, 'months').format('X');
                    end = moment().endOf("months").subtract(i, 'months').format('X');
                }
                if (i == 0) {
                    var time = moment().endOf('day').subtract(i, 'days').format('X') * 1000;


                } else {
                    var time = moment().endOf("month").subtract(i, 'months').format('X') * 1000;

                }
                var resLab = await labModel.get([[[LAB_TIME, '>', start], [LAB_TIME, '<', end]]]);


                var coin = [];
                var total = [];


                Object.values(resLab.data).map(item => {
                    var index = coin.indexOf(item.lab_symbol);

                    var profit = Number(item[LAB_PROFIT]) - 0.08

                    if (index >= 0) {
                        if (item[LAB_PENDING] == 0) {

                            total[index] += profit

                        }

                    } else {
                        coin.push(item.lab_symbol);
                        total.push(profit);

                    }
                })



                if (coin.length > 0) {

                    Object.keys(series).map((keys) => {
                        var item = series[keys];

                        var index = coin.indexOf(item.name);
                        if (index >= 0) {
                            var value = total[index].toFixed(6);
                            series[keys].data.unshift([time, Number(value)]);
                        } else {
                            series[keys].data.unshift([time, 0]);
                        }


                    })

                } else {

                    Object.keys(series).map((keys) => {

                        series[keys].data.unshift([time, 0]);

                    })
                }

            }

            this.setState({
                LineChart: {
                    series: series,

                }
            })
        }








    }
}

export default ChartCrypto;
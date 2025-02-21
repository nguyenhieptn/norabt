import React, { Component } from 'react';
import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official'




class ChartLongShort extends Component {
    constructor(props) {
        super(props);

        this.state = {
            coin: [],
            selected: false,
            seriestemponary: [],
            OptionsLongShort: {

                title: {
                    text: '<b>TOTAL PROFIT AND SESSION PER DAY</b>',
                },
                xAxis: {

                },

                navigator: {
                    enabled: false
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


                yAxis: [{

                    labels: {
                        align: 'auto',
                        style: {
                            fontSize: "10px"
                        }
                    },

                    title: {
                        text: '<b>COIN PER DAY</b>',
                        x: 15
                    },

                    height: '50%',
                    lineWidth: 2,
                    resize: {
                        enabled: true
                    }
                }, {

                    top: '55%',
                    height: '45%',
                    labels: {
                        // distance: '75%',
                        align: 'auto',
                        style: {
                            fontSize: "10px"
                        }
                    },
                    offset: 0,
                    lineWidth: 2,
                    title: {
                        text: '<b>LONG SHORT</b>',
                        x: 15
                    }
                }
                ],

                chart: {
                    height: (8 / 16 * 100) + '%'

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
                tooltip: {
                    style: {
                        fontSize: '9px'
                    },
                    shared: true,
                    split: false,
                    formatter: function () {

                        var tmp = this.points;
                        var profit = tmp.slice(0, tmp.length / 2);

                        var ls = tmp.slice(tmp.length / 2, tmp.length + 1);
                        var tempnary = [];
                        profit.sort(function (a, b) {
                            return b.y - a.y;
                        });

                        profit.map((profit) => {
                            var a = ls.filter(ls => ls.series.name == profit.series.name);
                            tempnary.push(a[0]);
                        })


                        var txt = '<b>' + moment(this.x).format("dddd, MMM DD, k:mm:ss") + '</b>';


                        $.each(profit, function (i, point) {
                            txt += '<br/><span style="color:' + point.color + '">\u25CF</span> ' + point.series.name + ': ' + ': <b> ' + point.y + '</b> ';
                        });
                        $.each(tempnary, function (i, point) {
                            txt += '<br/><span style="color:' + point.color + '">\u25CF</span> L/S - ' + point.series.name + ': ' + ': <b> ' + point.y + '</b> ';
                        });

                        return txt;
                    }
                },
                series: []
            }
        }
        this.updateChartWidth = this.updateChartWidth.bind(this);

    }
    componentDidMount() {
        if (App.watchlist == undefined) return;
        var coin = [];
        Object.values(App.watchlist).map(item => {
            if (item.wl_symbol == 'ADAUSDT' || item.wl_symbol == 'MATICUSDT' || item.wl_symbol == 'AVAXUSDT') {
                coin.unshift(item.wl_symbol);
            } else {
                coin.push(item.wl_symbol);
            }

        })
        this.setState({ coin }, () => this.getData())

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
                OptionsLongShort: {
                    ...this.setState.OptionsLongShort,
                    chart: {
                        width: this.chartContainer.clientWidth
                    }

                }
            })
        }, 500);
    }
    dislegend() {
        var temponary;
        if (this.state.OptionsLongShort.series == undefined) {
            temponary = this.state.seriestemponary
        } else {
            temponary = [... this.state.OptionsLongShort.series]
        };

        if (this.state.selected) {
            temponary.map((item, index) => {
                item.visible = true
            })
        } else {
            var mid = temponary.length / 2;
            temponary.map((item, index) => {
                if (index >= 0 && index <= 2 || index >= mid && index <= mid + 2) {
                    item.visible = true
                } else {
                    item.visible = false
                }
            })
        }
        this.setState({
            OptionsLongShort: {
                series: temponary
            }
        })
    }
    render() {
        return (
            <>
                <div className='p-col-12 p-md-12 cushide' >
                    <div className='box_shadow ' ref={c => this.chartContainer = c} style={{ position: 'relative' }}>
                        <div style={{ display: 'flex', alignItems: 'center', position: 'absolute', top: 5, left: 5, zIndex: 100 }}>
                            <div className='button btn' style={{ border: 'solid thin darkgray', borderRadius: 5, padding: '2px 5px', fontWeight: 'bold', background: (this.state.selected ? '#28a745' : 'none') }} onClick={() => {
                                this.setState({ selected: !this.state.selected },
                                    () => this.dislegend()
                                );
                            }}>ALL</div>
                        </div>

                        <HighchartsReact
                            constructorType={'stockChart'}
                            highcharts={Highcharts}
                            options={this.state.OptionsLongShort}
                        />

                    </div>

                </div>
            </>
        );
    }

    async getData() {
        var series = [];
        var seriesLongShort = [];

        this.state.coin.map((coin, index) => {
            if (index > 2) {
                series.push({
                    name: coin,
                    data: [],
                    lineWidth: 0.8,
                    id: coin,
                    visible: false
                });
                seriesLongShort.push({
                    yAxis: 1,
                    name: coin,
                    data: [],
                    lineWidth: 0.8,
                    linkedTo: coin,
                    id: 'longshort_' + coin,
                    visible: false
                })
            } else {
                series.push({
                    name: coin,
                    data: [],
                    lineWidth: 0.8,
                    id: coin,
                    visible: true
                });
                seriesLongShort.push({
                    yAxis: 1,
                    name: coin,
                    data: [],
                    lineWidth: 0.8,
                    linkedTo: coin,
                    id: 'longshort_' + coin,
                    visible: true
                })
            }
        })



        var categories = [];
        for (var i = 0; i <= 9; i++) {
            var temponary = moment().subtract(i, 'days').format("DD/MM/YYYY");
            categories.unshift(temponary);
            // if (i == 0) {
            //     start = moment().startOf("day").format('X');
            //     end = moment().format('X');
            // } else {
            //     start = moment().startOf("day").subtract(i, 'days').format('X');
            //     end = moment().startOf("day").subtract(i - 1, 'days').format('X');
            // }


            var time = moment().endOf('day').subtract(i, 'days').format('X') * 1000;

            var coin = [];
            var total = [];

            var coinLongShort = [];
            var totalLongShort = [];

            Object.values(App.lab[i]).map(item => {
                var index = coin.indexOf(item.lab_symbol);

                var profit = Number(item[LAB_PROFIT]) - 0.08

                if (index >= 0) {
                    if (item[LAB_PENDING] == 0) {

                        total[index] += profit;
                        totalLongShort[index]++

                    }

                } else {
                    coin.push(item.lab_symbol);
                    total.push(profit);
                    coinLongShort.push(item.lab_symbol);
                    totalLongShort.push(1);

                }
            })

            if (coin.length > 0) {

                Object.keys(series).map((keys) => {
                    var item = series[keys];

                    var index = coin.indexOf(item.name);
                    if (index >= 0) {
                        var value = total[index].toFixed(6);
                        series[keys].data.unshift([time, Number(value)]);
                        seriesLongShort[keys].data.unshift([time, totalLongShort[index]]);

                    } else {
                        series[keys].data.unshift([time, 0]);
                        seriesLongShort[keys].data.unshift([time, 0]);
                    }


                })

            } else {

                Object.keys(series).map((keys) => {

                    series[keys].data.unshift([time, 0]);
                    seriesLongShort[keys].data.unshift([time, 0]);
                })
            }


        }

        this.setState({
            seriestemponary: series.concat(seriesLongShort),
            OptionsLongShort: {
                series: series.concat(seriesLongShort)

            }
        })

    }
}

export default ChartLongShort;
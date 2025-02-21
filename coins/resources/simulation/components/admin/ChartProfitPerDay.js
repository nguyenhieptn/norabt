import React, { Component } from 'react';
import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official'
import Lab_watchlist from '../../model/admin/Lab_watchlist';
import Lab_results from '../../model/admin/Lab_results';

class ChartProfitPerDay extends Component {
    constructor(props) {
        super(props);
        this.state = {
            ALL: true,
            coin: [],
            selected: {},
            Options: {
                chart: {
                    height: (8 / 16 * 73) + '%',
                    panning: {
                        enabled: true,
                        type: 'x'
                    },
                    panKey: 'shift',
                    zoomType: 'x'
                }

                ,
                title: {
                    text: '<b>TOTAL PROFIT PER DAY</b>',
                },
                xAxis: {
                    type: 'datetime',

                },
                credits: {
                    enabled: false
                  },
                  scrollbar: {
                    enabled: false
                },

                yAxis: [
                    {
                        startOnTick: true,
                        title: {
                            text: '<b></b>',
                        },

                        startOnTick: false,

                        labels: {
                            align: 'left'
                        }
                    }
                ],

                rangeSelector: {
                    buttonPosition: {
                        align: 'left',
                        // x: '0',
                        y: '-1',
                    },

                    allButtonsEnabled: true,
                    buttons:
                        [
                            {
                                text: '1H',
                                type: 'hour',
                                count: 1,

                            },
                            {
                                text: '2H',
                                type: 'hour',
                                count: 2,
                            },
                            {
                                text: '6H',
                                type: 'hour',
                                count: 6,

                            }, {
                                text: '12H',
                                type: 'hour',
                                count: 12,

                            }, {
                                text: '24H',
                                type: 'hour',
                                count: 24,

                            }, {
                                type: 'all',
                                text: 'All'
                            },
                        ],
                    inputEnabled: false,
                    buttonSpacing: 10,
                },


                legend: {
                    enabled: false,

                },
                plotOptions: {
                    series: {
                        dataLabels: {
                            enabled: true
                        },
                        maxPointWidth: 100,
                        turboThreshold: 0 // Comment out this code to display error
                    },

                    column: {
                        zones: [{
                            value: 0,
                            color: 'red'
                        }, {
                            color: '#007bff'
                        }]
                    }

                },
                tooltip: {
                    style: {
                        fontSize: '9px'
                    },
                    pointFormat: '<div>PROFIT <b>{point.y}</b></div>'

                },
                series: [
                    {
                        type: 'column',
                        data: [],

                    },
                    // {
                    //     yAxis: 1,
                    //     data: [],
                    // }
                ]
            }
        }
        this.updateChartWidth = this.updateChartWidth.bind(this);

        this.colors = {};

        Highcharts.setOptions({
            time: {
                timezoneOffset: moment().utcOffset(),
                useUTC: false
            }
        });

    }
    componentDidMount() {
        var wlModel = new Lab_watchlist();
        wlModel.getWatchlist(res => {
            if (res) {
                Object.values(res).map(item => {
                    var color = this.getRandomColor();
                    coin.push({ name: item[LAB_WL_SYMBOL], color: color });
                    selected.push(item[LAB_WL_SYMBOL]);
                })
                this.setState({ coin, selected, temponary: selected }, () => this.getData(true))
            }
        })

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
    getRandomColor(item) {
        if (isset(this.colors[item])) return this.colors[item];
        var letters = '0123456789ABCDEF';
        var color = '#';
        for (var i = 0; i < 6; i++) {
            color += letters[Math.floor(Math.random() * 16)];
        }
        this.colors[item] = color;
        return this.colors[item];
    }
    render() {
        return (
            <>
                <div className='p-col-12 p-md-12 ' >
                    <div className='box_shadow ' ref={c => this.chartContainer = c} style={{ position: 'relative' }}>
                        <div style={{ display: 'flex', alignItems: 'center', position: 'absolute', top: 5, left: 5, zIndex: 100 }}>
                            <div className='button btn' style={{ border: 'solid thin darkgray', borderRadius: 5, padding: '2px 5px', fontWeight: 'bold', background: (this.state.ALL ? '#28a745' : 'none') }} onClick={() => {
                                if (this.state.ALL) {
                                    this.setState({ ALL: !this.state.ALL, selected: [] },
                                        () => this.getData()
                                    );
                                } else {
                                    var selected = {};
                                    this.state.coin.map(item => selected[item] = true)
                                    this.setState({ ALL: !this.state.ALL, selected: selected },
                                        () => this.getData()
                                    );
                                }

                            }}>ALL</div>
                        </div>
                        <HighchartsReact
                            highcharts={Highcharts}
                            options={this.state.Options}
                            constructorType={'stockChart'}
                        />
                        <div style={{ display: 'flex', flexWrap: 'wrap', width: '90%', margin: 'auto', paddingBottom: '10px' }}>
                            {this.state.coin.map(item => {

                                return (
                                    <div key={item} style={{ width: '125px', cursor: 'pointer', marginBottom: '5px' }} onClick={() => {


                                        var selected = this.state.selected;
                                        if (selected[item]) {
                                            delete selected[item]
                                        } else {
                                            selected[item] = true
                                        }
                                        this.setState({ selected, ALL: false }, () => this.getData())


                                    }}>
                                        <div style={{ borderRadius: '50%', backgroundColor: this.getRandomColor(item), width: '10px', height: '10px', display: 'inline-block', marginRight: '5px' }}></div>
                                        <span style={{ color: (this.state.selected[item] || this.state.ALL ? 'black' : 'rgb(204, 204, 204)') }}> {item.toUpperCase()}</span>
                                    </div>
                                )
                            })}
                        </div>

                    </div>

                </div>
            </>
        );
    }

    getData() {

        if (!App.strategySelector || App.strategySelector.selected() == null) return;

        var resultModel = new Lab_results();
        var symbols = {};

        var maxOrder = {};

        resultModel.get([[[LAB_RESULT_STRATEGY, '=', App.strategySelector.selected()]]], { 'orderBy': LAB_RESULT_SELL_TIME, 'asc': false }).then(res => {
            if (res['data']) {
                res = res['data'];
                var data = [];

                var limitTime = Number(moment().startOf('day').format('x'));
                for (let i in res) {

                    // var start = Number(res[i][LAB_RESULT_CHART]);
                    // var stop = Number(res[i][LAB_RESULT_SELL_TIME]);
                    // if(!isset(maxOrder[start])) maxOrder[start] = 1;
                    // for(let j in maxOrder){
                    //     if(j > start && j < stop) maxOrder[j]++;
                    // }

                    if (res[i][LAB_RESULT_PENDING] == 1) continue;

                    var symbol = res[i][LAB_RESULT_SYMBOL];
                    symbols[symbol] = true;

                    if (!this.state.selected[symbol] && !this.state.ALL) continue;

                    var tempTime = Number(res[i][LAB_RESULT_SELL_TIME])
                    if (tempTime >= limitTime && isset(data[0])) {
                        // var xvalue = moment(limitTime, 'x').format("DD/MM/YYYY");
                        var xvalue = limitTime;
                        if (res[i][LAB_RESULT_PENDING] == 0 && res[i][LAB_RESULT_STATUS] != LAB_RESULT_STATUS_CANCLE) {
                            var yvalue = Number(res[i][LAB_RESULT_REAL_PROFIT]) + Number(data[0].y);
                            data[0].y = Number(yvalue.toFixed(2))
                        }
                    } else {
                        while (tempTime < limitTime) {
                            limitTime -= 86400 * 1000;
                        }

                        // var xvalue = moment(limitTime, 'x').format("DD/MM/YYYY");
                        var xvalue = limitTime;
                        if (res[i][LAB_RESULT_PENDING] == 0 && res[i][LAB_RESULT_STATUS] != LAB_RESULT_STATUS_CANCLE) {
                            var yvalue = Number(res[i][LAB_RESULT_REAL_PROFIT]);
                        } else {
                            var yvalue = 0;
                        }

                        data.unshift({
                            x: xvalue,
                            y: yvalue
                        })
                    }

                }

                // console.log(data);

                var coin = Object.keys(symbols);

                // var maxOrderData = [];
                // for(let j in maxOrder){
                //     maxOrderData.push({
                //         x: Number(j),
                //         y: maxOrder[j],
                //     })
                // }
                // maxOrderData = maxOrderData.sort((a,b)=>a.x - b.x)
                // console.log(maxOrderData);

                // var serial = [];
                // var categories = [];

                // data.map(item => {
                //     serial.push(Number(item.y.toFixed(3)));
                //     categories.push(item.x);
                // });

                // serial = serial.slice(-15);
                // categories = categories.slice(-15);
        
                this.setState({
                    coin: coin,
                    Options: {
                        series: [{
                            data: data,
                        },
                            // {
                            //     data: maxOrderData
                            // }
                        ],
                        // xAxis: {
                        //     categories
                        // }

                    }
                })
            }
        })


        // for (var i = 0; i <= 14; i++) {
        //     var temponary = moment().subtract(i, 'days').format("DD/MM/YYYY");
        //     categories.unshift(temponary);

        //     var totalProfit = 0;

        //     Object.values(App.lab[i]).map(data => {
        //         var index = this.state.selected.indexOf(data.lab_symbol);
        //         if (index > -1) {
        //             if (data[LAB_PENDING] == 0) {
        //                 totalProfit += Number(data[LAB_PROFIT]) - 0.08;
        //             }
        //         }

        //     })

        //     series.unshift(Number(totalProfit.toFixed(4)));

        // }






    }
}

export default ChartProfitPerDay;
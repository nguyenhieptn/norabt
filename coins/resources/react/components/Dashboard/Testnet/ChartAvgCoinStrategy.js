import React, { Component } from 'react';
import Highcharts from 'highcharts';
import HighchartsReact from 'highcharts-react-official'
import Watchlist from '../../../model/admin/Watchlist';
import Testnet_results from '../../../model/admin/Testnet_results';
import Strategies from '../../../model/admin/Strategies';

import Input from '../../input/Input';

class ChartAvgCoinStrategy extends Component {
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
                    // text: '<b>AVG COIN STRATEGY </b>',
                    text: '<b>Avg Order Time Per Coin </b>',
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
                            text: ''
                        },
                        lineWidth: 1,
                        opposite: true,
                    }
                ],
                chart: {
                    height: 600

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
                                var result = Number(this.y);
                                // result = Math.round(result / 1000);
                                var d = Math.floor(result / (3600 * 24));
                                var h = Math.floor(result % (3600 * 24) / 3600);
                                var m = Math.floor(result % 3600 / 60);

                                var dDisplay = d > 0 ? d + 'd' : "";
                                var hDisplay = h > 0 ? h + 'h' : "";
                                var mDisplay = m > 0 ? m + 'm' : 0;
                                var color = '';
                                if (h > 0 || d > 0) color = 'red'
                                var date = dDisplay + hDisplay + mDisplay;
                                return date
                                // return this.y + 'm';
                            }
                        },
                        maxPointWidth: 50
                    },
                    column: {
                        zones: [{
                            value: 100,
                            color: '#007bff'
                        }, {
                            color: 'red'
                        }]
                    }
                },

                legend: {
                    enabled: false,
                },

                series: [
                    {
                        name: 'Avg Time',
                        type: 'column',

                        data: [],
                    }

                ]
            }
        }
        this.updateChartWidth = this.updateChartWidth.bind(this);

        this.colors = {};

        this.Frame = [
            {
                text: '3d',
                type: 'day',
                count: 3,
            },
            {
                text: '1w',
                type: 'week',
                count: 1,
            },
            {
                text: '1m',
                type: 'month',
                count: 1,

            },
            {
                text: '3m',
                type: 'month',
                count: 3,
            },
            {
                text: '6m',
                type: 'month',
                count: 6,

            }, {
                text: '1y',
                type: 'year',
                count: 1,

            }, {
                type: 'all',
                text: 'All'
            },]

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
                chartOptions: {
                    ...this.setState.chartOptions,
                    chart: {
                        width: typeof (this.chartContainer) !== null && this.chartContainer.clientWidth,
                    }

                }
            })
        }, 500);
    }
    // getRandomColor(item) {
    //     if (isset(this.colors[item])) return this.colors[item];
    //     var letters = '0123456789ABCDEF';
    //     var color = '#';
    //     for (var i = 0; i < 6; i++) {
    //         color += letters[Math.floor(Math.random() * 16)];
    //     }
    //     this.colors[item] = color;
    //     return this.colors[item];
    // }

    render() {
        return (
            <>

                <div className='p-col-12 p-md-12 ' >

                    <div className='box_shadow ' ref={c => this.chartContainer = c} style={{ position: 'relative' }}>
                        <div style={{ display: 'flex', alignItems: 'center', padding: 7, position: 'absolute', zIndex: 1, top: '35px', left: '31px' }}>
                            {
                                this.Frame.map(item => (
                                    <div
                                        key={item.text}
                                        onClick={(e) => this.calDate(item)}
                                        style={this.state.frameSelect == item.text ?
                                            { width: '32px', height: '22px', textAlign: 'center', color: 'black', background: 'rgb(230, 235, 245)', marginRight: '10px', fontWeight: 'bold', cursor: 'pointer' } :
                                            { width: '32px', height: '22px', textAlign: 'center', color: 'black', background: '#f7f7f7', marginRight: '10px', cursor: 'pointer' }
                                        }
                                        className={`${item.text}-async`}
                                    >{item.text}</div>
                                ))
                            }

                        </div>

                        <div className='cus-hide' style={{ display: 'flex', alignItems: 'center', padding: 7, position: 'absolute', zIndex: 1, top: '35px', right: '31px' }}>

                            <Input ref={c => this.startInput = c} placeholder="Start Time" className='input' struct={{
                                [INPUT_TYPE]: 'date',
                                [INPUT_DEFAULT]: this.state.start != '' ? (this.state.start / 1000) : '',
                                [INPUT_ONCHANGE_BLUR]: (e, obj) => { this.setState({ start: obj.getValue() * 1000 }, () => this.getData(true)) }
                            }}></Input>

                            &nbsp;

                            <Input ref={c => this.stopInput = c} placeholder="Stop Time" className='input' struct={{
                                [INPUT_TYPE]: 'date',
                                [INPUT_DEFAULT]: this.state.stop != '' ? (this.state.stop / 1000) : '',
                                [INPUT_ONCHANGE_BLUR]: (e, obj) => {
                                    this.setState({ stop: obj.getValue() * 1000 }, () => {
                                        this.getData(true);
                                        // if (obj.getValue() == '') this.startUpdate();
                                    })
                                }
                            }}></Input>

                        </div>
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

    calDate(item) {
        if (this.state.frameSelect == item.text) return;

        $(`.${item.text}-async`).click();

        var startDate = moment().subtract(item.count, item.type).format('x');
        var stopDate = moment().format('x');
        if (item.text == "All") {
            this.startInput.setValue();
            this.stopInput.setValue(stopDate / 1000)
            this.setState({
                start: 0,
                stop: stopDate,
                frameSelect: item.text
            }, () => this.getData());

        } else {

            this.startInput.setValue(startDate / 1000);
            this.stopInput.setValue(stopDate / 1000)
            this.setState({
                start: startDate,
                stop: stopDate,
                frameSelect: item.text
            }, () => this.getData());

        }
    }

    getData() {

        var symbols = {};


        var resultModel = new Testnet_results();

        // resultModel.getByStrategy(App.strategySelector.selected()).then(res => {
        resultModel.getByAccountTestnet(App.accountSelectorTestnet.selected()).then(res => {
            if (res['data']) {
                res = res['data'];


                var data = {};
                var count = {};

                for (let i in res) {

                    if (res[i][TESTNET_RESULT_MATCHED_QTY] <= 0) continue;
                    var time = Number(res[i][TESTNET_RESULT_SELL_TIME]);
                    if (time > this.state.stop || time < this.state.start) continue;

                    var symbol = res[i][TESTNET_RESULT_SYMBOL];


                    var sell_time = moment(res[i][TESTNET_RESULT_SELL_TIME], 'x');
                    var enter_time = moment(res[i][TESTNET_RESULT_CHART], 'x');

                    // if (isNaN(sell_time) || isNaN(enter_time)) continue;
                    if (isNaN(sell_time) || isNaN(enter_time)) {
                        sell_time = moment(Number(moment().format('x')), 'x')
                    };
                    var diff = sell_time.diff(enter_time, 'seconds');

                    if (!isset(data[symbol])) {
                        data[symbol] = diff;
                        count[symbol] = 1;
                    } else {

                        data[symbol] += diff;
                        count[symbol] += 1;
                    }

                }

                var dataArray = [];
                for (let i in data) {
                    dataArray.push({ key: i, value: data[i] / count[i] });
                }

                dataArray = dataArray.sort((a, b) => a.value - b.value);


                var categories = [];
                var data = [];

                dataArray.map(item => {
                    categories.push(item.key);
                    data.push(Math.floor(item.value));
                })

                this.setState({
                    chartOptions: {
                        series: [
                            {
                                data: data,

                            }
                        ],
                        xAxis: {
                            categories: categories
                        }
                    },

                })

            }
        });






    }




}

export default ChartAvgCoinStrategy;
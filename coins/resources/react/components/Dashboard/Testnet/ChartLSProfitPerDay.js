import React, { Component } from 'react';
import Highcharts from 'highcharts';
import HighchartsReact from 'highcharts-react-official'
import Input from '../../input/Input';

import Testnet_results from '../../../model/admin/Testnet_results';
class ChartLSProfitPerDay extends Component {
    constructor(props) {
        super(props);
        this.state = {
            start: 0,
            stop: moment().format('x'),
            frameSelect: 'All',

            ALL: true,
            coin: [],
            selected: true,
            temponary: [],
            Options: {
                chart: {}

                ,
                title: {
                    // text: '<b> PER CRYPTO</b>',
                    text: '<b>Total Orders Per Coin</b>',
                    margin: 45
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
                        lineWidth: 1,
                        opposite : true,
                    }
                ],

                chart: {
                    height: 600

                },
                legend: {
                    enabled: true,

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

        this.updateChartWidth = this.updateChartWidth.bind(this);

    }
    componentDidMount() {


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
                        {/* <div style={{ display: 'flex', alignItems: 'center', position: 'absolute', top: 5, left: 5, zIndex: 100 }}>
                            <div className='button btn' style={{ border: 'solid thin darkgray', borderRadius: 5, padding: '2px 5px', fontWeight: 'bold', background: (this.state.selected ? '#28a745' : 'none') }} onClick={() => {
                                this.setState({ selected: !this.state.selected },
                                    () => this.dislegend()
                                );
                            }}>ALL</div>
                        </div> */}
                        <div  style={{ display: 'flex', alignItems: 'center', padding: 7, position: 'absolute', zIndex: 1, top: '35px', left: '31px' }}>
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

                        <div className='cus-hide' style={{ display: 'flex', alignItems: 'center', padding: 7, position: 'absolute', zIndex: 1, top: '35px', right: '40px' }}>

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
                            highcharts={Highcharts}
                            options={this.state.Options}
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

        var labModel = new Testnet_results();

        // labModel.getByStrategy(App.strategySelector.selected()).then(res => {
            labModel.getByAccountTestnet(App.accountSelectorTestnet.selected()).then(res => {
            res = res['data'];
            var coin = [];
            var total = [];
            var totalTakeProfit = [];
            var totalStopLoss = [];

            for (let i in res) {

                var time = Number(res[i][TESTNET_RESULT_SELL_TIME]);
                if (time > this.state.stop || time < this.state.start) continue;

                var index = coin.indexOf(res[i][TESTNET_RESULT_SYMBOL]);

                if (index >= 0) {
                    total[index]++;
                    if (res[i][TESTNET_RESULT_STATUS] == [TESTNET_RESULT_STATUS_TAKEPROFIT]) {
                        totalTakeProfit[index]++;

                    }
                    if (res[i][TESTNET_RESULT_STATUS] == [TESTNET_RESULT_STATUS_STOPLOSS]) {
                        totalStopLoss[index]++;
                    }

                } else {
                    coin.push(res[i][TESTNET_RESULT_SYMBOL]);
                    total.push(1);
                    if (res[i][TESTNET_RESULT_STATUS] == [TESTNET_RESULT_STATUS_TAKEPROFIT]) {
                        totalTakeProfit.push(1);

                    } else {
                        totalTakeProfit.push(0);
                    }
                    if (res[i][TESTNET_RESULT_STATUS] == [TESTNET_RESULT_STATUS_STOPLOSS]) {
                        totalStopLoss.push(1);

                    } else {
                        totalStopLoss.push(0);
                    }



                }

            }
            // Object.values(res.data).map(item => {



            //     var index = coin.indexOf(item[TESTNET_RESULT_SYMBOL]);

            //     if (index >= 0) {
            //         total[index]++;
            //         if (item[TESTNET_RESULT_STATUS] == [TESTNET_RESULT_STATUS_TAKEPROFIT]) {
            //             totalTakeProfit[index]++;

            //         }
            //         if (item[TESTNET_RESULT_STATUS] == [TESTNET_RESULT_STATUS_STOPLOSS]) {
            //             totalStopLoss[index]++;
            //         }

            //     } else {
            //         coin.push(item[TESTNET_RESULT_SYMBOL]);
            //         total.push(1);
            //         if (item[TESTNET_RESULT_STATUS] == [TESTNET_RESULT_STATUS_TAKEPROFIT]) {
            //             totalTakeProfit.push(1);

            //         } else {
            //             totalTakeProfit.push(0);
            //         }
            //         if (item[TESTNET_RESULT_STATUS] == [TESTNET_RESULT_STATUS_STOPLOSS]) {
            //             totalStopLoss.push(1);

            //         } else {
            //             totalStopLoss.push(0);
            //         }



            //     }


            // })







            var objectdata = [];
            coin.map((item, index) => {
                objectdata.push({
                    'symbol': item,
                    'total': total[index],
                    'takeProfit': totalTakeProfit[index],
                    'stopLoss': totalStopLoss[index],
                })
            })

            objectdata.sort(function (a, b) { return a.total - b.total });

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
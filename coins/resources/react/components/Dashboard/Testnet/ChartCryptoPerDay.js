import React, { Component } from 'react';
import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official'
import Input from '../../input/Input';
import Testnet_results from '../../../model/admin/Testnet_results';



class ChartCryptoPerDay extends Component {
    constructor(props) {
        super(props);
        this.state = {

            start: 0,
            stop: moment().format('x'),
            frameSelect: 'All',
            selected: true,
            seriestemponary: [],
            chartOptions: {
                chart: {

                },
                exporting: {
                    enabled: false
                },
                title: {
                    // text: '<b>CRYPTO PER DAY </b>',
                    text: '<b>Total Profit Per Coin </b>',
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
                            text: '<b></b>'
                        },
                        lineWidth: 1,
                        opposite : true,
                    }
                ],
                chart: {
                    // height: (8 / 16 * 80) + '%'
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
                            enabled: true
                        },
                        maxPointWidth: 50
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


                legend: {
                    enabled: false,
                },

                series: [
                    {
                        name: 'Profit',
                        type: 'column',

                        data: [],
                    }

                ]
            }
        }
        this.updateChartWidth = this.updateChartWidth.bind(this);
        this.startDate = 0;
        this.stopDate = moment().format('x');

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
        this.getData(0);

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
            if (!this.chartContainer) return;
            this.setState({
                chartOptions: {
                    ...this.setState.chartOptions,
                    chart: {
                        width: this.chartContainer ? this.chartContainer.clientWidth : 0,
                    }

                }
            })
        }, 500);
    }

    render() {
        return (
            <div style={{ width: '100%', padding: 10 }} >
                <div className='box_shadow ' ref={c => this.chartContainer = c} style={{ position: 'relative' }}>

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
                    {/* <div style={{ display: 'flex', alignItems: 'center', position: 'absolute', top: 7, left: 5, zIndex: 100 }}>
                        <div className='button btn' style={{ border: 'solid thin darkgray', borderRadius: 5, padding: '2px 5px', fontWeight: 'bold', background: (this.state.selected ? '#28a745' : 'none') }} onClick={() => {
                            this.startDate = 0;
                            this.stopDate = moment().format('x');
                            this.getData();
                        }}>ALL</div>


                    </div> */}
                    {/* 
                    <div style={{ display: 'flex', position: 'absolute', top: 15, right: 20, zIndex: 100 }}>

                        <div style={{ width: '30%', marginRight: '10px' }}>
                            <Input placeholder="Select Date" ref={c => this.day = c} className='input' struct={{
                                [INPUT_TYPE]: 'date',
                                [INPUT_NULL]: true,
                                [INPUT_FORMAT]: 'DD/MM/YYY',
                                [INPUT_ONBLUR]: (e, obj) => {
                                    var val = obj.input.getValue();
                                    this.startDate = moment(val, 'X').startOf("day").format('x');
                                    this.stopDate = moment(val, 'X').endOf("day").format('x');
                                    this.inputFromDate.setValue(this.startDate / 1000);
                                    this.inputEndDate.setValue(this.stopDate / 1000);
                                    this.getData();
                                }
                            }}></Input>
                        </div>

                        <div style={{ width: '30%', marginRight: '10px' }}>
                            <Input placeholder="From" ref={c => this.inputFromDate = c} className='input' struct={{
                                [INPUT_TYPE]: 'date',
                                [INPUT_NULL]: true,
                                [INPUT_ONBLUR]: (e, obj) => {
                                    var val = obj.input.getValue();
                                    this.startDate = moment(val, 'X').format('x');
                                    this.getData();
                                }
                            }}></Input>
                        </div>

                        <div style={{ width: '30%', marginRight: '10px' }}>
                            <Input placeholder="To" ref={c => this.inputEndDate = c} className='input' struct={{
                                [INPUT_TYPE]: 'date',
                                [INPUT_NULL]: true,
                                [INPUT_ONBLUR]: (e, obj) => {
                                    var val = obj.input.getValue();
                                    this.stopDate = moment(val, 'X').format('x');
                                    this.getData();
                                }
                            }}></Input>
                        </div>

                    </div> */}
                    <HighchartsReact
                        highcharts={Highcharts}
                        options={this.state.chartOptions}
                    />
                </div>

            </div>
        );
    }
    // dislegend() {
    //     if (this.state.selected) {
    //         this.state.seriestemponary.map(item => {
    //             item.visible = true
    //         })
    //     } else {
    //         this.state.seriestemponary.map(item => {
    //             item.visible = false
    //         })
    //     }

    //     this.setState({
    //         chartOptions: {
    //             series: this.state.seriestemponary
    //         }
    //     })
    // }
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

                for (let i in res) {

                    if (res[i][TESTNET_RESULT_PENDING] == 1) continue;

                    var symbol = res[i][TESTNET_RESULT_SYMBOL];

                    var time = Number(res[i][TESTNET_RESULT_SELL_TIME]);

                    // if (time > this.stopDate || time < this.startDate) continue;

                    if (time > this.state.stop || time < this.state.start) continue;

                    if (res[i][TESTNET_RESULT_PENDING] == 0 && res[i][TESTNET_RESULT_STATUS] != TESTNET_RESULT_STATUS_CANCLE) {
                        if (!isset(data[symbol])) {
                            // data[symbol] = Number(res[i][TESTNET_RESULT_REAL_PROFIT]);
                            data[symbol] = Number(res[i][TESTNET_RESULT_REAL_PNL]);
                        } else {
                            // data[symbol] += Number(res[i][TESTNET_RESULT_REAL_PROFIT]);
                            data[symbol] += Number(res[i][TESTNET_RESULT_REAL_PNL]);
                        }

                    }

                }

                var dataArray = [];
                for (let i in data) {
                    dataArray.push({ key: i, value: data[i] });
                }

                dataArray = dataArray.sort((a, b) => a.value - b.value);


                var categories = [];
                var data = [];

                dataArray.map(item => {
                    categories.push(item.key);
                    data.push(Number(item.value.toFixed(3)));
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

export default ChartCryptoPerDay;
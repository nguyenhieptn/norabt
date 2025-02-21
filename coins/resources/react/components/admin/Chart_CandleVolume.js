import React, { Component } from 'react';

import Input from '../input/Input'

import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official'


import Top_sum from '../../model/admin/Top_Sum';
import Watchlist from '../../model/admin/Watchlist'

class Chart_CandleVolume extends Component {

    constructor(props) {
        super(props);
        this.state = {

            khung: '1w',
            symbolOptions: {},
            symbol: 'BTCUSDT',


            dislabel: false,

            Options: {
                exporting: {
                    enabled: false
                },
                title: {
                    text: '<b> Candle Volume </b>',
                    margin : 35
                },
                credits: {
                    enabled: false
                },
                scrollbar: {
                    enabled: false
                },

                xAxis: {

                },
                yAxis: [
                    {

                        labels: {
                            align: 'left'
                        },

                        height: '70%',
                        lineWidth: 1,
                        resize: {
                            enabled: true
                        },
                        gridLineColor: '#ededed',
                    },
                    {
                        labels: {
                            align: 'left'
                        },
                        top: '72%',
                        height: '28%',
                        offset: 0,
                        lineWidth: 1
            
                    },

                ],

                chart: {
                    height: 800,

                },
                legend: {
                    enabled: true,

                },
                navigator: {
                    enabled: true
                },
                // scrollbar: {
                //     enabled: true
                // },
                plotOptions: {
                    candlestick: {
                        color: '#ffcdd2',
                        lineColor: '#ff5252',
                        upColor: '#b2dfdb',
                        upLineColor: '#26a69a',

                    },
                    series: {
                        dataLabels: {
                            enabled: false,
                            formatter: function () {

                                return formatNumber(this.y);
                            }
                        },
                        maxPointWidth: 100
                    },
                },
                tooltip: {
                    padding: 1,
                    style: {
                        fontSize: '10px',
                    }

                },

                rangeSelector: {

                    buttonPosition: {
                        align: 'left',
                        // x: '0',
                        y: '-1',
                    },

                    // selected: 0,

                    allButtonsEnabled: true,
                    buttons:
                        [

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
                            },
                        ],
                    inputEnabled: false,

                    buttonSpacing: 10,
                },

                series: [{
                    type: 'candlestick',
                    name: 'Candle',
                    data: [],
                    id: 'aapl',
                   
                }, {
                    type: 'column',
                    name: 'Volume',
                    data: [],
                    yAxis: 1,
            
                }]
            }
        }
        this.updateChartWidth = this.updateChartWidth.bind(this);

        this.khung = ['1w', '1M'];

    }

    getSymbol() {

        var wlModel = new Watchlist();
        wlModel.read(null, false).then((res) => {
            if (res['data']) {
                var response = res['data'];
                var symbolOptions = {};

                response.map(item => {
                    symbolOptions[item[WL_SYMBOL]] = item[WL_SYMBOL];
                });

                this.setState({ symbolOptions }, () => this.getData())

            }
        })
    }

    componentDidMount() {
        this.updateChartWidth();
        this.resize_ob = new ResizeObserver((entries) => {
            this.updateChartWidth()
        });
        this.resize_ob.observe(this.chartContainer);


        this.getSymbol();





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

    setRangeSelector() {

        // console.log('Set rangselector to 4')

        this.setState({
            Options: { rangeSelector: { selected: 2 } },
        })

    }





    render() {
        // console.log(App.accountSelectorTestnet.())
        return (
            <>

                <div className='box_shadow ' ref={c => this.chartContainer = c} style={{ position: 'relative', marginTop: 15, padding: 5 }}>
                    <div style={{ display: 'flex', alignItems: 'center', padding: 7, position: 'absolute', zIndex: 1, top: '25px', left: '40px' }}>

                        <div className='button btn' style={{  borderRadius: 0, padding: '2px 5px', fontWeight: (this.state.dislabel == false ? 'bold' : '100'), background: (this.state.dislabel == false ? 'rgb(230, 235, 245)' : '#f7f7f7') }} onClick={() => {
                            this.setState({
                                dislabel: !this.state.dislabel,
                                Options: {
                                    plotOptions: {
                                        candlestick: {
                                            color: '#ffcdd2',
                                            lineColor: '#ff5252',
                                            upColor: '#b2dfdb',
                                            upLineColor: '#26a69a',

                                        },
                                        series: {
                                            dataLabels: {
                                                enabled: !this.state.dislabel,
                                                formatter: function () {

                                                    return formatNumber(this.y);
                                                }
                                            },
                                            maxPointWidth: 100
                                        },
                                    },


                                }
                            });

                        }}>Label</div>

                        {this.khung.map(item => {
                            return <div key={item} className='button btn'                         style={{  borderRadius: 0, padding: '2px 5px', fontWeight: (this.state.khung == item ? 'bold' : '100'), background: (this.state.khung == item ? 'rgb(230, 235, 245)' : '#f7f7f7') }} onClick={() => {
                                this.setState({ khung: item }, () => this.getData());
                            }}>{item.toUpperCase()}</div>
                        })}

                        &nbsp;
                        <Input ref={c => this.symbolInput = c} placeholder="Symbol" className='input' struct={{
                            [INPUT_TYPE]: 'select',
                            [INPUT_DEFAULT]: this.state.symbol,
                            [INPUT_ONCHANGE]: (e, obj) => {
                                var id = obj.getValue();
                                this.setState({
                                    symbol: id,
                                }, () => this.getData(0))
                            },
                            [INPUT_OPTION]: this.state.symbolOptions
                        }}></Input>

                    </div>


                    <HighchartsReact
                        highcharts={Highcharts}
                        options={this.state.Options}
                        constructorType={'stockChart'}
                        ref={c => this.chart = c}

                    />

                </div>




            </>

        );
    }

    getData(loading = true, limit = 1000, reset = true) {


        var symbol = this.state.symbol;
        var frame = this.state.khung;

        // var startDate = Number(this.startDate.getValue());
        // var endDate = Number(this.endDate.getValue());

        if (!symbol) return Promise.reject(false);
        if (loading) App.loading(true)

        var url = '/admin/testnetchart/getCandleData1w1M';
        return axios.request({
            url: url,
            method: 'POST',
            data: {
                symbol: symbol,
                interval: frame,
            }
        })

            .then(response => {
                if (loading) App.loading(false);


                response = response['data'];



                if (response['result']) {
                    if (!this.chart) return;
                    var ohlc = [];
                    var volumn = [];

                    response['data'].map(item => {

                        ohlc.unshift([
                            Number(item[`candlestick_${frame}_open_time`]), // the date
                            Number(item[`candlestick_${frame}_open`]), // open
                            Number(item[`candlestick_${frame}_high`]), // high
                            Number(item[`candlestick_${frame}_low`]), // low
                            Number(item[`candlestick_${frame}_close`]) // close
                        ]);

                        volumn.unshift({
                            x: Number(item[`candlestick_${frame}_open_time`]),
                            y: Number(item[`candlestick_${frame}_volume`]),
                            color :  Number(item[`candlestick_${frame}_close`]) -  Number(item[`candlestick_${frame}_open`]) > 0 ? 'rgb(178, 223, 219)' : 'rgb(255, 205, 210)'
                        });
                    })

                    this.setState({
                        Options: {
                            series: [
                               
                                {
                                    name: this.state.symbol + ' ' + this.state.khung,
                                    data: ohlc,
                                    id: 'aapl'
                                },
                                {
                                    data: volumn,
                                },
                            ],


                        }
                    })



                } else {
                    error_handle(response);
                }


            })

            .catch((error) => {
                if (loading) App.loading(false);
                error_handle(error)
                return false;
            })
    }







}

export default Chart_CandleVolume;
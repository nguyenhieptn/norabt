import React, { Component } from 'react';

import Input from '../input/Input'

import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official'


import Top_sum from '../../model/admin/Top_Sum';
import Watchlist from '../../model/admin/Watchlist'

class Chart_BTC extends Component {

    constructor(props) {
        super(props);
        this.state = {

            khung: '1d',
            symbolOptions: {},
            symbol: 'BTCUSDT',

            conditionBTC: [],
            dataConditionBTC: {},
            datatotalBTC: '',

            dislabel : false,

            Options: {
                exporting: {
                    enabled: false
                },
                title: {
                    text: '<b>BTC Wallet</b>',
                   
                    margin : 35
                
                },
                credits: {
                    enabled: false
                },
                scrollbar: {
                    enabled: false
                },

                xAxis: {
                    lineWidth: 1,
                },
                yAxis: [
                    {
                        startOnTick: true,
                        // title: {
                        //     text: '<b></b>',
                        // },
                        // height: '60%',
                        height: '70%',
                        lineWidth: 1,
                        gridLineWidth: 1,
                        gridLineColor: '#ededed',
                        labels: {
                            align: 'left'
                        },

                    

                    
                        
                    },
                    {
                        startOnTick: true,
                        // title: {

                        //     text: '<b></b>',
                        // },
                        lineWidth: 1,
                        gridLineWidth: 1,
                        gridLineColor: '#ededed',
                        opposite: false,
                        // height: '60%',
                        height: '70%',
                     
                    },

                    {
                        labels: {
                            align: 'left'
                        },
                        lineWidth: 1,
                        gridLineWidth: 1,
                        gridLineColor: '#ededed',
                        // top: '65%',
                        // height: '35%',
                        top: '72%',
                        height: '28%',
                        offset: 0,

                 
                       
                       
            
                    },

                ],

                chart: {
                    height:800,

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
                series: [
                    {

                        type: 'line',
                        name: 'BTC',
                        data: [],
                        color: 'dodgerblue'

                    },

                    {
                        type: 'candlestick',
                        name: 'Candle',
                        id: 'aapl',
                        data: [],
                        yAxis: 1,
                    },

                    {
                        type: 'column',
                        name: 'Volume',
                        data: [],
                        yAxis: 2,
                
                    }

                ]
            }
        }
        this.updateChartWidth = this.updateChartWidth.bind(this);

        this.khung = [ '4h', '1d'];

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

    OnRun() {
        var conditionBTC = this.state.conditionBTC;
        var data = this.state.dataConditionBTC;
        var temp = [];

        var datatotalBTC1 = 0;

        conditionBTC.map(item => {
            var BTCstartData = data[item.startDate];
            var BTCendData = data[item.endDate];
            var btc = (BTCendData - BTCstartData).toFixed(2);
            datatotalBTC1 += Number(btc);
            temp.push({
                startDate: Number(item.startDate),
                endDate: Number(item.endDate),
                totalBTC: formatNumber(btc)
            })
        })




        this.setState({
            datatotalBTC: 'ok',
            conditionBTC: temp
        });
    }


    render() {
        // console.log(App.accountSelectorTestnet.())
        return (
            <>
        
                    <div className='box_shadow mt-2 ' ref={c => this.chartContainer = c} style={{ position: 'relative' }}>
                        <div style={{ display: 'flex', alignItems: 'center', padding: 7, position: 'absolute', zIndex: 1, top: '22px', left: '73px' }}>
                           
                            <div  className='button btn' style={{  borderRadius: 0, padding: '2px 5px', fontWeight: (this.state.dislabel == false ? 'bold' : '100'), background: (this.state.dislabel == false ? 'rgb(230, 235, 245)' : '#f7f7f7') }} onClick={() => {
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
                                return <div key={item} className='button btn'  style={{  borderRadius: 0, padding: '2px 5px', fontWeight: (this.state.khung == item ? 'bold' : '100'), background: (this.state.khung == item ? 'rgb(230, 235, 245)' : '#f7f7f7') }} onClick={() => {
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

                        <div className='cus-hide' style={{ display: 'flex', alignItems: 'center', padding: 7, position: 'absolute', zIndex: 1, top: '55px', right: '61px' }}>


                            <Input className='input' placeholder='Start Time' ref={c => this.startDate = c} struct={{
                                [INPUT_TYPE]: 'date',
                                [INPUT_FORMAT]: 'DD/MM/YYYY',
                                [INPUT_DEFAULT]: moment(1577923200000, 'x').format('DD/MM/YYYY'),
                                [INPUT_DECORATOR_IN]: data => data,
                                [INPUT_DECORATOR_OUT]: (data) => moment.utc(data, 'DD/MM/YYYY').format('x'),
                                [INPUT_ONCHANGE_BLUR]: () => { this.getData() }
                            }}></Input>&nbsp;
                            <Input className='input' placeholder='Stop Time' ref={c => this.endDate = c} struct={{
                                [INPUT_TYPE]: 'date',
                                [INPUT_FORMAT]: 'DD/MM/YYYY',
                                [INPUT_DEFAULT]: moment().format('DD/MM/YYYY'),
                                [INPUT_DECORATOR_IN]: data => data,
                                [INPUT_DECORATOR_OUT]: (data) => moment.utc(data, 'DD/MM/YYYY').format('x'),
                                [INPUT_ONCHANGE_BLUR]: () => { this.getData() }
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

    getAllData(loading = true, limit = 1000, reset = true) {


        var symbol = this.state.symbol;
        var frame = this.state.khung;

        var startDate = Number(this.startDate.getValue());
        var endDate = Number(this.endDate.getValue());

        if (!symbol) return Promise.reject(false);
        if (loading) App.loading(true)

        var url = '/admin/testnetchart/getCandleData';
        return axios.request({
            url: url,
            method: 'POST',
            data: {
                symbol: symbol,
                interval: frame,
                limit: limit,
                account: 1,
            }
        })

            .then(response => {
                if (loading) App.loading(false);
                response = response['data'];

                if (response['result']) {
                    if (!this.chart) return;
                    var ohlc = [];
                    var allData = response['data'];
                    var data = allData['data'];

                    var dataLength = data.length;


                    var volumn = [];

                    var lastTime = 0;
                    if (ohlc.length > 0) lastTime = ohlc[ohlc.length - 1][0];

                    for (var i = 0; i < dataLength; i += 1) {
                        if (data[i]['open_time'] <= lastTime) continue;
                        var item = data[i];

                        if (data[i]['open_time'] >= startDate && data[i]['open_time'] <= endDate) {
                            ohlc.push([
                                Number(data[i]['open_time']), // the date
                                Number(data[i]['open']), // open
                                Number(data[i]['high']), // high
                                Number(data[i]['low']), // low
                                Number(data[i]['close']) // close
                            ]);

                            volumn.push({
                                x: Number(data[i]['open_time']),
                                // y: Number(data[i]['volume']),
                                y: Math.round(Number(data[i]['volume'])*1000)/1000 ,
                                color :  Number(data[i]['close']) -   Number(data[i]['open']) > 0 ? 'rgb(178, 223, 219)' : 'rgb(255, 205, 210)'
                            });
                        }


                    }

                     return {
                        ohlc,
                        volumn
                    }


                } else {
                    error_handle(response);
                }

                // return response;
            })

            .catch((error) => {
                if (loading) App.loading(false);
                error_handle(error)
                return false;
            })
    }

    async getData() {
        var startDate = Number(this.startDate.getValue());
        var endDate = Number(this.endDate.getValue());
        var TopSumModel = new Top_sum();
        var length = Object.keys(this.state.dataConditionBTC).length;

        var topsumdata = await TopSumModel.get([], { 'orderBy': TOP_SUM_TIME, 'asc': true });

        var data = [];
        var dataConditionBTC = {};
        if (topsumdata['data']) {
            topsumdata = topsumdata['data'];


            topsumdata.map(item => {
                var time = Number(item[TOP_SUM_TIME]) - 86399999 - 86400000;

                if (time >= startDate && time <= endDate) {
                    data.push({
                        x: time,
                        y: Number(item[TOP_SUM_BALANCE].toFixed(2))
                    });

                    if (length == 0) {
                        dataConditionBTC[time] = Number(item[TOP_SUM_BALANCE].toFixed(2));
                    }

                }

            })
        }

        // var ohlc = await this.getAllData();

        var dataAll = await this.getAllData();

        var ohlc = dataAll['ohlc'];
        var volume1 = dataAll['volumn'];
        // console.log(stick);

        if (length == 0) {
            this.setState({
                dataConditionBTC,
                Options: {
                    series: [
                        {
                            data: data,
                        },
                        {
                            name: this.state.symbol + ' ' + this.state.khung,
                            data: ohlc,
                            id: 'aapl'
                        },
                        {
                            data: volume1,
                        },
                    ],


                }
            })
        } else {
            this.setState({
                Options: {
                    series: [
                        {
                            data: data,
                        },
                        {
                            name: this.state.symbol + ' ' + this.state.khung,
                            data: ohlc,
                            id: 'aapl'
                        },
                        {
                            data: volume1,
                        },
                    ],


                }
            })
        }

        this.setRangeSelector()


    }
}

export default Chart_BTC;
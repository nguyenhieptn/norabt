import React, { Component } from 'react';
import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official'

import Testnet_results from '../../../model/admin/Testnet_results';

import Input from '../../input/Input';

class ChartPNLDaily extends Component {

    constructor(props) {
        super(props);
        this.state = {
            start: '',
            stop: '',
            coin: [],
            selected: {},
            Options: {
                chart: {}

                ,
                exporting: {
                    enabled: false
                },
                title: {
                    text: '<b>Daily PNL</b>',
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
                        startOnTick: true,
                        title: {
                            text: '<b></b>',
                        },

                        startOnTick: false,

                        labels: {
                            align: 'left'
                        },
                        lineWidth: 1,
                    }
                ],

                chart: {
                     height: 600,
                 

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
                    series: {
                        dataLabels: {
                            enabled: true,
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

                    allButtonsEnabled: true,
                    buttons:
                        [
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
                            },
                        ],
                    inputEnabled: false,
                    // selected: 0,
                    buttonSpacing: 10,
                },
                series: [
                    {
                        type: 'column',
                        name: '$',
                        data: [],
                        color: 'dodgerblue' 

                    },

                ]
            }
        }
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
                   
                            <div className='cus-hide' style={{ display: 'flex', alignItems: 'center', padding: 7 , position : 'absolute' , zIndex : 1, top : '35px' , right : '47px' }}>

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
                            constructorType={'stockChart'}
                        />
                    

                    </div>

                </div>
            </>
        );
    }

    getData() {


        var resultModel = new Testnet_results();
        
        // resultModel.get([[[TESTNET_RESULT_STRATEGY, '=', App.strategySelector.selected()]]], { 'orderBy': TESTNET_RESULT_SELL_TIME, 'asc': false }).then(res => {
            resultModel.getByAccountTestnet( App.accountSelectorTestnet.selected()).then(res => {
            if (res['data']) {
                res = res['data'];
       
                var data = [];

                // var limitTime = Number(moment().startOf('day').format('x'));
                var limitTime = this.state.stop == '' ? Number(moment().startOf('day').format('x')) : this.state.stop;
                for (let i in res) {


                    if (res[i][TESTNET_RESULT_PENDING] == 1) continue;

                    var tempTime = Number(res[i][TESTNET_RESULT_SELL_TIME])

                    if (this.state.start !== '') {
                        if (tempTime < this.state.start) continue;
                    }
                    
                    if (tempTime >= limitTime && isset(data[0])) {
                        // var xvalue = moment(limitTime, 'x').format("DD/MM/YYYY");
                        var xvalue = limitTime;
                        if (res[i][TESTNET_RESULT_PENDING] == 0 && res[i][TESTNET_RESULT_STATUS] != TESTNET_RESULT_STATUS_CANCLE) {
                            var yvalue = Number(res[i][TESTNET_RESULT_REAL_PNL]) + Number(data[0].y);
                            data[0].y = Number(yvalue.toFixed(2))
                        }
                    } else {
                        while (tempTime < limitTime) {
                            limitTime -= 86400 * 1000;
                        }

                        // var xvalue = moment(limitTime, 'x').format("DD/MM/YYYY");
                        var xvalue = limitTime;
                        if (res[i][TESTNET_RESULT_PENDING] == 0 && res[i][TESTNET_RESULT_STATUS] != TESTNET_RESULT_STATUS_CANCLE) {
                            var yvalue = Number(res[i][TESTNET_RESULT_REAL_PNL].toFixed(2));
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
   

                this.setState({
                    Options: {
                        series: [{
                            data: data,
                        },
                            
                        ],
                       

                    }
                })
            }
           
        })


    }
}

export default ChartPNLDaily;
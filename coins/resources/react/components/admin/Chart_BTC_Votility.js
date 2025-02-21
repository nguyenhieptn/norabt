import React, { Component } from 'react';

import Input from '../input/Input'

import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official'


import Top_sum from '../../model/admin/Top_Sum';
import Watchlist from '../../model/admin/Watchlist'

class Chart_BTC_Votility extends Component {

    constructor(props) {
        super(props);
        this.state = {

            khung: '1d',
            symbolOptions: {},
            symbol: 'BTCUSDT',

            conditionBTC: [],
            dataConditionBTC: {},
            datatotalBTC: '',

            dislabel: false,
            dateSeleted : 'day',
            Options: {
                exporting: {
                    enabled: false
                },
                title: {
                    text: '<b>BTC Wallet Volatility</b>',

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

                        lineWidth: 1,
                        gridLineWidth: 1,
                        gridLineColor: '#ededed',
                        labels: {
                            align: 'left'
                        },





                    }




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


                    series: {
                        dataLabels: {
                            enabled: false,
                            formatter: function () {

                                return formatNumber(this.y);
                            }
                        },
                        maxPointWidth: 100
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

                    // selected: 4,

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

                        type: 'column',
                        name: 'BTC Volatility',
                        data: [],
                        color: 'dodgerblue'

                    }



                ]
            }
        }
        this.updateChartWidth = this.updateChartWidth.bind(this);

        this.khung = ['4h', '1d'];

    }



    componentDidMount() {
        this.updateChartWidth();
        this.resize_ob = new ResizeObserver((entries) => {
            this.updateChartWidth()
        });
        this.resize_ob.observe(this.chartContainer);


        this.getData('week');





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
            Options: { rangeSelector: { selected: 4 } },
        })

    }



    render() {
        return (
            <>

                <div className='box_shadow mt-2 ' ref={c => this.chartContainer = c} style={{ position: 'relative' }}>
                    <div style={{ display: 'flex', alignItems: 'center', padding: 7, position: 'absolute', zIndex: 1, top: '0px', left: '36px' }}>

                        <div className='button btn' style={{ borderRadius: 0, padding: '2px 5px', fontWeight: (this.state.dislabel == false ? 'bold' : '100'), background: (this.state.dislabel == false ? 'rgb(230, 235, 245)' : '#f7f7f7') }} onClick={() => {
                            this.setState({
                                dislabel: !this.state.dislabel,
                                Options: {
                                    plotOptions: {
                                        series: {
                                            dataLabels: {
                                                enabled: !this.state.dislabel,
                                                formatter: function () {
                                                    this.y = Math.round((this.y) * 1000) / 1000
                                                    return formatNumber(this.y);
                                                }
                                            },
                                            maxPointWidth: 100
                                        },
                                    },


                                }
                            });

                        }}>Label</div>


                    </div>

                    <div className='cus-hide' style={{ display: 'flex', alignItems: 'center', padding: 7, position: 'absolute', zIndex: 1, top: '35px', right: '61px' }}>


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
                        &nbsp;
                        <div>
                            <select className='input' defaultValue={'week'} onChange={(e) => { this.getData(e.target.value); this.setState({ dateSeleted: e.target.value }); }}>
                                <option value="day" >Day</option>
                                <option value="week" >Week</option>
                                <option value="month">Month</option>

                            </select>
                        </div>

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


    async getData(option) {
        var startDate = Number(this.startDate.getValue());
        var endDate = Number(this.endDate.getValue());
        var TopSumModel = new Top_sum();

        var topsumdata = await TopSumModel.get([], { 'orderBy': TOP_SUM_TIME, 'asc': true });

        var data = [];
        if (topsumdata['data']) {
            topsumdata = topsumdata['data'];


            if(option == 'day'){
                for (let index = 0; index < topsumdata.length - 1; index++) {
                    var time = Number(topsumdata[index][TOP_SUM_TIME]) - 86399999;
    
                    var volity = Math.round((Number(topsumdata[index + 1][TOP_SUM_BALANCE]) - Number(topsumdata[index][TOP_SUM_BALANCE])) * 1000) / 1000;
                    if (time >= startDate && time <= endDate) {
                        data.push({
                            x: time,
                            y: volity,
                        });
    
    
                    }
    
    
                }
    
            }else if(option == 'week'){
                var formatData = topsumdata.filter(item => new Date(item[TOP_SUM_TIME]).getDay() == 2 )

                for (let index = 0; index < formatData.length - 1; index++) {
                    var time = Number(formatData[index][TOP_SUM_TIME]) - 86399999;
    
                    var volity = Math.round((Number(formatData[index + 1][TOP_SUM_BALANCE]) - Number(formatData[index][TOP_SUM_BALANCE])) * 1000) / 1000;
                    if (time >= startDate && time <= endDate) {
                        data.push({
                            x: time,
                            y: volity,
                        });
    
    
                    }
    
    
                }
                if(new Date(topsumdata[topsumdata.length - 1][TOP_SUM_TIME]).getDay() !== 2){
                    data.push({
                        x: formatData[formatData.length - 1][TOP_SUM_TIME] - 86399999,
                        y: topsumdata[topsumdata.length - 1][TOP_SUM_BALANCE] - formatData[formatData.length -1][TOP_SUM_BALANCE],
                    });
                }

             

              
            }else{
                var formatData = topsumdata.filter(item => new Date(item[TOP_SUM_TIME]).getDate() == 2 )

                for (let index = 0; index < formatData.length - 1; index++) {
                    var time = Number(formatData[index][TOP_SUM_TIME]) - 86399999;
    
                    var volity = Math.round((Number(formatData[index + 1][TOP_SUM_BALANCE]) - Number(formatData[index][TOP_SUM_BALANCE])) * 1000) / 1000;
                    if (time >= startDate && time <= endDate) {
                        data.push({
                            x: time,
                            y: volity,
                        });
    
    
                    }
    
    
                }
                if(new Date(topsumdata[topsumdata.length - 1][TOP_SUM_TIME]).getDate() !== 2){
                    data.push({
                        x: formatData[formatData.length - 1][TOP_SUM_TIME] - 86399999,
                        y: topsumdata[topsumdata.length - 1][TOP_SUM_BALANCE] - formatData[formatData.length -1][TOP_SUM_BALANCE],
                    });
                } 
            }
           
        }

       


        this.setState({
            Options: {
                series: [
                    {
                        data: data,
                    }

                ],


            }
        })


        this.setRangeSelector()


    }
}

export default Chart_BTC_Votility;
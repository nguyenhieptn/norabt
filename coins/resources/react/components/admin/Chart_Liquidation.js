import React, { Component } from 'react';

import Input from '../input/Input'

import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official'


import Liquidation from '../../model/admin/Liquidation';


class Chart_Liquidation extends Component {

    constructor(props) {
        super(props);
        this.state = {


            dislabel : false,
            Options: {
                exporting: {
                    enabled: false
                },
                title: {
                    text: '<b>Liquidations</b>',
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
                        // title: {
                        //     text: '<b></b>',
                        // },

                        startOnTick: true,
                        labels: {
                            align: 'left'
                        },
                        lineWidth: 1,
                    },

                    {
                        // title: {
                        //     text: '<b></b>',
                        // },
                        // labels: {
                        //     align: 'left'
                        // },
                        opposite: false,
                        startOnTick: true,
                        lineWidth: 1,
                        gridLineColor: '#ededed',

                    },

                ],

                chart: {
                    height: 700,

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
                        type: 'column',
                        name: 'Shorts',
                        data: [],
                        color: '#e0294a'

                    },

                    {
                        type: 'column',
                        name: 'Longs',
                        data: [],
                        color: '#2ebd85'

                    },
                    {

                        type: 'line',
                        name: 'BTC Price',
                        data: [],
                        color: '#f5cf59',
                        yAxis: 1,

                    }


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


        this.getData();





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
        // console.log(App.accountSelectorTestnet.())
        return (
            <>

                <div className='box_shadow mt-2 ' ref={c => this.chartContainer = c} style={{ position: 'relative' }}>
                <div style={{ display: 'flex', alignItems: 'center', padding: 7, position: 'absolute', zIndex: 1, top: '0px', left: '73px' }}>
                           
                           <div  className='button btn' style={{  borderRadius: 0, padding: '2px 5px', fontWeight: (this.state.dislabel == false ? 'bold' : '100'), background: (this.state.dislabel == false ? 'rgb(230, 235, 245)' : '#f7f7f7') }} onClick={() => {
                               this.setState({ 
                                   dislabel: !this.state.dislabel,
                                   Options: {
                                       plotOptions: {
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


    async getData() {

        var LiquidationModel = new Liquidation();

        var liquidata = await LiquidationModel.read({}, true, { orderBy: LIQUIDATION_TIME, sort: 'asc', });



        var dataShorts = [];
        var dataLongs = [];
        var dataPrice = [];
        if (liquidata['data']) {
            liquidata = liquidata['data'];



            liquidata.map(item => {
                var time = Number(item[LIQUIDATION_TIME]);


                dataShorts.push({
                    x: time,
                    y: Number(item[LIQUIDATION_BUYVOLUSD].toFixed(2))
                });
                dataLongs.push({
                    x: time,
                    y: Number(item[LIQUIDATION_SELLVOLUSD].toFixed(2))
                });
                dataPrice.push({
                    x: time,
                    y: Number(item[LIQUIDATION_PRICE].toFixed(2))
                });
            })
        }

        this.setState({
            Options: {
                series: [
                    {
                        data: dataShorts,
                    },
                    {
                        data: dataLongs,
                    },
                    {
                        data: dataPrice,
                    },
                ],


            }
        })



    }
}

export default Chart_Liquidation;
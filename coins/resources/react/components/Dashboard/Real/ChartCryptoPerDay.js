import React, { Component } from 'react';
// import Highcharts from 'highcharts';
import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official'

import Testnet_results from '../../../model/admin/Testnet_results';
import Input from '../../input/Input';
import Actions from '../../../model/admin/Actions';


class ChartCryptoPerDay extends Component {
    constructor(props) {
        super(props);
        this.state = {
            frameSelect : 'All',
            start: 0,
            stop: moment().format('x'),
            selected: true,
            seriestemponary: [],
            chartOptions: {
                chart: {

                },
                exporting: {
                    enabled: false
                },
                title: {
                    text: '<b>PROFIT PER COIN (USDT) </b>',
                    align: 'center',
                    margin: 50,

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
                        opposite : true,
                        lineWidth : 1
                    }
                ],
                chart: {
                    // height: (8 / 16 * 80) + '%',
                    height: 500,

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
                        name: 'Profit'
                    }
                ]
            }
        }
        this.updateChartWidth = this.updateChartWidth.bind(this);

        this.startDate = 0;
        this.stopDate = moment().format('x');
        this.Frame = [ {
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

        // }
        calDate(item){
            if(this.state.frameSelect == item.text) return;
        
            var startDate = moment().subtract(item.count, item.type).format('x');
            var stopDate =  moment().format('x') ;
            if(item.text == "All"){
                this.startInput.setValue();
                this.stopInput.setValue(stopDate/1000)
                this.setState({
                    start : 0,
                    stop: stopDate,
                    frameSelect : item.text
                },() => this.getData());
           
            }else{
    
                this.startInput.setValue(startDate/1000);
                this.stopInput.setValue(stopDate/1000)
                this.setState({
                    start : startDate ,
                    stop: stopDate ,
                    frameSelect : item.text
                },() => this.getData());
         
            }
        }

    render() {
        return (
            <div className='p-col-12 p-md-12  mt-1' >
                <div className='box_shadow ' ref={c => this.chartContainer = c} style={{ position: 'relative' }}>

                    
                <div style={{display: 'flex', alignItems: 'center', padding: 7, position: 'absolute', zIndex: 1, top: '30px', left: '31px' }}>
                        
                        {
                            this.Frame.map(item => (
                                <div 
                                    key={item.text}
                                     onClick={(e) => this.calDate(item)}
                                    style={this.state.frameSelect == item.text ? 
                                        { width : '32px' , height : '22px' , textAlign : 'center' , color  : 'black' , background : 'rgb(230, 235, 245)' , marginRight : '10px', fontWeight : 'bold',cursor : 'pointer'}:
                                        { width : '32px' , height : '22px' , textAlign : 'center' , color  : 'black' , background : '#f7f7f7' , marginRight : '10px',cursor : 'pointer'}
                                    }
                                     > {item.text}</div>
                            ))
                        }
        
                    </div>

                    <div className='cus-hide' style={{ display: 'flex', alignItems: 'center', padding: 7, position: 'absolute', zIndex: 1, top: '35px', right: '35px' }}>

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

                    {/* <div style={{ display: 'flex', position: 'absolute', top: 15, right: 20, zIndex: 100 }}>

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
                    // constructorType={'stockChart'}
                    />
                </div>

            </div>
        );
    }
    dislegend() {
        if (this.state.selected) {
            this.state.seriestemponary.map(item => {
                item.visible = true
            })
        } else {
            this.state.seriestemponary.map(item => {
                item.visible = false
            })
        }

        this.setState({
            chartOptions: {
                series: this.state.seriestemponary
            }
        })
    }

    getData() {

        var symbols = {};


        var resultModel = new Actions();

        resultModel.getAll(App.accountSelector.selected()).then(res => {
            if (res['data']) {
                res = res['data'];


                var data = {};

                for (let i in res) {

                    if (res[i][ACTION_PENDING] == 1) continue;

                    var symbol = res[i][ACTION_SYMBOL];

                    var time = Number(res[i][ACTION_SELL_TIME]);

                    var realPNL = Number(res[i][ACTION_PNL]) - Number(res[i][ACTION_COMMIT]);

                    if (time > this.state.stop || time < this.state.start) continue;

                    if (res[i][ACTION_PENDING] == 0 && res[i][ACTION_STATUS] != ACTION_STATUS_CANCLE) {
                        if (!isset(data[symbol])) {
                            // data[symbol] = Number(res[i][ACTION_REALPROFIT]) 
                            data[symbol] = realPNL
                        } else {
                            // data[symbol] += Number(res[i][ACTION_REALPROFIT])
                            data[symbol] += realPNL
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
                                type: 'column',
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
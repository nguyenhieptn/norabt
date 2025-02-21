import React, { Component } from 'react';
import Highcharts from 'highcharts';
import HighchartsReact from 'highcharts-react-official'
import Input from '../../input/Input';
import Testnet_results from '../../../model/admin/Testnet_results';
class ChartStopLossPer extends Component {
    constructor(props) {
        super(props);
        this.state = {
            start: 0,
            stop: moment().format('x'),
            frameSelect: 'All',
            selected: true,
            seristemponary: [],

            ChartOptions: {
                chart: {
                    type: 'column',
                    height: 600
                },
                title: {

                    text: '<b>Stop Loss Per Coin %</b>',

                    margin: 45
                },
                xAxis: {

                },
                yAxis: {

                    title: {
                        text: '<b></b>'
                    },
                    lineWidth: 1,
                    opposite: true,
                },
                credits: {
                    enabled: false
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
                                return formatNumber(this.y);
                            }
                        },
                        pointWidth: 20,
                        groupPadding: 0,

                    }
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
                ChartOptions: {
                    ...this.setState.ChartOptions,
                    chart: {
                        width: this.chartContainer ? this.chartContainer.clientWidth : 0,
                    }

                }
            })
        }, 500);
    }



    render() {
        return (
            <div className='col-12' >
                <div className='box_shadow ' ref={c => this.chartContainer = c} style={{ width: '100%', background: 'white', position: 'relative' }}>
                    <div style={{ display: 'flex', alignItems: 'center', position: 'absolute', top: 8, left: 5, zIndex: 100 }}>
                        <div className='button btn' style={{ borderRadius: 0, padding: '2px 5px', fontWeight: (this.state.selected == true ? 'bold' : '100'), background: (this.state.selected == true ? 'rgb(230, 235, 245)' : '#f7f7f7') }} onClick={() => {
                            this.setState({ selected: !this.state.selected },
                                () => this.dislegend()
                            );
                        }}>ALL</div>

                    </div>

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
                        options={this.state.ChartOptions}
                    />

                </div>

            </div>
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

    async getData() {

        var resultModel = new Testnet_results();
        var res = await resultModel.getByAccountTestnet(App.accountSelectorTestnet.selected())
        if (res['result']) {
            res = res['data'];
            var series = [];
            var coin = [];
            var total = [];
            res.map(item => {
                var time = item[TESTNET_RESULT_SELL_TIME];
                if (time < this.state.stop && time > this.state.start){

                    if(Number(item[TESTNET_RESULT_STATUS]) == 3){
                        var index = coin.indexOf(item[TESTNET_RESULT_SYMBOL]);
    
                        var realPNL = Number(item[TESTNET_RESULT_EVENT_PROFIT]);
                        if (index >= 0) {
                                total[index] += realPNL;
                        } else {
                            coin.push(item[TESTNET_RESULT_SYMBOL]);
                            total.push(realPNL);
        
                        }
                    }

                }
                
              


            })
        }
    

        total.map((total, index) => {
            var obj = {};
            obj['name'] = coin[index];
            obj['data'] = [Number(total.toFixed(3))];
            series.push(obj);
        })

        series.sort(function (a, b) {
            return a.data[0] - b.data[0];
        });


        this.setState({
            seristemponary: series,
            ChartOptions: {
                series
            }
        })
    }

    dislegend() {
        if (this.state.selected) {
            this.state.seristemponary.map(item => {
                item.visible = true
            })
        } else {
            this.state.seristemponary.map(item => {
                item.visible = false
            })
        }

        this.setState({
            ChartOptions: {
                series: this.state.seristemponary
            }
        })
    }
}

export default ChartStopLossPer;
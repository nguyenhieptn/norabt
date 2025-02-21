import React, { Component } from 'react';
import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official'

import Testnet_results from '../../model/admin/Lab_results';

import Input from '../input/Input';
import XLSX from 'xlsx';
import Lab_account from '../../model/admin/Lab_account';
class ChartPNLDaily extends Component {

    constructor(props) {
        super(props);
        this.state = {
            start: '',
            stop: '',
            coin: [],
            selected: {},
            dateSeleted : 'week',
            Options: {
                chart: {}

                ,
                exporting: {
                    enabled: false
                },
                title: {
                    text: '<b>PNL</b>',
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
                    column: {
                        zones: [{
                            value: 0,
                            color: 'red'
                        }, {
                            color: 'dodgerblue'
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
            },

            accountOptions : {}
        }
        this.updateChartWidth = this.updateChartWidth.bind(this);

    }
    componentDidMount() {
        this.updateChartWidth();
        this.resize_ob = new ResizeObserver((entries) => {
            this.updateChartWidth()
        });
        this.resize_ob.observe(this.chartContainer);

        this.getAccount()

    }
    componentWillUnmount() {
        if (this.resize_ob) this.resize_ob.unobserve(this.chartContainer);
    }
    updateChartWidth() {
        if (this.updateWidthTimeout) clearTimeout(this.updateWidthTimeout);
        this.updateWidthTimeout = setTimeout(() => {

            this.setState({
                Options: {
                    ...this.state.Options,
                    chart: {
                        width: typeof (this.chartContainer) !== null && this.chartContainer.clientWidth,
                    }

                }
            })
        }, 500);
    }

    getAccount() {

        var accountSymbol = new Lab_account();
        accountSymbol.read(null, false).then((res) => {
            if (res['data']) {
                var response = res['data'];
              
                var accountOptions = {};

                response.map(item => {

                    accountOptions[item[LAB_ACCOUNT_ID]] = item[LAB_ACCOUNT_NAME]
                   
                
                });

                this.setState({accountOptions})


            }
        })


    }

    exportToExcel(data , account, option) {
        const worksheet = XLSX.utils.json_to_sheet(data);
        // worksheet['A1'].v = 'time';
        // worksheet['B1'].v = 'pnl';
        const workbook = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(workbook, worksheet, "Data");
        XLSX.writeFile(workbook,   `${account}-${option}.xlsx`);
    }
    onExport() {

        let data = this.state.Options.series[0]['data']

        let tranData = []
        data.map(item => {
            tranData.push({
                // timestamp : item['x'],
                time : moment(item['x'] , 'x').format(DATE_FORMAT),
                pnl : item['y']
            })
        })

        this.exportToExcel(tranData,this.state.accountOptions[App.accountSelectorLab.selected()],this.state.dateSeleted);
    }
    render() {
        return (
            <>
                <div className='p-col-12 p-md-12 ' >
                    <div className='box_shadow ' ref={c => this.chartContainer = c} style={{ position: 'relative' }}>



                        {!App.isMobile() &&
                            <div className='cus-hide' style={{ display: 'flex', alignItems: 'center', padding: 7, position: 'absolute', zIndex: 1, top: '35px', right: '48px' }}>

                                <Input ref={c => this.startInput = c} placeholder="Start Time" className='input' struct={{
                                    [INPUT_TYPE]: 'date',
                                    [INPUT_DEFAULT]: this.state.start != '' ? (this.state.start / 1000) : '',
                                    [INPUT_ONCHANGE_BLUR]: (e, obj) => { this.setState({ start: obj.getValue() * 1000 }, () => this.getData(this.state.dateSeleted)) }
                                }}></Input>

                                &nbsp;

                                <Input ref={c => this.stopInput = c} placeholder="Stop Time" className='input' struct={{
                                    [INPUT_TYPE]: 'date',
                                    [INPUT_DEFAULT]: this.state.stop != '' ? (this.state.stop / 1000) : '',
                                    [INPUT_ONCHANGE_BLUR]: (e, obj) => {
                                        this.setState({ stop: obj.getValue() * 1000 }, () => {
                                            this.getData(this.state.dateSeleted);
                                            // if (obj.getValue() == '') this.startUpdate();
                                        })
                                    }
                                }}></Input>
                                &nbsp;
                                {/* <Input ref={c => this.selectedDate = c} className='input' struct={{
                                    [INPUT_TYPE]: 'select',
                                    [INPUT_DEFAULT]: 1,
                                    [INPUT_ONCHANGE]: (e, obj) => {
                                        this.getData(obj.getValue());
                                    },
                                    [INPUT_OPTION]: {
                                        'day': 'Day',
                                        'week': 'Week',
                                        'month': 'Month',
                                    },
                                }}></Input> */}

                                <div>
                                    <select className='input' value={this.state.dateSeleted} onChange={(e) => {this.getData(e.target.value) ; this.setState({dateSeleted : e.target.value});}}>
                                        <option value="day" >Day</option>
                                        <option value="week">Week</option>
                                        <option value="month">Month</option>
                                        <option value="year">Year</option>

                                    </select>
                                </div>

                                <div className="button function_button" onClick={() => this.onExport()}>
                                    <span><i className="fa fa-save"></i></span>
                                    <span>&nbsp;Export</span>
                                </div>

                            </div>
                        }

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

    getData(option) {

        var a = {
            'day': 86400 * 1000,
            'week': 604800 * 1000,
            'month': 2592000 * 1000,
            'year': 2592000 * 1000 * 12,
        };

        var distance = a[option];

        var resultModel = new Testnet_results();

        resultModel.getByAccount().then(res => {
            // resultModel.get([[[LAB_RESULT_STRATEGY, '=', App.strategySelector.selected()]]], { 'orderBy': LAB_RESULT_SELL_TIME, 'asc': false }).then(res => {
            if (res['data']) {
                res = res['data'];
                // console.log(res)
                var data = [];

                // var limitTime = Number(moment().startOf('day').format('x'));
                var limitTime = this.state.stop == '' ? Number(moment().startOf(option).format('x')) : this.state.stop;
                if(option == 'week'){
                    limitTime = this.state.stop == '' ? Number(moment().startOf(option).format('x')) +86400000 : this.state.stop;
                }
              


                for (let i in res) {


                    if (res[i][LAB_RESULT_PENDING] == 1) continue;

                    var tempTime = Number(res[i][LAB_RESULT_SELL_TIME])
                    if(tempTime == 0) continue;
                    if (tempTime == 0) continue;
                    if (this.state.start !== '') {
                        if (tempTime < this.state.start) continue;
                    }

                    if (tempTime >= limitTime && isset(data[0])) {
                        // var xvalue = moment(limitTime, 'x').format("DD/MM/YYYY");
                        var xvalue = limitTime;
                        if (res[i][LAB_RESULT_PENDING] == 0 && res[i][LAB_RESULT_STATUS] != LAB_RESULT_STATUS_CANCLE) {
                            var yvalue = Number(res[i][LAB_RESULT_REAL_PNL]) + Number(data[0].y);
                            data[0].y = Number(yvalue.toFixed(2))
                        }
                    } else {
                        while (tempTime < limitTime) {
                            // limitTime -= 86400 * 1000;
                            if(option == 'month'){

                                distance = (new Date( moment(limitTime).year(),  moment(limitTime).month() , 0)).getDate() * 86400000;
                               
                            }
                            if (option == 'year') {

                                const date = new Date(limitTime);
                                const year = date.getFullYear();
                                const daysInYear = (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0 ? 366 : 365;
                                distance = daysInYear * 86400000;

                            }
                            limitTime -= distance;
                        }

                        // var xvalue = moment(limitTime, 'x').format("DD/MM/YYYY");
                        var xvalue = limitTime;
                        if (res[i][LAB_RESULT_PENDING] == 0 && res[i][LAB_RESULT_STATUS] != LAB_RESULT_STATUS_CANCLE) {
                            var yvalue = Number(res[i][LAB_RESULT_REAL_PNL].toFixed(2));
                        } else {
                            var yvalue = 0;
                        }

                        data.unshift({
                            x: xvalue,
                            y: yvalue
                        })
                    }

                }





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
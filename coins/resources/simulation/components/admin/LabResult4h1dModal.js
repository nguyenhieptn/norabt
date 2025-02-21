import React, { Component } from 'react';
import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official';
import Lab_results from '../../model/admin/Lab_results';

class LabResult4h1dModal extends Component {
    constructor(props) {
        super(props);

        this.id = makeId()

        this.symbol = '',
            this.state = {

                frame: '4h',
                interval: '5',

                account: {},

                maxPerInBa: 0,
                daymaxPerInBa: 0,
                maxPerUreBa: 0,
                daymaxPerUreBa: 0,

                Options: {
                    chart: {
                    }
                    ,
                    title: {
                        text: '',
                    },
                    xAxis: {
                        type: 'category',
                        labels: {
                            formatter: function () {
                                return moment(this.value,'x').utc().format('HH:mm');
                            },
                            step: 1
                        }
                    },
                    scrollbar: {
                        enabled: false
                    },
                    credits: {
                        enabled: false
                      },
                    yAxis: [
                        {
                            crosshair: true,
                            title: {
                                text: '<b></b>',
                            },

                            // startOnTick: false,

                            labels: {
                                align: 'left'
                            }

                        },
                        {
                            crosshair: true,
                            title: {
                                text: '<b></b>',
                            },

                            // startOnTick: false,

                            labels: {
                                align: 'right'
                            },
                            
                            opposite: false

                        },

                    ],

                    chart: {
                        height: (6 / 16 * 100) + '%',
                        panning: {
                            enabled: true,
                            type: 'x'
                        },
                        panKey: 'shift',
                        zoomType: 'x'

                    },
                    legend: {
                        enabled: true,


                    },
                    plotOptions: {
                        series: {
                            dataLabels: {
                                enabled: false
                            },
                            lineWidth: 1,
                            maxPointWidth: 100,
                            turboThreshold: 0,

                            marker: {
                                enabled: false
                            }
                        }

                    },
                    tooltip: {
                        style: {
                            fontSize: '10px'
                        },
                        shared: true,
                        split: false,
                        
                        // formatter: function () {
                        //     return 'Time:' + moment(this.x ,'x').utc().format('HH:mm') + ' Value:' + this.y + '</div>';
                        // }
                        
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
                                    text: '1M',
                                    type: 'day',
                                    count: 30,

                                },
                                {
                                    text: '2M',
                                    type: 'day',
                                    count: 60,

                                },
                                {
                                    text: '3M',
                                    type: 'day',
                                    count: 90,

                                },
                                {
                                    text: '6M',
                                    type: 'day',
                                    count: 180,

                                },
                                {
                                    text: '1Y',
                                    type: 'day',
                                    count: 365,

                                },
                                {
                                    type: 'all',
                                    text: 'All'
                                },
                            ],
                        inputEnabled: false,
                        buttonSpacing: 10,
                    },

                    series: [
                        {
                            name: 'Stoploss Position',
                            id: "stoploss_pos",
                            data: [],
                            type: 'column',
                        },
                        {
                            name: 'Stoploss Position(%)',
                            id: "stoploss_pos_percent",
                            data: [],
                            type: 'column',
                            visible: false,
                        },
                        {
                            name: 'Stoploss USDT',
                            id: "stoploss_usdt",
                            data: [],
                            type: 'column',
                            color: 'blue',
                            yAxis: 1,
                            visible: false,

                        },
                        {
                            name: 'Takeprofit Position',
                            id: "takeprofit_pos",
                            data: [],
                            type: 'column',
                            color: 'red',
                            visible: false,
                        },
                        {
                            name: 'Takeprofit Position(%)',
                            id: "takeprofit_pos_percent",
                            data: [],
                            type: 'column',
                            visible: false,
                        },
                        {
                            name: 'Takeprofit USDT',
                            id: 'takeprofit_usdt',
                            data: [],
                            type: 'column',
                            yAxis: 1,
                            color: 'limegreen',
                            visible: false,
                        },

                    ]
                }
            }
        this.updateChartWidth = this.updateChartWidth.bind(this);

        this.colors = {};

        Highcharts.setOptions({
            time: {
                timezoneOffset: moment().utcOffset(),
                useUTC: false
            }
        });

        this.startTime = null;
        this.chartData = {};

        this.resetIndex = 0;

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



    setRangeSelector() {

        console.log('Set rangselector to 4')

        this.setState({
            Options: { rangeSelector: { selected: 4 } },
        })

    }

    modal(cmd = 'show') {
        if (cmd == 'hide') {
            $("#edit_row_modal" + this.id).modal('hide');
        } else {
            $("#edit_row_modal" + this.id).modal();
        }
    }

    loadData(rowData) {
        this.setState({ account: rowData });
        this.getData(rowData[LAB_ACCOUNT_ID]);
    }

    render() {

        
        return (
            <>

                <div className="modal fade" id={"edit_row_modal" + this.id} onClick={() => { addClass($('body')[0], 'modal-open') }}>
                    <div className="modal-dialog modal-lg modal-dialog-centered" style={{ maxWidth: '95%' }}>
                        <div className="modal-content">

                            <div className="modal-header">
                                <h4 className="modal-title">{this.state.account[LAB_ACCOUNT_NAME]}</h4>
                                <button type="button" className="close" data-dismiss="modal">&times;</button>
                            </div>

                            <div className="modal-body" style={{ textAlign: 'initial' }}>

                                <div className='box_shadow cus-hide ' ref={c => this.chartContainer = c} style={{ position: 'relative', marginTop: 15, padding: 5 }}>
                                    <div style={{ display: 'flex', position: 'absolute', top: '12px', right: '30px', zIndex: 1000 }}>
                                        <select className='input' value={this.state.frame} onChange={e =>{
                                            this.setState({frame: e.target.value}, ()=>this.getData(this.state.account[LAB_ACCOUNT_ID]))
                                        }}>
                                            <option value="4h">4H</option>
                                            <option value="1d">1D</option>
                                        </select>
                                        &nbsp;
                                        <select className='input' value={this.state.interval} onChange={e =>{
                                            this.setState({interval: e.target.value}, ()=>this.getData(this.state.account[LAB_ACCOUNT_ID]))
                                        }}>
                                            <option value="5">5 minutes</option>
                                            <option value="15">15 minutes</option>
                                            <option value="30">30 minutes</option>
                                            <option value="60">60 minutes</option>
                                        </select>
                                    </div>
                                    <HighchartsReact
                                        ref={c => this.chart = c}
                                        highcharts={Highcharts}
                                        options={this.state.Options}
                                        constructorType={'stockChart'}
                                    />


                                </div>
 

                            </div>

                            <div className="modal-footer">
                                {isset(this.props.extraFunction) ? this.props.extraFunction : ''}
                                <button type="button" className="btn btn-danger" data-dismiss="modal">{lang('Close')}</button>
                            </div>

                        </div>
                    </div>
                </div>


            </>
        );
    }


    getData(id){
        console.log(id)
        // this.chart.chart.showLoading()
        let acmodel = new Lab_results()

        let stoplossPos = {}
        let stoplossUsdt = {}
        let profitPos = {}
        let profitUsdt = {}

        let frameTime = 4*60*60*1000
        if(this.state.frame == '1d') frameTime = 24*60*60*1000
        let interval = Number(this.state.interval) * 60000

        var index = 1
        while(true){
            let wrapTime = index * interval
            stoplossPos[wrapTime]= {
                x: wrapTime,
                y: 0
            }
            stoplossUsdt[wrapTime]= {
                x: wrapTime,
                y: 0
            }
            profitPos[wrapTime]= {
                x: wrapTime,
                y: 0
            }
            profitUsdt[wrapTime]= {
                x: wrapTime,
                y: 0
            }
            if(wrapTime >= frameTime) break
            index ++

        }

        let totalStoploss = 0;
        let totalTakeprofit = 0;

        acmodel.getByAccount(id).then(res => {
            if(res['result']){
                let pos = res['data']
                for(let index in pos){
                    let p = pos[index]
                    let openTime = Number(p[LAB_RESULT_CHART])
                    
                    let wrapTime = Math.ceil((openTime%frameTime)/interval)*interval
                    if(p[LAB_RESULT_STATUS] == LAB_RESULT_STATUS_STOPLOSS){
                        totalStoploss ++;
                        if(!isset(stoplossPos[wrapTime])){
                            stoplossPos[wrapTime] = {
                                x : wrapTime,
                                y : 1
                            }
                        }else{
                            stoplossPos[wrapTime].y ++
                        }
                        if(!isset(stoplossUsdt[wrapTime])){
                            stoplossUsdt[wrapTime] = {
                                x: wrapTime,
                                y: Number(p[LAB_RESULT_REAL_PNL])
                            }
                        }else{
                            stoplossUsdt[wrapTime].y += Number(p[LAB_RESULT_REAL_PNL])
                        }
                    }

                    if(p[LAB_RESULT_STATUS] == LAB_RESULT_STATUS_TAKEPROFIT){
                        totalTakeprofit ++
                        if(!isset(profitPos[wrapTime])){
                            profitPos[wrapTime] = {
                                x: wrapTime,
                                y: 1
                            }
                        }else{
                            profitPos[wrapTime].y ++
                        }
                        if(!isset(profitUsdt[wrapTime])){
                            profitUsdt[wrapTime] = {
                                x: wrapTime,
                                y: Number(p[LAB_RESULT_REAL_PNL])
                            }
                        }else{
                            profitUsdt[wrapTime].y += Number(p[LAB_RESULT_REAL_PNL])
                        }
                    }
                }

                let stoplossPosValues = Object.values(stoplossPos)
                let stoplossPercent = stoplossPosValues.map((e)=>{
                    return {
                        x : e.x,
                        y: Number((e.y * 100/totalStoploss).toFixed(2))
                    }
                })

                let takeprofitPosValues = Object.values(profitPos)
                let takeprofitPercent = takeprofitPosValues.map((e)=>{
                    return {
                        x : e.x,
                        y: Number((e.y * 100/totalTakeprofit).toFixed(2))
                    }
                })

                this.setState({
                    
                    Options: {
                        series: [
                            {
                                data: stoplossPosValues
                            },

                            {
                                data: stoplossPercent
                            },

                            {
                                data: Object.values(stoplossUsdt)
                            },
                            {
                                data: takeprofitPosValues
                            },
                            {
                                data: takeprofitPercent
                            },
                            {
                                data: Object.values(profitUsdt)
                            }
                        ]
                    }
                })
            }
        })
    }



    




}

export default LabResult4h1dModal;
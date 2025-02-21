import React, { Component } from 'react';
import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official'
// import Candle_4h from '../../model/analytics/Candle_4h';
// import Candle_1h from '../../model/analytics/Candle_1h';
// import Candle_1d from '../../model/analytics/Candle_1d';

import Candle_4h from '../../model/admin/Lab_candle_4h';
import Candle_1h from '../../model/admin/Lab_candle_1h';
import Candle_1d from '../../model/admin/Lab_candle_1d';

require('highcharts/indicators/indicators')(Highcharts);
require('highcharts/indicators/ema')(Highcharts);
import Input from '../input/Input';
class FluctuationsChart extends Component {
    constructor(props) {
        super(props);

        this.id = makeId();

        this.state = {
            start: '',
            stop: null,

            maxWMA: '',
            minWMA: '',
            maxRSI4h0: '',
            minRSI4h0: '',
            maxRSI4h1: '',
            minRSI4h1: '',
            maxRSI1h0: '',
            minRSI1h0: '',

            highlowavg: 0,
            lowlowavg: 0,
            highhighavg: 0,
            symbol: '',
            frame: '',
            maxHighLow : 0,
            minLowLow : 0,

            Options: {
                chart: {
                }
                ,
                title: {
                    text: '',
                },
                xAxis: {
                },

                yAxis: [
                    {
                        crosshair: true,
                        title: {
                            text: '<b>Volatility(%)</b>',
                        },

                        startOnTick: false,

                        labels: {
                            align: 'left'
                        }

                    },

                ],

                chart: {
                    height: (9 / 16 * 100) + '%',
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
                                text: '1D',
                                type: 'day',
                                count: 1,

                            },
                            {
                                text: '2D',
                                type: 'day',
                                count: 2,

                            },
                            {
                                text: '3D',
                                type: 'day',
                                count: 3,

                            },
                            {
                                text: '6D',
                                type: 'day',
                                count: 6,

                            },
                            {
                                text: '7D',
                                type: 'day',
                                count: 7,

                            },
                            {
                                type: 'all',
                                text: 'All'
                            },
                        ],
                    inputEnabled: false,
                    // selected: 1,
                    buttonSpacing: 10,
                },
                series: [
                    {
                        name: 'High-Low',
                        id: "highlow",
                        data: [],
                    },
                    {
                        name: 'High-High',
                        id: "highhigh",
                        data: [],
                    },
                    {
                        name: 'Low-Low',
                        id: "lowlow",
                        data: [],
                    }
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

        this.data = {};

    }
    componentDidMount() {

        this.updateChartWidth();
        this.resize_ob = new ResizeObserver((entries) => {
            this.updateChartWidth()
        });
        this.resize_ob.observe(this.chartContainer);

        // setTimeout(() => this.setRangeSelector(), 3000);

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

    getRandomColor(item) {
        if (isset(this.colors[item])) return this.colors[item];
        var letters = '0123456789ABCDEF';
        var color = '#';
        for (var i = 0; i < 6; i++) {
            color += letters[Math.floor(Math.random() * 16)];
        }
        this.colors[item] = color;
        return this.colors[item];
    }


    setRangeSelector() {

        console.log('Set rangselector to 5')
        this.setState({
            Options: { rangeSelector: { selected: 5 } },
        })

    }

    modal(cmd = 'show') {
        if (cmd == 'hide') {
            $("#bladeModal" + this.id).modal('hide');
        } else {
            $("#bladeModal" + this.id).modal();
        }
    }

    render() {

        return (
            <>
                <div className="modal fade" id={"bladeModal" + this.id}>
                    <div className="modal-dialog modal-lg modal-dialog-centered" style={{ maxWidth: '95%' }}>
                        <div className="modal-content">

                            <div className="modal-header">
                                <span>{this.state.symbol} {this.state.frame}</span>
                                <button type="button" className="close" data-dismiss="modal">&times;</button>
                            </div>

                            <div ref={c => this.chartContainer = c} className="modal-body" style={{ textAlign: 'initial' }}></div>

                            <div className='box_shadow ' ref={c => this.chartContainer = c} style={{ position: 'relative', padding: 5 }}>

                                <div>
                                    <div>Condition</div>
                                    <div className='box_flex' style={{ margin: 5 }}><li style={{ width: 300 }}>RSI WMA 1D BTC (low-low only) </li> from &nbsp; <input className='input' value={this.state.minWMA} onChange={(e) => {
                                        this.setState({
                                            minWMA: e.target.value
                                        })
                                    }} type='number'></input> &nbsp; to &nbsp; <input className='input' value={this.state.maxWMA} onChange={(e) => {
                                        this.setState({
                                            maxWMA: e.target.value
                                        })
                                    }} type='number'></input></div>
                                    <div className='box_flex' style={{ margin: 5 }}><li style={{ width: 300 }}>RSI 4h(0) (high-high only) </li> from &nbsp; <input className='input' value={this.state.minRSI4h0} onChange={(e) => {
                                        this.setState({
                                            minRSI4h0: e.target.value
                                        })
                                    }} type='number'></input> &nbsp; to &nbsp; <input className='input' value={this.state.maxRSI4h0} onChange={(e) => {
                                        this.setState({
                                            maxRSI4h0: e.target.value
                                        })
                                    }} type='number'></input></div>
                                    <div className='box_flex' style={{ margin: 5 }}><li style={{ width: 300 }}>RSI 4h(-1) (high-high only) </li> from &nbsp; <input className='input' value={this.state.minRSI4h1} onChange={(e) => {
                                        this.setState({
                                            minRSI4h1: e.target.value
                                        })
                                    }} type='number'></input> &nbsp; to &nbsp; <input className='input' value={this.state.maxRSI4h1} onChange={(e) => {
                                        this.setState({
                                            maxRSI4h1: e.target.value
                                        })
                                    }} type='number'></input></div>
                                    <div className='box_flex' style={{ margin: 5 }}><li style={{ width: 300 }}>RSI 1h(0) (high-high only) </li> from &nbsp; <input className='input' value={this.state.minRSI1h0} onChange={(e) => {
                                        this.setState({
                                            minRSI1h0: e.target.value
                                        })
                                    }} type='number'></input> &nbsp; to &nbsp; <input className='input' value={this.state.maxRSI1h0} onChange={(e) => {
                                        this.setState({
                                            maxRSI1h0: e.target.value
                                        })
                                    }} type='number'></input></div>
                                    <div><div className='btn btn-sm btn-primary' style={{ margin: 10, marginLeft: 200 }} onClick={() => { this.getData(this.state.symbol, this.state.frame) }}>Apply</div></div>
                                </div>

                                <div style={{ position: 'absolute', top: '20px', right: '45px' }}>
                                    <div style={{ marginBottom: '5px' }}><b>High - Low Avg : {this.state.highlowavg.toFixed(3)} % </b></div>
                                    <div style={{ marginBottom: '5px' }}><b>Low - Low Avg (less than 0 only) : {this.state.lowlowavg.toFixed(3)} % </b></div>
                                    <div style={{ marginBottom: '5px' }}><b>High - High Avg (greater than 0 only) : {this.state.highhighavg.toFixed(3)} % </b></div>

                                    <div style={{ marginBottom: '5px' }}><b>Max : {this.state.maxHighLow.toFixed(3)} % </b></div>
                                    <div><b>Min : {this.state.minLowLow.toFixed(3)} %</b></div>
                                </div>

                                {!App.isMobile() &&
                                    <div className='cus-hide' style={{ display: 'flex', alignItems: 'center', padding: 7, position: 'absolute', zIndex: 1, top: '198px', right: '60px' }}>

                                        <Input ref={c => this.startInput = c} placeholder="Start Time" className='input' key={this.state.start} struct={{
                                            [INPUT_TYPE]: 'date',
                                            [INPUT_DEFAULT]: this.state.start ? (this.state.start / 1000) : '',
                                            [INPUT_ONCHANGE_BLUR]: (e, obj) => { this.setState({ start: obj.getValue() * 1000 }, () => this.getData(this.state.symbol, this.state.frame)) }
                                        }}></Input>

                                        &nbsp;

                                        <Input ref={c => this.stopInput = c} placeholder="Stop Time" key={this.state.stop} className='input' struct={{
                                            [INPUT_TYPE]: 'date',
                                            [INPUT_DEFAULT]: this.state.stop ? (this.state.stop / 1000) : '',
                                            [INPUT_ONCHANGE_BLUR]: (e, obj) => {
                                                this.setState({ stop: obj.getValue() * 1000 }, () => {
                                                    this.getData(this.state.symbol, this.state.frame);
                                                    // if (obj.getValue() == '') this.startUpdate();
                                                })
                                            }
                                        }}></Input>

                                    </div>
                                }

                                <HighchartsReact
                                    ref={c => this.chart = c}
                                    highcharts={Highcharts}
                                    options={this.state.Options}
                                    constructorType={'stockChart'}
                                />

                                {/* <div>
                                    <div><b>High - Low Avg : {this.state.highlowavg.toFixed(3)} % </b></div>
                                    <div><b>Low - Low Avg (less than 0 only) : {this.state.lowlowavg.toFixed(3)} % </b></div>
                                    <div><b>High - High Avg (greater than 0 only) : {this.state.highhighavg.toFixed(3)} % </b></div>
                                </div> */}


                            </div>

                            <div className="modal-footer">
                                <button type="button" className="btn btn-danger" data-dismiss="modal">Close</button>
                            </div>

                        </div>
                    </div>
                </div>


            </>
        );
    }



    async getData(symbol, frame) {

        // var colNames = {
        //     symbol: 'candle_' + frame + '_symbol',
        //     low: 'candle_' + frame + '_low',
        //     high: 'candle_' + frame + '_high',
        //     time: 'candle_' + frame + '_close_time',
        //     opentime: 'candle_' + frame + '_open_time',
        //     startpoint: 'candle_' + frame + '_startpoint',
        //     rsi14: 'candle_' + frame + '_rsi14',
        // }

        var colNames = {
            symbol: 'lab_candle_' + frame + '_symbol',
            low: 'lab_candle_' + frame + '_low',
            high: 'lab_candle_' + frame + '_high',
            time: 'lab_candle_' + frame + '_close_time',
            opentime: 'lab_candle_' + frame + '_open_time',
            startpoint: 'lab_candle_' + frame + '_startpoint',
            rsi14: 'lab_candle_' + frame + '_rsi14',
        }

        var btcData = await this.loadData('BTCUSDT', '1d');
      
       
        if (!btcData) return;
        var btcDataIndex = {};
        for (let i in btcData) {
            // btcDataIndex[btcData[i][CANDLE_1D_OPEN_TIME]] = btcData[i];
            btcDataIndex[btcData[i][LAB_CANDLE_1D_OPEN_TIME]] = btcData[i];
        }

        var data4h = await this.loadData(symbol, '4h');
      
        if (!data4h) return;
        var data4hIndex = {};
        for (let i in data4h) {
            // data4hIndex[data4h[i][CANDLE_4H_OPEN_TIME]] = data4h[i];
            data4hIndex[data4h[i][LAB_CANDLE_4H_OPEN_TIME]] = data4h[i];
        }

        var data1h = await this.loadData(symbol, '1h');
        
        if (!data1h) return;
        var data1hIndex = {};
        for (let i in data1h) {
            // data1hIndex[data1h[i][CANDLE_1H_OPEN_TIME]] = data1h[i];
            data1hIndex[data1h[i][LAB_CANDLE_1H_OPEN_TIME]] = data1h[i];
        }


        var symbolData = await this.loadData(symbol, frame);
        
        if (!symbolData) return;


        var datas = symbolData;

        var lowlow = [];
        var highhigh = [];
        var highlow = [];

        var lowlowsum = 0;
        var highhighsum = 0;
        var highlowsum = 0;

        var lowlowcount = 0;
        var highlowcount = 0;
        var highhighcount = 0;


        var maxHighLow = 0;
        var minLowLow = 0;
        if(this.state.start == '' && this.state.stop == null ){
            this.setState({
                start : datas[1][colNames.time],
                stop : datas[datas.length - 1][colNames.time],
            });
        }
        
        for (let i in datas) {
            if (isset(datas[i - 1])) {

                var time = Number(datas[i][colNames.time]);
               


                if (time == 0) continue;

                if (Number(datas[i][colNames.low]) > 0) {
                    var highlowval = Number(((Number(datas[i][colNames.high]) - Number(datas[i][colNames.low])) * 100 / Number(datas[i][colNames.high])).toFixed(3));
                    
                    if (this.state.start <= time && this.state.stop >= time) {
                        highlow.push({
                            x: time,
                            y: highlowval
                        })

                        highlowsum += highlowval;
                        highlowcount++;

                        if(highlowval > maxHighLow){
                            maxHighLow = highlowval
                        } 
                    }


                   
                }


                if (Number(datas[i - 1][colNames.low]) > 0) {

                    var ignore = false;
                    if (this.state.maxWMA != '' || this.state.minWMA != '') {
                        var openTime = Number(datas[i][colNames.opentime]);
                        var openTimeBTC = Math.floor(openTime / 86400000) * 86400000;
                        if (!isset(btcDataIndex[openTimeBTC])) {
                            ignore = true;
                        } else {
                            // var wmaBTC = btcDataIndex[openTimeBTC][CANDLE_1D_RSI_WMA];
                            var wmaBTC = btcDataIndex[openTimeBTC][LAB_CANDLE_1D_RSI_WMA];
                        }


                        if (!ignore && this.state.minWMA != '') {
                            if (wmaBTC < this.state.minWMA) ignore = true;
                        }
                        if (this.state.maxWMA != '') {
                            if (wmaBTC > this.state.maxWMA) ignore = true;
                        }
                    }

                    if (!ignore) {

                        var lowlowval = Number(((Number(datas[i][colNames.low]) - Number(datas[i - 1][colNames.low])) * 100 / Number(datas[i][colNames.low])).toFixed(3));

                       
                        if (this.state.start <= time && this.state.stop >= time) {
                            if (lowlowval < 0) {
                                lowlowsum += lowlowval
                                lowlowcount++;
                            } else {
                                lowlowval = 0;
                            }

                            lowlow.push({
                                x: time,
                                y: lowlowval
                            })

                            if( lowlowval  < minLowLow ){
                                minLowLow = lowlowval
                            } 

                           
                        }

                    }



                }


                if (Number(datas[i - 1][colNames.high]) > 0) {

                    var ignore = false;

                    if (this.state.minRSI4h1 != '' || this.state.maxRSI4h1 != '' || this.state.minRSI4h0 != '' || this.state.maxRSI4h0 != '') {

                        var openTime = Number(datas[i][colNames.opentime]);
                        var openTime4h = Math.floor(openTime / 14400000) * 14400000;
                        if (!isset(data4hIndex[openTime4h])) {
                            ignore = true;
                        } else {
                            // var rsi4h0 = data4hIndex[openTime4h][CANDLE_4H_RSI14]
                            var rsi4h0 = data4hIndex[openTime4h][LAB_CANDLE_4H_RSI14]
                            if (!isset(data4hIndex[openTime4h - 14400000])) {
                                ignore = true;
                            } else {
                                var rsi4h1 = data4hIndex[openTime4h - 14400000][LAB_CANDLE_4H_RSI14]
                            }

                        }

                        if (!ignore && this.state.minRSI4h0 != '') {
                            if (rsi4h0 < this.state.minRSI4h0) ignore = true;
                        }
                        if (!ignore && this.state.minRSI4h1 != '') {
                            if (rsi4h1 < this.state.minRSI4h1) ignore = true;
                        }
                        if (!ignore && this.state.maxRSI4h0 != '') {
                            if (rsi4h0 > this.state.maxRSI4h0) ignore = true;
                        }
                        if (!ignore && this.state.maxRSI4h1 != '') {
                            if (rsi4h1 > this.state.maxRSI4h1) ignore = true;
                        }
                    }


                    if (this.state.minRSI1h0 != '' || this.state.maxRSI1h0 != '') {

                        var openTime = Number(datas[i][colNames.opentime]);
                        var openTime1h = Math.floor(openTime / 3600000) * 3600000;
                        if (!isset(data1hIndex[openTime1h])) {
                            ignore = true;
                        } else {
                            var rsi1h0 = data1hIndex[openTime1h][LAB_CANDLE_1H_RSI14]
                        }

                        if (!ignore && this.state.minRSI1h0 != '') {
                            if (rsi1h0 < this.state.minRSI1h0) ignore = true;
                        }

                        if (!ignore && this.state.maxRSI1h0 != '') {
                            if (rsi1h0 > this.state.maxRSI1h0) ignore = true;
                        }

                    }

                    if (!ignore) {
                        var highhighval = Number(((Number(datas[i][colNames.high]) - Number(datas[i - 1][colNames.high])) * 100 / Number(datas[i][colNames.high])).toFixed(3));

                      
                        if (this.state.start <= time && this.state.stop >= time) {
                            if (highhighval > 0) {
                                highhighsum += highhighval
                                highhighcount++;
                            } else {
                                highhighval = 0;
                            }
                            highhigh.push({
                                x: time,
                                y: highhighval
                            })
                        }
                    }


                }


            }

        }

   

        var highlowavg = highlowsum / highlowcount;
        var lowlowavg = lowlowsum / lowlowcount;
        var highhighavg = highhighsum / highhighcount;

        this.setState({
            highlowavg,
            lowlowavg,
            highhighavg,
            symbol,
            frame,
            maxHighLow,
            minLowLow,
            Options: {
                series: [
                    {
                        data: highlow
                    },

                    {
                        data: highhigh
                    },

                    {
                        data: lowlow
                    }
                ]
            }
        })

        this.setRangeSelector()





    }


    async loadData(symbol, frame) {
        var id = symbol + '_' + frame;
        if (isset(this.data[id])) return this.data[id];

        if (frame == '4h') {
            var model = new Candle_4h();
        }
        if (frame == '1h') {
            var model = new Candle_1h();
        }
        if (frame == '1d') {
            var model = new Candle_1d();
        }

        var colNames = {
            symbol: 'lab_candle_' + frame + '_symbol',
            low: 'lab_candle_' + frame + '_low',
            high: 'lab_candle_' + frame + '_high',
            time: 'lab_candle_' + frame + '_close_time',
            opentime: 'lab_candle_' + frame + '_open_time',
            rsi14: 'lab_candle_' + frame + '_rsi14',
            startpoint: 'lab_candle_' + frame + '_startpoint',
        }

        // var symbolData = await model.get([[[colNames.symbol, '=', symbol]]], { orderBy: colNames.time, asc: true, limit: 500 });
        // var symbolData = await model.get([[ [colNames.symbol, '=', symbol] , [colNames.startpoint , '=' , 1] ]], { orderBy: colNames.time, asc: false, limit: 1000 });
        var symbolData = await model.get([[ [colNames.symbol, '=', symbol] , [colNames.startpoint , '=' , 1] ]], { orderBy: colNames.time, asc: true });
        if (!symbolData['result']) {
            error_handle(symbolData);
            return null;
        }

        this.data[id] = symbolData['data'];
        return this.data[id];
    }




}

export default FluctuationsChart;
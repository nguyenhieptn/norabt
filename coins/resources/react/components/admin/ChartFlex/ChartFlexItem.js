import React, { Component } from 'react'
import ChartFelxModel from '../../../model/admin/ChartFelxModel';
import ChartConfig from './ChartConfig';
import Loading from '../../common/Loading'
import ChartClone from './ChartClone';
import Ctrl from '../../../model/control/Ctrl';

class ChartFlexItem extends Component {

    constructor(props) {
        super(props);
        this.id = 'plot' + makeId()
        this.ctrl = new Ctrl()
        this.storageId = this.props.id
        var chartConfig = localStorage.getItem(this.storageId)
        if(chartConfig == null){
            chartConfig = []
        }else{
            chartConfig = JSON.parse(chartConfig)
        }
        this.setChartConfig(chartConfig)

        this.config = {
            data: [],
            layout: {
                height: get(this.chartConfig['height'], 300),
                title: get(this.chartConfig['title'], null),
                autosize: true,
                hovermode: "x unified",
                hoverdistance: 10,
                margin: {b:40, t:40, l:40, r:40},
                xaxis: {
                    autorange: true, 
                    type:"category", 
                    categoryorder : 'category ascending',
                    rangeslider : {'visible': false},
                    showspikes: true, 
                    spikemode: 'across', 
                    spikesnap: 'cursor', 
                    spikedash: 'dot', 
                    spikecolor: 'black', 
                    spikethickness: 1 
                },
                yaxis: {
                    autorange: true, 
                    showspikes: true, 
                    spikemode: 'across', 
                    spikesnap: 'cursor', 
                    spikedash: 'dot', 
                    spikecolor: 'black', 
                    spikethickness: 1 
                },
                barmode: 'group',
                font: {
                    size: 10,
                },

                shapes: [
                    {
                        type: 'line',
                        xref: 'x',
                        yref: 'paper',
                        x0:0,
                        y0:0,
                        x1:0,
                        y1:0,
                        line: {
                            color: 'black',
                            width: 1,
                            dash: 'dot'
                        }
                    }
                ],

                legend:{
                    yanchor:"top",
                    y:1,
                    xanchor:"left",
                    x:0

                }
            }


        }

        this.model = new ChartFelxModel()

    }

    setChartConfig(chartConfig){
        this.chartConfig = chartConfig
        var configs = get(this.chartConfig['configs'], [])
        var timeframe = null
        for(let conf of configs){
            var temp = get(conf['timeframe'], 1)
            if(temp == '') temp = 1
            if(timeframe === null){
                timeframe = temp
            }else{
                if(timeframe > temp) timeframe = temp
            }
        }
        this.minTimeFrame = timeframe;

        if(this.props.isPosition && App.parsed.symbol){
            this.chartConfig['symbol'] = App.parsed.symbol
            this.chartConfig['title'] = App.parsed.symbol
        }
    }

    updateLayout(){
        let currentLayout = this.plot.layout
        currentLayout['title'] = {'text' : get(this.chartConfig['title'], null)}
        currentLayout['height'] = get(this.chartConfig['height'], 300)
        Plotly.relayout(this.plot, currentLayout)
    }

    getData(){
        const {startTime, stopTime} = this.props.parent.getTimeRange()
        if(startTime == '' || stopTime == '') return;
        if(this.chartConfig.length == 0 )return;
        this.loading.loading(true, 'Get Data...')
        this.model.getData(this.chartConfig, startTime, stopTime).then(res => {
            this.loading.loading(false)
            if(res){
                this.updateData(res)
            }
        })
    }


    async updateAllData(){
        if(this.props.isPosition){
            await this.getPosition()
        }
        this.getData()
    }

    
    updateData(datas){
        let chartData = []
        let configIndex = {}
        for(let index in this.chartConfig['configs']){
            let conf = this.chartConfig['configs'][index]
            let type = get(conf['type'], 'line')
            let id = conf['source_data'] + "_" + conf['name'];

            if(!configIndex[id]) configIndex[id] = []
            configIndex[id].push(index)
            
            if(type == 'line'){
                chartData[index] = { name: conf['name'], mode: 'lines', x:[], y:[], line:{color: conf['color_1'], dash: get(conf['dash'], 'solid')}}
            }else if (type=='bar'){
                chartData[index] = { name: conf['name'], type: 'bar', x:[], y:[], marker: {color: conf['color_1']}}
            }else if (type=='bar_histogram'){
                chartData[index] = { name: conf['name'], type: 'bar', x:[], y:[], marker: {color: []}}
            }else if (type=='candlestick'){
                chartData[index] = { 
                    name: conf['name'], type: 'candlestick', 
                    x:[], close:[], high:[], 
                    low:[], open:[], 
                    increasing: {line: {color: conf['color_3'], width:1}, fillcolor: conf['color_4']},
                    decreasing: {line: {color: conf['color_1'], width:1}, fillcolor: conf['color_2']},
                }
            }
        }
       
        let periodRow = null
        for(let coll in datas){
            let rows = datas[coll]
            for(let row of rows){
                let timestamp = moment(row['timestamp'], 'X').format()
                for(let field in row){
                    let id = coll + "_" + field
                    if(configIndex[id]){
                        for(let index of configIndex[id]){
                            chartData[index]['x'].push(timestamp)
                            let conf = this.chartConfig['configs'][index]
                            let type = get(conf['type'], 'line')
                            if(type == 'line'){
                                chartData[index]['y'].push(row[field])
                            }else if(type == 'bar'){
                                chartData[index]['y'].push(row[field])
                            }else if (type == 'bar_histogram'){
                                chartData[index]['y'].push(row[field])
                                if(periodRow === null){
                                    if(row[field] >= 0) chartData[index]['marker']['color'].push(conf['color_3'])
                                    else chartData[index]['marker']['color'].push(conf['color_1'])
                                }else{
                                    if(row[field] >= 0 && row[field] >= periodRow[field]) chartData[index]['marker']['color'].push(conf['color_3'])
                                    else if(row[field] >= 0 && row[field] < periodRow[field]) chartData[index]['marker']['color'].push(conf['color_4'])
                                    else if(row[field] < 0 && row[field] >= periodRow[field]) chartData[index]['marker']['color'].push(conf['color_2'])
                                    else if(row[field] < 0 && row[field] < periodRow[field]) chartData[index]['marker']['color'].push(conf['color_1'])
                                }
                            }else if(type == 'candlestick'){
                                chartData[index]['close'].push(row['close'])
                                chartData[index]['open'].push(row['open'])
                                chartData[index]['low'].push(row['low'])
                                chartData[index]['high'].push(row['high'])
                            }
                        }
                    }
                }

                periodRow = row
            }
        }
        //update to chart

        if(this.positionOpenData) chartData.push(this.positionOpenData)
        if(this.positionCloseData) chartData.push(this.positionCloseData)
        if(this.orderData) chartData.push(this.orderData)
        
        Plotly.newPlot(this.plot, chartData, this.config.layout).then(()=>{this.syncChart()})
        
        // for(let id in chartData){
        //     let data = chartData[id]
        //     Plotly.restyle(this.plot, data, [id])
        // }
        
    }


    getPosition(){
        const {startTime, stopTime} = this.props.parent.getTimeRange()
        if(startTime == '' || stopTime == '') return Promise.resolve();
        var account = this.props.parent.getAccount()
        if(account == '') return Promise.resolve();
        var symbol = this.chartConfig['symbol'];
        if(!symbol) return Promise.resolve();
        return this.model.getPosition(account, symbol, startTime * 1000, stopTime * 1000 , this.props.parent.mode).then(res => {
            if(res){
                return this.drawPosition(res)
            }
        })

    }

    drawPosition(data){
        const {startTime, stopTime} = this.props.parent.getTimeRange()
        this.positionOpenData = {
            x:[], 
            y:[], 
           
            name:"Position Open", 
            marker:{color:"red", size:8}, 
            mode:"markers+text",
            text:[],
            textposition:"top center",
            textfont:{
                color:"red",
            }
        }

        this.positionCloseData = {
            x:[], 
            y:[], 
            
            name:"Position Close", 
            marker:{color:"orange", size:8}, 
            mode:"markers+text",
            text:[],
            textposition:"top center",
            textfont:{
                color:"orange",
            }
        }

        this.orderData = {
            x:[], 
            y:[], 
            name:"Orders", 
            visible:'legendonly',
            marker:{color:[], size:8, symbol:'square'}, 
            mode:"markers+text",
            text:[],
            textposition:"top center",
            textfont:{
                color:"green",
            }
        }

        for(let position of data['position']){
            var timestampStart = moment(position[TESTNET_RESULT_CHART], 'x').format()
            this.positionOpenData.x.push(timestampStart)
            this.positionOpenData.y.push(position[TESTNET_RESULT_CHART_PRICE])
            this.positionOpenData.text.push(position[TESTNET_RESULT_TYPE] == TESTNET_RESULT_TYPE_LONG ? 'B' : 'S')
            if(position[TESTNET_RESULT_SELL_TIME] > 0 && position[TESTNET_RESULT_SELL_TIME] <= stopTime * 1000){
                var timestampStop = moment(position[TESTNET_RESULT_SELL_TIME], 'x').format()
                this.positionCloseData.x.push(timestampStop)
                this.positionCloseData.y.push(position[TESTNET_RESULT_SELL_PRICE])
                this.positionCloseData.text.push(position[TESTNET_RESULT_REAL_PNL] > 0 ? 'TP' : 'SL')
            }
        }

        for(let order of data['orders']){
            var timestampStart = moment(order[TESTNET_ORDER_TIME], 'x').format()
            this.orderData.x.push(timestampStart)
            this.orderData.y.push(order[TESTNET_ORDER_PRICE])
            this.orderData.text.push("<b>" + (order[TESTNET_ORDER_TYPE] == TESTNET_RESULT_TYPE_LONG ? 'B' : 'S') + '' + order[TESTNET_ORDER_PHASE] + "</b>")
            this.orderData.marker.color.push(order[TESTNET_ORDER_TYPE] == TESTNET_RESULT_TYPE_LONG ? 'green' : 'red')
        }

        // console.log(this.positionOpenData)


    }


    syncChart(){
        if(this.props.sync){
            this.props.sync.register(this.id, this)
            //sync hover
            this.plot.on('plotly_hover', (data)=>{
                // this.props.sync.updateHover(this.id, data.xvals[0])
                this.props.sync.updateHover(this.id, data.points[0].x)
            })

            this.plot.on('plotly_relayout', (data)=>{
                this.props.sync.updateScale(this.id, data)
            })
        }

        
    }

    render() {
        return <div className='box_padding box_shadow' ref={c => this.chartContainer = c} style={{position:'relative', margin:2, minHeight:50}}>
            <div className='box_flex' style={{position: 'absolute', zIndex:1}} >
                <div className='button' onClick={()=>{
                        this.chartConfigCom.modal()
                        this.chartConfigCom.setConfig(this.chartConfig)
                    }}><i className="fa fa-cog"></i>
                </div>
                &nbsp;
                <div className='button' onClick={()=>{
                        this.updateAllData()
                    }}><i className="fa fa-refresh"></i>
                </div>
                &nbsp;
                <div className='button' onClick={()=>{
                        this.chartCloneCom.modal()
                        this.chartCloneCom.setConfig(this.chartConfig)
                }}><i className="fa fa-clone"></i>
                </div>
                &nbsp;
                <div className='button' onClick={()=>{
                        this.chartConfig.hidden = !this.chartConfig.hidden
                        this.forceUpdate()
                }}><i className="fa fa-window-restore"></i>
                </div>
            </div>
            <div style={{display: (this.chartConfig.hidden ? 'none' : 'block')}} ref={c => this.plot = c} id={this.id} />
            <ChartConfig ref = {c => this.chartConfigCom = c} onApply={(config)=>{
                this.setChartConfig(config)
                this.updateLayout()
                this.updateAllData()
                localStorage.setItem(this.storageId, JSON.stringify(config))
                this.chartConfigCom.modal('hide')
            }}></ChartConfig>
            <ChartClone ref={c => this.chartCloneCom = c} onApply={(config)=>{
                this.setChartConfig(config)
                this.updateLayout()
                this.updateAllData()
                localStorage.setItem(this.storageId, JSON.stringify(config))
                this.chartCloneCom.modal('hide')
            }} onSetDefault={(config)=>{
                this.ctrl.set({[this.storageId]: JSON.stringify(config)}).then(res => {
                    if(res){
                        showLog('Configuration is set as Default', 'success')
                    }
                })
            }}></ChartClone>
            <Loading style={{position:'absolute'}} ref = {c => this.loading = c}></Loading>
        </div>
        
    }

    async componentDidMount() {
        Plotly.newPlot(this.plot, this.config.data, this.config.layout)
        this.resize_ob = new ResizeObserver((entries) => {
            if (this.resizeTimeOut) clearTimeout(this.resizeTimeOut)
            this.resizeTimeOut = setTimeout(() => {
                console.log('Resize')
                if(!this.chartConfig.hidden)
                    Plotly.Plots.resize(this.plot)
            })
        });
        this.resize_ob.observe(this.chartContainer);

        if(get(this.chartConfig['configs'], []).length == 0){
            
            this.ctrl.get(this.storageId).then(res => {
                
                if(res){
                    res = JSON.parse(res)
                    if(res){
                        this.setChartConfig(res)
                        this.updateAllData()
                    }
                       
                }
            })
        }

        
        await this.updateAllData()
    }

    componentWillUnmount(){
        if(this.props.sync){
            this.props.sync.unregister(this.id)
        }
    }

    hover(xval){
        if(xval === null){
            Plotly.relayout(this.plot, {
                shapes: [
                    { visible: false}
                ]
            })
        }else{
            if(this.plot.data.length == 0) return;
            var poins = []
            var x = Math.floor(moment(xval).valueOf() / (this.minTimeFrame * 60000)) * (this.minTimeFrame * 60000)
            x = moment(x).format()
            var index = this.plot.data[0]['x'].indexOf(x)
            if(index != -1){
                for (let curve in this.plot.data){
                    poins.push({curveNumber:curve, xval:index})
                }
                Plotly.Fx.hover(this.id, poins);
                Plotly.relayout(this.plot, {
                    shapes: [
                        {
                            type: 'line', xref: 'x', yref: 'paper',
                            x0:index, y0:0, x1:index, y1:1,
                            line: {
                                color: 'black',
                                width: 1,
                                dash: 'dot'
                            }
                        }
                    ]
                })
            }
            
        }
        
    }
}

export default ChartFlexItem
import React, { Component } from 'react';
import { Calendar } from 'primereact/calendar';
import { Dropdown } from 'primereact/dropdown';
import moment from 'moment'


// import { ThemeContext } from '../../AppWrapper';
import '../../assets/css/cus_css.scss'
import { Button } from 'primereact/button';
import { get } from '../../helpers/Default';
import Axios from 'axios';
import BacktestChart from '../../models/admin/BacktestChart';

class ChartView extends Component {

    constructor(props) {
        super(props);
        this.state = {
            dateSel: moment().toDate(),

            accountOptions: [],
            accountSelected: {},

            symbolOptions : [],
            symbolSelected : {},
            chartData: '',
            iframeHeigh: 1000

        }

        this.realTimeModel = new BacktestChart()

    }


    componentDidMount(){
        this.realTimeModel.getListAccount().then(res => {
            if(res){
                this.setState({
                    accountOptions: res,
                    accountSelected : res.length > 0 ? res[0]: {}
                })
            }
        }).then(()=>{
            return this.realTimeModel.getListSymbol().then(res => {
                if(res){
                    this.setState({
                        symbolOptions: res,
                        symbolSelected : res.length > 0 ? res[0]: {}
                    })
                }
            })
        }).then(()=>{
            this.updateIframe()
        })

        
    }

    changeAccount(e){
        this.setState({accountSelected: e.value}, ()=>this.updateIframe())
        
    }

    changeSymbol(e){
        this.setState({symbolSelected: e.value}, ()=>this.updateIframe())
       
    }

    updateChart(){
        var account = get(this.state.accountSelected['code'], null)
        var symbol = get(this.state.symbolSelected['code'], null)
        var date = moment(this.state.dateSel).format('YYYY_MM_DD')
        this.realTimeModel.updateChart(account, symbol, date).then(res => {
            this.updateIframe()
        })
    }
    getStatistic(){
        var account = get(this.state.accountSelected['code'], null)
        var symbol = get(this.state.symbolSelected['code'], null)
        this.realTimeModel.getStatistic(account, symbol).then(res => {
            window.open('/public/statistic/' + res)
        })
    }

    

    updateIframe(){

        var iframeHeigh = window.innerHeight - this.iframe.offsetTop

        var chartData = `<div style="text-align:center; padding:20px; font-size:18px; font-weight:bold; color:darkgray">Loading...</div>`
        this.setChartData(chartData)
        var account = get(this.state.accountSelected['code'], null)
        var symbol = get(this.state.symbolSelected['code'], null)
        var date = moment(this.state.dateSel).format('YYYY_MM_DD')
        var time = moment().format('x')
        if(account == null || symbol == null) return
        var chartName = `/public/plot/backtest_${account}_${symbol}_${date}.html?id=${time}`
        global.App.loading.loading(true, 'Loading...');
        return Axios.request({
			url: chartName,
			method: 'GET',
		})
			.then(response => {
				global.App.loading.loading(false)
                var chartData  = response['data']
                this.setState({
                    iframeHeigh: iframeHeigh,
                    chartData: chartName
                })
                // this.setChartData(chartData)
			})

			.catch((error) => {
				global.App.loading.loading(false)
                var chartData = `<div style="text-align:center; padding:20px; font-size:18px; font-weight:bold; color:darkgray">Chart is not available. Please click on Update button</div>`
                this.setChartData(chartData)
				return false;
			})
    }


    setChartData(data){
        // const container = window.document.getElementById('testnet_chart');
        // container.innerHTML = data; 
        this.setState({
            chartData: 'data:text/html;charset=utf-8,' + escape(data)
        })
    }
   

    render() {

        return (
            <div>
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom:5 }} >
                    <Dropdown className='mr-2' optionLabel="name" value={this.state.accountSelected} options={this.state.accountOptions} onChange={(e) => this.changeAccount(e)} />
                    <Dropdown className='mr-2' optionLabel="name" value={this.state.symbolSelected} options={this.state.symbolOptions} onChange={(e) => this.changeSymbol(e)} />
                    <Calendar className='mr-2' id="icon" value={this.state.dateSel} onChange={(e) => this.setState({ dateSel: e.value }, ()=>this.updateIframe())} showIcon />
                    <Button className='p-button-primary mr-2' onClick={e => this.getStatistic()}>Statistic</Button>
                    <Button className='p-button-primary mr-2' onClick={e => this.updateChart()}>Update</Button>
                    <Button className='p-button-warning' onClick={e => window.open(this.state.chartData)}>Full screen</Button>
                </div>
                
                <div style={{marginTop:5}} id="testnet_chart">
                    <iframe ref={c => this.iframe = c} width="100%" style={{width:'100%', height:this.state.iframeHeigh}} frameBorder="0" src={this.state.chartData}></iframe>
                </div>
                
                
            </div>
        );
    }


}

// ChartView.contextType = ThemeContext;
export default ChartView;
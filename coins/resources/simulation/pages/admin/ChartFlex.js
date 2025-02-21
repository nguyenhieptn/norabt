import React, { Component } from 'react'

import ChartFlexItem from '../../components/admin/ChartFlex/ChartFlexItem';
import ChartSync from '../../components/admin/ChartFlex/ChartSync';
import Input from '../../components/Input_v2/Input';
import ChartFelxModel from '../../model/admin/ChartFelxModel';

class ChartFlex extends Component {

	constructor(props) {
		super(props);
        this.id = 'ChartFlex'
        this.storageAccountKey = `${this.id}_account`
        this.storageStartTime = `${this.id}_startTime`
        this.storageTimeLength = `${this.id}_timeLength`
        this.chartSycn = new ChartSync()
        this.state = {
            account: App.parsed.account ?  Number(App.parsed.account) : localStorage.getItem(this.storageAccountKey) ? localStorage.getItem(this.storageAccountKey) : ''  ,
            timeLeng: localStorage.getItem(this.storageTimeLength) ? localStorage.getItem(this.storageTimeLength) : 2,
            startTime: App.parsed.time ?  Number(App.parsed.time) : localStorage.getItem(this.storageStartTime) ? localStorage.getItem(this.storageStartTime) : Number(moment().startOf('day').subtract(1, 'day').format('X')),
            account_options : [],
        }
    }

    componentDidMount(){
        let model = new ChartFelxModel()
        model.getLabAccounts().then(res => {
            if(res){
                this.setState({account_options: res})
            }
        })
    }

    getTimeRange(){
        let stopTime = Number(this.state.startTime) + Number(this.state.timeLeng) * 86400
        return {startTime : Number(this.state.startTime), stopTime}
    }

    getAccount(){
        return this.state.account;
    }

    render(){
        return <div>
            <div className='box_flex'>
                
                <Input className='input' DateFormat = {'DD/MM/YYYY'} type='date' Direct={true} value={this.state.startTime} placeholder="Start Time"  OnChange={(val) => {

                    val = Number(val)
                    localStorage.setItem(this.storageStartTime, val);
                    this.setState({startTime: val})
                }}></Input>
                &nbsp;
                <Input style={{width:50}} className='input' type='number' Direct={true} value={this.state.timeLeng} placeholder="Days" OnChange={(val) =>{
                    val = Number(val)
                    localStorage.setItem(this.storageTimeLength, val);
                    this.setState({timeLeng: val})
                }}></Input>
                &nbsp;
                <Input className='input' type="select" Direct={true} value={Number(this.state.account)} OnChange={(val)=> {localStorage.setItem(this.storageAccountKey, val); this.setState({account: val})}} Options={this.state.account_options}></Input>
                &nbsp;
                <div className='button btn btn-sm btn-info' onClick={()=>{
                    this.chartPrice.updateAllData()
                    this.chartFlex1.updateAllData()
                    this.chartFlex2.updateAllData()
                }}>Apply</div>
            </div>
            <ChartFlexItem ref={c => this.chartPrice = c} id="flex_chart_00" sync={this.chartSycn} parent = {this} isPosition={true}></ChartFlexItem>
            <ChartFlexItem ref={c => this.chartFlex1 = c} id="flex_chart_01" sync={this.chartSycn} parent = {this}></ChartFlexItem>
            <ChartFlexItem ref={c => this.chartFlex2 = c} id="flex_chart_02" sync={this.chartSycn} parent = {this}></ChartFlexItem>
        </div>
    }
}

export default ChartFlex
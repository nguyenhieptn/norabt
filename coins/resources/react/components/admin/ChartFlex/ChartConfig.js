import React, { Component } from 'react'
import Input from '../../../components/Input_v2/Input'
import ChartFelxModel from '../../../model/admin/ChartFelxModel';
import DragSort from '../../common/DragSort';
class ChartConfig extends Component {

	constructor(props) {
		super(props);
		this.id = makeId()
		this.state = {

			configs : [],
			symbol: '',
			title: '',
			database: '',
			height: 250,

			source_data_options : [],
			symbol_options: [],
			source_field_options : {},
			database_options : [
				// {value: 'backtest_data', label:'backtest_data'},
				// {value: 'backtest_data_1m', label:'backtest_data_1m'}
			],

			type_options : [
				{'value': '', 'label': ''},
				{'value': 'line', 'label': 'Line'},
				{'value': 'bar', 'label': 'Bar'},
				{'value': 'bar_histogram', 'label': 'Bar Histogram'},
				{'value': 'candlestick', 'label': 'Candle Stick'}
			],

			dash_options : [
				{'value': '', 'label': ''},
				{'value': 'solid', 'label': 'Solid'},
				{'value': 'dash', 'label': 'Dash'},
				{'value': 'dot', 'label': 'Dot'},
			],
			agg_optipons : [
				{'value': '', 'label': ''},
				{'value': 'sum', 'label': 'Sum'},
				{'value': 'max', 'label': 'Max'},
				{'value': 'min', 'label': 'Min'},
				{'value': 'first', 'label': 'First'},
				{'value': 'last', 'label': 'Last'},
			]
		}

		this.model = new ChartFelxModel()
	}


	onClickHandle() {
		if(this.props.onApply){
			this.props.onApply({
				title: this.state.title,
				symbol: this.state.symbol,
				height:this.state.height,
				configs:this.state.configs,
				database: this.state.database,
				
			})
		}
		
	}

	setConfig(config){
		let title = get(config['title'], '')
		let symbol = get(config['symbol'], '')
		let configs = get(config['configs'], [])
		let database = get(config['database'], 'backtest_data')
		let srcOption = {'': {value:'', label:'-- Select Source --'}}
		let fieldOption = {}
		let symbol_options = [{value:symbol, label:symbol}]

		for(let cfg of configs){
			srcOption[cfg['source_data']]={value: cfg['source_data'], label: cfg['source_data']}
			if(!fieldOption[cfg['source_data']]) fieldOption[cfg['source_data']] = {}
			fieldOption[cfg['source_data']][cfg['source_field']] = {value: cfg['source_field'], label: cfg['source_field']}
		}
		for(let src in fieldOption){
			fieldOption[src] = Object.values(fieldOption[src])
		}
		this.setState({
			configs, 
			title, 
			symbol,
			database, 
			height: get(config['height'], 250),
			source_data_options: Object.values(srcOption), 
			source_field_options: 
			fieldOption, 
			symbol_options,
			
		})
	}

	
	modal(cmd = 'show') {
		if (cmd == 'hide') {
			$("#edit_row_modal" + this.id).modal('hide');
		} else {
			$("#edit_row_modal" + this.id).modal();
			this.model.getDatabase().then(res => {
				if(res){
					this.setState({database_options: res})
				}
			})
		}
	}

	changeOrder(src_id, des_id) {
        src_id = Number(src_id)
        des_id = Number(des_id)
        var variables = this.state.configs
        if (src_id > des_id) {
            variables.splice(des_id, 0, variables[src_id])
            variables.splice(src_id + 1, 1)
        }
        if (des_id > src_id) {
            variables.splice(des_id + 1, 0, variables[src_id])
            variables.splice(src_id, 1)
        }
        this.setState({
            variables
        })
    }

	render() {

		let configs = this.state.configs
		
		return (
			<div className="modal fade" id={"edit_row_modal" + this.id} onClick={() => { addClass($('body')[0], 'modal-open') }}>
				<div className="modal-dialog modal-lg modal-dialog-centered" style={{maxWidth:'90%'}}>
					<div className="modal-content">

						<div className="modal-header">
							<h4 className="modal-title">{this.state.title}</h4>
							<button type="button" className="close" data-dismiss="modal">&times;</button>
						</div>

						<div className="modal-body" style={{ textAlign: 'initial' }}>

							<div className='box_flex' style={{padding:2}}>
								<div style={{flex:5}}>Title:</div>
								<div style={{flex:5}}>
									<Input className="input" type="text" Direct = {true} Options = {this.state.symbol_options} value={this.state.title} OnChange={(value, obj)=>{
											let update = {title: value}
											this.setState(update)
									}}></Input>
								</div>
							</div>

							<div className='box_flex' style={{padding:2}}>
								<div style={{flex:5}}>Height:</div>
								<div style={{flex:5}}>
									<Input className="input" type="number" Direct = {true} value={this.state.height} OnChange={(value, obj)=>{
											let update = {height: value}
											this.setState(update)
									}}></Input>
								</div>
							</div>

							<div className='box_flex' style={{padding:2}}>
								<div style={{flex:5}}>Symbol:</div>
								<div style={{flex:5}}>
									<Input className="input" type="select" Direct = {true} Options = {this.state.symbol_options} value={this.state.symbol} OnChange={(value, obj)=>{
											let update = {symbol: value}
											if(this.state.title == '')
												update['title'] = value
											else
												update['title'] = this.state.title.replace(this.state.symbol, value)
											this.setState(update)
										}} onClick = {()=>{
											this.model.getWatchlist().then(res => {
												res ? this.setState({symbol_options: res}) : this.setState({symbol_options: []})
										})
									}}></Input>
								</div>
							</div>

							<div className='box_flex' style={{padding:2}}>
								<div style={{flex:5}}>Database:</div>
								<div style={{flex:5}}>
									<Input className="input" type="select" Direct = {true} Options = {this.state.database_options} value={this.state.database} OnChange={(value, obj)=>{
											let update = {database: value}
											this.setState(update)
									}}></Input>
								</div>
							</div>

							<hr/>

							<div className='box_flex'>
								<div style={{flex: 5, padding:2, textAlign:'center', fontWeight:'bold'}}>Source</div>
								<div style={{flex: 5, padding:2, textAlign:'center', fontWeight:'bold'}}>Field</div>
								<div style={{flex: 5, padding:2, textAlign:'center', fontWeight:'bold'}}>Name</div>
								<div style={{flex: 2, padding:2, textAlign:'center', fontWeight:'bold'}}>Frame(m)</div>
								<div style={{flex: 2, padding:2, textAlign:'center', fontWeight:'bold'}}>Agg</div>
								<div style={{flex: 2, padding:2, textAlign:'center', fontWeight:'bold'}}>Type</div>
								<div style={{flex: 2, padding:2, textAlign:'center', fontWeight:'bold'}}>Dash</div>
								<div style={{flex: 2, padding:2, textAlign:'center', fontWeight:'bold'}}>Color 1</div>
								<div style={{flex: 2, padding:2, textAlign:'center', fontWeight:'bold'}}>Color 2</div>
								<div style={{flex: 2, padding:2, textAlign:'center', fontWeight:'bold'}}>Color 3</div>
								<div style={{flex: 2, padding:2, textAlign:'center', fontWeight:'bold'}}>Color 4</div>
								<div style={{flex: 1, padding:2, textAlign:'center', fontWeight:'bold'}}>Delete</div>
							</div>

							{configs.map((item, key) => {
								return <DragSort key={key} style={{ textAlign: 'center' }} changeOrder={(src_id, des_id) => { this.changeOrder(src_id, des_id) }} src_weight={key} src_id={key} icon={false}>
								<div className='box_flex'>
									<div style={{width:0, flex: 5, padding:2}}>
										<Input className="input" type="select" Direct = {true} Options = {this.state.source_data_options} value={item['source_data']} OnChange={(value, obj)=>{
											item['source_data'] = value
											let matched = /candle_(\d*\w*)/gm.exec(value)
											if(matched){
												item['timeframe'] = Math.floor(interval2second(matched[1])/60)
											}
											this.setState({configs})
										}} onClick = {()=>{
											this.model.getSourceOptions(this.state.database).then(res => {
												res ? this.setState({source_data_options: res}) : this.setState({source_data_options: []})
											})
										}}></Input>
									</div>
									<div style={{width:0, flex: 5, padding:2}}>
										<Input className="input" type="select" Direct = {true} Options = {this.state.source_field_options[item['source_data']]} value={item['source_field']} OnChange={(value, obj)=>{
											item['source_field'] = value
											item['name'] = value
											let matched = /^([a-zA-Z]*)_([a-zA-Z\d]+)_(\d+)_(\d+)/gm.exec(value)
											if(matched){
												item['timeframe'] = Math.floor(matched[4])
											}
											this.setState({configs})
										}} onClick = {()=>{
											this.model.getChartField(this.state.database, item['source_data']).then(res => {
												if(res){
													this.state.source_field_options[item['source_data']] = res
												}else{
													this.state.source_field_options[item['source_data']] = []
												}
												this.setState({source_field_options: this.state.source_field_options})
											})
										}}></Input>
									</div>
									<div style={{width:0, flex: 5, padding:2}}>
										<Input className="input" type="text" Direct = {true} value={item['name']} OnChange={(value, obj)=>{
											item['name'] = value
											this.setState({configs})
										}}></Input>
									</div>
									<div style={{width:0, flex: 2, padding:2}}>
										<Input className="input" type="number" Direct = {true} Options = {this.state.type_options} value={item['timeframe']} OnChange={(value, obj)=>{
											item['timeframe'] = value
											this.setState({configs})
										}}></Input>
									</div>
									<div style={{width:0, flex: 2, padding:2}}>
										<Input  className="input" type="select" Direct = {true} Options = {this.state.agg_optipons} value={item['agg']} OnChange={(value, obj)=>{
											item['agg'] = value
											this.setState({configs})
										}}></Input>
									</div>
									<div style={{width:0, flex: 2, padding:2}}>
										<Input className="input" type="select" Direct = {true} Options = {this.state.type_options} value={item['type']} OnChange={(value, obj)=>{
											item['type'] = value
											if(value == 'bar_histogram' || value == 'candlestick'){
												item['color_1'] = '#ff004c'
												item['color_2'] = '#ffc6d1'
												item['color_3'] = '#00af9b'
												item['color_4'] = '#9fe4dc'
											}else{
												item['color_1'] = '#' + Math.random().toString(16).slice(-6)
											}
											if(value == 'candlestick'){
												item['source_field'] = 'close'
											}
											
											this.setState({configs})
										}}></Input>
									</div>
									<div style={{width:0, flex: 2, padding:2}}>
										<Input disabled={item['type'] != 'line'} className="input" type="select" Direct = {true} Options = {this.state.dash_options} value={item['dash']} OnChange={(value, obj)=>{
											item['dash'] = value
											this.setState({configs})
										}}></Input>
									</div>
									<div style={{width:0, flex: 2, fontSize:8, padding:2}}>
										<Input className="input" type="color" Direct = {true} value={item['color_1']} OnChange={(value, obj)=>{
											console.log(value)
											item['color_1'] = value
											this.setState({configs})
										}}></Input>
									</div>
									<div style={{width:0, flex: 2, fontSize:8, padding:2}}>
										<Input className="input" type="color" Direct = {true} value={item['color_2']} OnChange={(value, obj)=>{
											item['color_2'] = value
											this.setState({configs})
										}}></Input>
									</div>
									<div style={{width:0, flex: 2, fontSize:8, padding:2}}>
										<Input className="input" type="color" Direct = {true} value={item['color_3']} OnChange={(value, obj)=>{
											item['color_3'] = value
											this.setState({configs})
										}}></Input>
									</div>
									<div style={{width:0, flex: 2, fontSize:8, padding:2}}>
										<Input className="input" type="color" Direct = {true} value={item['color_4']} OnChange={(value, obj)=>{
											item['color_4'] = value
											this.setState({configs})
										}}></Input>
									</div>
									<div style={{width:0, flex: 1, padding:2, fontWeight:'bold', fontSize:24, textAlign:'center'}} className='button' onClick={()=>{
										configs.splice(key, 1)
										this.setState({configs})
									}}>&times;</div>
								</div>
								</DragSort>
							})}

							
						</div>

						<div className="modal-footer">
							{isset(this.props.extraFunction) ? this.props.extraFunction : ''}
							<button type="button" className="btn btn-primary" onClick={() => { 
								configs.push({
									'source_data': '',
									'source_field': '',
									'name': '',
									'type': '',
									'dash': '',
									'agg': 'last',
									'timeframe':'',
									'color_1': '',
									'color_2': '',
									'color_3': '',
									'color_4': ''
								})
								this.setState({configs})
							}}>{lang('Add')}</button>
							<button type="button" className="btn btn-warning" onClick={() => { this.onClickHandle(1) }}>{lang('Apply')}</button>
							<button type="button" className="btn btn-danger" data-dismiss="modal">{lang('Close')}</button>
						</div>

					</div>
				</div>
			</div>
		)
	}
}
export default ChartConfig

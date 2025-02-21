import React, { Component } from 'react'
import Style from '../common/Style';
import InputParent from './InputParent';
class InputRadios extends InputParent {
	
	constructor(props) {
	    super(props);
	}

	onChangeHandle(event, value){
		var checked = event.target.checked;
		if(!checked) return;
		if(!this.props.Direct){
			this.setState({value: value}, ()=>{
				if(this.props.OnChange) this.props.OnChange(value, this);
				if(this.props.onChange) this.props.onChange(event);
				if(this.loadSuggest) this.loadSuggest()
			})
		}else{
			if(this.props.onChange) this.props.onChange(event);
			if(this.props.OnChange){
				if(this.DecoratorOut) value = this.DecoratorOut(value, this);
				this.props.OnChange(value, this);
			}
		}
		
	}
	
	drawOptions(){

		if(this.props.Direct){
			var val = this.props.value;
			if(this.DecoratorIn) val = this.DecoratorIn(val, this);
		}else{
			var val = this.state.value;
		}

		var optionHtml = [];
		for(let i in this.options){
			optionHtml.push(<div key={i}>
				<label className='box_flex'>	
					<input className='checkboxs_input' 
					type="radio" 
					checked={val==i} 
					onChange={(event)=>{this.onChangeHandle(event, i)}} 
					{...this.rent}/>
					<span title={this.options[i]} className='checkboxs_text'>{this.options[i]}</span>
				</label>
				</div>) ;
			this.revert[this.options[i]] = i;
		}
		return optionHtml;
	}
	
	render(){
		this.initial();
		
		return(
				<>
				<Style id='input_checks_css'>{`
					.checkboxs{
						display: flex;
						flex-wrap: wrap;
					}
					.checkboxs_item {
					    display: flex;
					    align-items: center;
						padding: 5px;
						margin-bottom: 0px;
					}
					.checkboxs_text{
						width: 150px;
				    	font-weight: normal;
						white-space: nowrap;
						text-overflow: ellipsis;
						overflow:hidden;
						padding-left: 5px;
					}
					
				`}</Style>
				<div className="checkboxs">
					{this.drawOptions()}
				</div>
				</>
		)
	}
}

export default InputRadios;
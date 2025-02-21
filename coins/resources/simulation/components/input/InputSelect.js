import React, { Component } from 'react'

class InputSelect extends Component {
	
	constructor(props) {
	    super(props);
	    
	    this.initial();
	    
	    this.state = {
	    	value: get(this.props.value, '')
	    }
	    this.revert = {};
	}
	
	initial(){
		var {id, value, decoratorOut, decoratorIn, options, onChange,sort, ...rent} = this.props;
		this.id = get(id, '');
		this.onChange = get(onChange, ()=>{});
	    this.decoratorOut = get(decoratorOut, null);
	    this.decoratorIn = get(decoratorIn, null);
	    this.options = get(options, []);
		
	    this.rent = rent;
	}
	
	setValue(value){
		if(isset(this.decoratorIn)) value = this.decoratorIn(value);
		if(value === null) value = '';
		
		this.setState({value: value});
	}
	
	getValue(){
		var value = this.state.value;
		if(isset(this.decoratorOut)) value = this.decoratorOut(value);
		if(value === 'true') value = true;
		if(value === 'false') value = false;
		return value;
	}
	
	revertValue(value){
		//Using for import
		if(isset(this.decoratorOut)) value = this.decoratorOut(value);
		if(isset(this.revert[value])) return this.revert[value];
		return '';
	}
	
	getInput(){
		return this.input;
	}
	
	drawOptions(){
		
		var optionHtml = [];
		this.revert = {}
		for(let i in this.options){
			this.revert[this.options[i]] = i;
			
		}
		var values 
		if(this.props.sort === false){

			if (Object.values(this.revert).indexOf('') == -1) {
				this.revert['All'] = ''
			}
			
			values = Object.keys(this.revert);
			values = values.reverse()
		}else{
			values = Object.keys(this.revert).sort();
		}
	
	
		if(isset(this.revert['All'])) {
			optionHtml.push(<option key={this.revert['All']} value={this.revert['All']}>{'All'}</option>) ;
		}
		for(let i of values){
			i != 'All' && optionHtml.push(<option key={this.revert[i]} value={this.revert[i]}>{i}</option>) ;
		}
	
		return optionHtml;
	}
	
	render(){
		this.initial();
		
		
		return(
				<select
					value={this.state.value} 
					onChange={function(event){this.setState({'value': event.target.value}, (event)=>{this.onChange(event, this.getValue())})}.bind(this)}
					ref = {input => this.input = input}
					{...this.rent}
				>
				{this.drawOptions()}
				</select>
		)
	}
}

export default InputSelect;
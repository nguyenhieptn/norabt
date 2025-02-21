import React, { Component } from 'react'

class InputText extends Component {
	
	constructor(props) {
	    super(props);
	    
	    this.initial();
	    
	    this.state = {
	    	value: ''
	    }
	    
	}
	
	initial(){
		var {id, value, decoratorOut, decoratorIn, onChange, ...rent} = this.props;
		this.id = get(id, '');
		this.onChange = get(onChange, ()=>{})
	    this.decoratorOut = get(decoratorOut, null);
	    this.decoratorIn = get(decoratorIn, null);
	    this.rent = rent;
	}
	
	setValue(value){
		
		if(isset(this.decoratorIn)) value = this.decoratorIn(value);
		if(value == null) value = '';
		this.setState({value: value});
	}
	
	getValue(){
		var value = this.state.value;
		if(isset(this.decoratorOut)) value = this.decoratorOut(value);
		return value;
	}
	
	revertValue(value){
		if(isset(this.decoratorOut)) value = this.decoratorOut(value);
		return value;
	}
	
	getInput(){
		return this.input;
	}
	
	render(){
		this.initial();
		return(
				<textarea
					value={this.state.value} 
					onChange={function(event){this.setState({'value': event.target.value}, ()=>{this.onChange()})}.bind(this)} 
					ref = {input => this.input = input}
					{...this.rent}
				>
				</textarea>
		)
	}

	componentDidMount(){
		if(isset(this.props.value)){
			this.setValue(this.props.value);
		}
	}
}

export default InputText;
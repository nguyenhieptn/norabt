import React, { Component } from 'react'

/**
 * props
 * - Direct: true/false
 * - DecoratorIn : (value, this) => {}
 * - DecoratorOut : (value, this) => {}
 * - OnChange : (value, this) => {}
 * - DefaultValue : default value
 * - Options: an object
 * - OnChangeBlur: (value, this)=>{} Onchange and value is modified
 */

class InputParent extends Component {

	constructor(props) {
	    super(props);
	    
	    this.state = {
	    	value: get(this.props.DefaultValue, ''),
	    }

		this.id = makeId();
		this.oldValue = get(this.props.DefaultValue, '');
		this.revert = {};
		this.rent = {};
		
	}

	initial() {

		this.rent = {}
		for(let key in this.props){
			if(key[0] == key[0].toUpperCase()){
				this[key] = this.props[key]
			}else{
				if(key == 'value') continue
				this.rent[key] = this.props[key]
			}
		}
		this.makeDecorator()

		// var {
		// 	value,
		// 	Direct,
		// 	DecoratorIn,
		// 	DecoratorOut,
		// 	OnChange,
		// 	Suggest,
		// 	DefaultValue,
		// 	Options,
		// 	OnChangeBlur,
		// 	...rent
		// } = this.props;

		// this.rent = rent;
	}

	makeDecorator(){
		this.DecoratorIn = this.props.DecoratorIn ? this.props.DecoratorIn : null
		this.DecoratorOut = this.props.DecoratorOut ? this.props.DecoratorOut: null
	}
	
	setValue(value){
		// Set value for undirect mode
		if(this.DecoratorIn) value = this.DecoratorIn(value, this);
		if(value == null) value = '';
		this.oldValue = value;
		this.setState({value: value});
	}
	
	getValue(){
		// Get value for undirect mode
		var value = this.state.value;
		if(this.DecoratorOut) value = this.DecoratorOut(value, this);
		if(isset(this.revert[value])) value = this.revert[value];
		return value;
	}

	showValue(){
		// Value to show on dom
		if(this.props.Direct){
			var val = get(this.props.value, '');
			if(this.DecoratorIn) val = this.DecoratorIn(val, this);
		}else{
			var val = this.state.value;
		}
		return val
	}
	
	revertValue(value){
		// convert value to option key
		if(this.DecoratorOut) value = this.DecoratorOut(value, this);
		if(isset(this.revert[value])) value = this.revert[value];
		return value;
	}

	onChangeHandle(event){
		var val = event.target.value;
		
		if(!this.props.Direct){
			this.setState({'value': event.target.value}, ()=>{
				if(this.props.OnChange) this.props.OnChange(val, this);
				if(this.loadSuggest) this.loadSuggest()
			})
		}else{
			if(this.props.OnChange){
				if(this.DecoratorOut) val = this.DecoratorOut(val, this);
				this.props.OnChange(val, this);
			}
		}
		
	}
	
}

export default InputParent;
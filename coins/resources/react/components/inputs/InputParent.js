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
		var {
			value,
			Direct,
			DecoratorIn,
			DecoratorOut,
			OnChange,
			Suggest,
			DefaultValue,
			Options,
			OnChangeBlur,
			...rent
		} = this.props;

		this.rent = rent;
	}
	
	setValue(value){
		if(this.props.DecoratorIn) value = this.props.DecoratorIn(value, this);
		if(value == null) value = '';
		this.oldValue = value;
		this.setState({value: value});
	}
	
	getValue(){
		var value = this.state.value;
		if(this.props.DecoratorOut) value = this.props.DecoratorOut(value, this);
		if(isset(this.revert[value])) value = this.revert[value];
		return value;
	}
	
	revertValue(value){
		if(this.props.DecoratorOut) value = this.props.DecoratorOut(value, this);
		if(isset(this.revert[value])) value = this.revert[value];
		return value;
	}

	onChangeHandle(event){
		var val = event.target.value;
		
		if(!this.props.Direct){
			this.setState({'value': event.target.value}, ()=>{
				if(this.props.OnChange) this.props.OnChange(val, this);
				if(this.props.onChange) this.props.onChange(event);
				if(this.loadSuggest) this.loadSuggest()
			})
		}else{
			if(this.props.onChange) this.props.onChange(event);
			if(this.props.OnChange){
				if(this.props.DecoratorOut) val = this.props.DecoratorOut(val, this);
				this.props.OnChange(val, this);
			}
		}
		
	}
	
}

export default InputParent;
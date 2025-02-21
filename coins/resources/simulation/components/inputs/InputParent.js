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

		this.makeDecorator();
	    let defautValue = get(this.props.DefaultValue, '');
		if(this.DecoratorIn) defautValue = this.DecoratorIn(defautValue, this);
	    this.state = {
	    	value: defautValue,
	    }

		this.id = makeId();
		this.oldValue = defautValue;
		this.revert = {};
		this.rent = {};
		
	}

	initial(){
		this.makeProps();
		this.makeDecorator();
	}

	makeProps() {
		for(let key in this.props){
			if(key[0] == key[0].toUpperCase()){
				this[key] = this.props[key]
			}else{
				if(key == 'value') continue
				this.rent[key] = this.props[key]
			}
		}
	}

	makeDecorator(){
		this.DecoratorIn = this.props.DecoratorIn;
		this.DecoratorOut = this.props.DecoratorOut;
	}
	
	setValue(value){
		if(this.DecoratorIn) value = this.DecoratorIn(value, this);
		if(value == null) value = '';
		this.oldValue = value;
		this.setState({value: value});
	}
	
	getValue(){
		var value = this.state.value;
		if(this.DecoratorOut) value = this.DecoratorOut(value, this);
		if(isset(this.revert[value])) value = this.revert[value];
		return value;
	}
	
	revertValue(value){
		if(this.DecoratorOut) value = this.DecoratorOut(value, this);
		if(isset(this.revert[value])) value = this.revert[value];
		return value;
	}

	onBlurHandle(event){
		let val = event.target.value;
		if(val != this.oldValue){
			if(this.props.OnChangeBlur){
				this.oldValue = val;
				if(this.DecoratorOut) val = this.DecoratorOut(val, this);
				this.props.OnChangeBlur(val, this)
			}
		}
	}

	onChangeHandle(event){
		
		let val = event.target.value;
		
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
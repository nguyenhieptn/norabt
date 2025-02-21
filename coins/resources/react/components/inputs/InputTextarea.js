import React, { Component } from 'react'
import InputParent from './InputParent';

/**
 * props
 * - Direct: true/false
 * - DecoratorIn : (value, this) => {}
 * - DecoratorOut : (value, this) => {}
 * - OnChange : (value, this) => {}
 * - Suggest : an URL
 * - DefaultValue : default value
 * - Options: an object
 */

class InputTextarea extends InputParent {
	
	constructor(props) {
	    super(props);
	}
	
	initial(){
		var {
			value, 
			DefaultValue, 
			DecoratorOut, 
			DecoratorIn, 
			OnChange, 
			Options, 
			Direct,
			...rent
		} = this.props;
		
	    this.rent = rent;
	}
	
	

	onBlurHandle(event){
		if(this.props.onBlur) this.props.onBlur(event);
		let val = event.target.value;
		if(val != this.oldValue){
			if(this.props.OnChangeBlur){
				this.oldValue = val;
				this.props.OnChangeBlur(val, this)
			}
		}
	}
	
	
	render(){

		this.initial();
		
		if(this.props.Direct){
			var val = this.props.value;
			if(this.props.DecoratorIn) val = this.props.DecoratorIn(val, this);
		}else{
			var val = this.state.value;
		}
		
		return(
				<div style={{display:'flex'}}>
					<textarea
						value={val} 
						onChange={(event)=>{this.onChangeHandle(event)}}
						onBlur = {event => this.onBlurHandle(event)}
						ref = {input => this.input = input}
						{...this.rent}
					/>
            	</div>
		)
	}
}

export default InputTextarea;
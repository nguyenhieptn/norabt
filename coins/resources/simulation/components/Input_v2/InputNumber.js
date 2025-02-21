import React, { Component } from 'react'
import InputParent from './InputParent';

/**
 * props
 * - Direct: true/false
 * - DecoratorIn : (value, this) => {}
 * - DecoratorOut : (value, this) => {}
 * - OnChange : (value, this) => {}
 * - DefaultValue : default value
 * - OnChangeBlur: (value, this)=>{} Onchange and value is modified
 */

class InputNumber extends InputParent {
	
	constructor(props) {
	    super(props);
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
		
		var val = this.showValue()
		
		return(
				<div style={{display:'flex'}}>
					<input
						value={val} 
						onChange={(event)=>{this.onChangeHandle(event)}}
						onBlur={event => this.onBlurHandle(event)}
						ref = {input => this.input = input}
						{...this.rent}
						type = "number"
					/>
            	</div>
		)
	}
}

export default InputNumber;
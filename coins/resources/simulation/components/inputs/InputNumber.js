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
	

	render(){

		this.initial();
		
		if(this.props.Direct){
			var val = this.props.value;
			if(this.DecoratorIn) val = this.DecoratorIn(val, this);
		}else{
			var val = this.state.value;
		}
		
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
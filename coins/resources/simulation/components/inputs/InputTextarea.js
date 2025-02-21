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
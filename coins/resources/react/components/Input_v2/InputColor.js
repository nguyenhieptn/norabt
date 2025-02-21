import { unset } from 'lodash';
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

class InputColor extends InputParent {
	
	constructor(props) {
	    super(props);
		this.id = 'input' + makeId()
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
		this.rent['style'] = {background: val, fontSize:10, fontWeight:'bold', textShadow: '-1px 0 white, 0 1px white, 1px 0 white, 0 -1px white', ...this.rent['style']}
		
		return(
				<div style={{display:'flex', position:'relative'}}>
					<input
						value={val} 
						onChange={(event)=>{this.onChangeHandle(event)}}
						onBlur={event => this.onBlurHandle(event)}
						ref = {input => this.input = input}
						style={{visibility:'hidden', width:0}}
						type = "color"
					/>
					<input type="text" onChange={(event)=>{this.onChangeHandle(event)}}
				  	  value = {val}
					  {...this.rent}
					  onClick={()=>{this.input.click()}}
				  	></input>
            	</div>
		)
	}
}

export default InputColor;
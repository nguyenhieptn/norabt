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

class InputMultiSelect extends InputParent {

	constructor(props) {
		super(props);
	}

	
	onChangeHandle(key, selected) {
		
		if (!this.props.Direct) {
			var value = this.showValue();
			var index = value.indexOf(key);
			if (index > -1 && !selected) {
				value.splice(index, 1);
			}
			if(index == -1 && selected){
				value.push(key)
			}
			this.setState({value},() => {
				if (this.props.OnChange) this.props.OnChange(value, this);
			});

		} else {

			if (this.props.OnChange) {

				var value = this.showValue();
				if(this.props.DecoratorIn) value = this.props.DecoratorIn(value, this);

				var index = value.indexOf(key);
				if (index > -1 && !selected) {
					value.splice(index, 1);
				}

				if(index == -1 && selected){
					value.push(key)
				}

				if (this.props.DecoratorOut) value = this.props.DecoratorOut(value, this);
				this.props.OnChange(value, this);
			}
		}

	}
	
	drawOptions(inputValue){

		var optionHtml = [];
		this.revert = {};
		
		if(this.props.Options){
			for (let option of this.props.Options) {
				this.revert[option['label']] = option['value'];
				optionHtml.push(<div key={option['value']} className="dropdown-item">
					<label style={{display:'flex', textAlign:'center'}}>
						<input checked={inputValue.includes(option['value'])} onChange={(event)=>{
							this.onChangeHandle(option['value'], event.target.checked);
						}} type="checkbox"/>&nbsp;{option['label']}
					</label>
				</div>) ;
			}
		}
		
		return optionHtml;

	}

	showValue(){
		let val = super.showValue()
		if(val == '' || !isset(val)) val = []
		return val
	}

	
	render(){
		this.initial();

		var val = this.showValue()
		
		
		return(
				<div className="dropdown" style={{width:'100%'}}>
				  <div className="input" data-toggle="dropdown" aria-haspopup="true" style={{cursor:'pointer'}} {...this.rent}>
				  	&nbsp;{val.join(', ')}
				  </div>
				  <div className="dropdown-menu" style={{maxHeight: 500, overflow: 'auto'}}>
				  	{this.drawOptions(val)}
				    
				  </div>
				</div>
		)
	}
}

export default InputMultiSelect;
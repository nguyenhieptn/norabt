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
			var value = this.state.value;
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

				var value = this.props.value;
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
			for (let i in this.props.Options) {
				this.revert[this.props.Options[i]] = i;
			}

			var values = Object.keys(this.revert).sort();
	
			for (let value of values) {
				let key = this.revert[value];
				optionHtml.push(<div key={key} className="dropdown-item">
					<label style={{display:'flex', textAlign:'center'}}>
						<input checked={inputValue.includes(key)} onChange={(event)=>{
							this.onChangeHandle(key, event.target.checked);
						}} type="checkbox"/>&nbsp;{value}
					</label>
				</div>) ;
			}
		}
		
		return optionHtml;

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
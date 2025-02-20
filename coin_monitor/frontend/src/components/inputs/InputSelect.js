import React from 'react'
import { get } from '../../helpers/Default';
import InputParent from './InputParent';

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
class InputSelect extends InputParent {

	constructor(props) {
		super(props);
	}


	drawOptions(val) {
		var optionHtml = [];
		this.revert = {};
		if(this.props.Options){
			for (let option of this.props.Options) {
				this.revert[option['label']] = option['value'];
				optionHtml.push(<option key={option['value']} value={option['value']} disabled={get(option['disabled'], false)}>{option['label']}</option>);
			}
		}
		
		return optionHtml;
	}

	render() {

		this.initial();

		var val = this.showValue()

		return (
			<select
				value={val}
				onChange={(event) => { this.onChangeHandle(event) }}
				ref={input => this.input = input}
				{...this.rent}
			>
				{this.drawOptions(val)}
			</select>

		)
	}
}

export default InputSelect;
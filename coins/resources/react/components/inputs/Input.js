import React, { Component } from 'react'
import InputText from './InputText'
import InputNumber from './InputNumber';
import ToolTip from '../common/Tooltip';
import InputTextarea from './InputTextarea';
import InputSelect from './InputSelect';
import InputMultiSelect from './InputMultiSelect';


/**
 * props
 * - Direct: true/false
 * - DecoratorIn : (value, this) => {}
 * - DecoratorOut : (value, this) => {}
 * - OnChange : (value, this) => {}
 * - Suggest : an URL
 * - DefaultValue : default value
 * - Options: an object
 * - Type: type of input text/number
 * - Nullable: can be null or not
 * - Validate: verify data regex
 */

class Input extends Component {

	constructor(props) {
		super(props);
		this.id = "input" + makeId();
	}

	initial() {
		var { 
			type, 
			style, 
			Nullable,
			Validate,
			...rent } = this.props;
		this.rent = rent;
	}

	setValue(value) {
		if (value===null) value = '';
		return this.input.setValue(value);
	}

	getValue() {
		var value = this.input.getValue();
		if (!this.validate(value)) return null;
		return value;
	}

	validate(value = null) {
		if (value === null) value = this.input.getValue();
		this.tooltip.set(false, '');
		if (this.props.Nullable === false) {
			if (value === '' || value === null) {
				this.tooltip.set(true, lang('Please fill out this field'));
				return false;
			}

		} else {
			if (value == '') {
				return true;
			}
		}

		if (this.props.Validate == 'email') {
			if (!/^[\w\d\.\-\+\_]+\@[\w\d\.\-\+\_]+$/.test(value)) {
				this.tooltip.set(true, lang('This field\'s value must be an Email'));
				return false;
			} else {
				return true;
			}
		}

		if (this.props.Validate == 'phone') {
			if (!/[+\d]{10,11}/.test(value)) {
				this.tooltip.set(true, lang('This field\'s value must be a Phone Number'));
				return false;
			} else {
				return true;
			}
		}

		if (this.props.Validate && this.props.Validate.test) {
			if (!this.props.Validate.test(value)) {
				this.tooltip.set(true, lang('Value must satisfy regex ' + this.props.Validate));
				return false;
			} else {
				return true;
			}
		}

		if (typeof this.props.Validate == 'function') {
			var result = this.props.Validate(value)
			if (result === true) return true;
			this.tooltip.set(true, lang(result));
			return false;
		}


		return true;
	}

	drawInput() {

		switch (this.props.type) {

			case 'text':

				return (
					<InputText
						style={{width: '100%', ...this.props.style}}
						ref={input => { this.input = input }}
						{...this.rent}
						
					>
					</InputText>

				);
				break;

			case 'number':

				return (
					<InputNumber
						style={{width: '100%', ...this.props.style}}
						ref={input => { this.input = input }}
						{...this.rent}
					>
					</InputNumber>
				);
				break;
			case 'select':

				return (
					<InputSelect
						style={{width: '100%', ...this.props.style}}
						ref={input => { this.input = input }}
						{...this.rent}
					>
					</InputSelect>
				);
				break;
			case 'multiselect':

				return (
					<InputMultiSelect
						style={{width: '100%', ...this.props.style}}
						ref={input => { this.input = input }}
						{...this.rent}
					>
					</InputMultiSelect>
				);
				break;
			case 'textarea':
				return (
					<InputTextarea
						style={{width: '100%', ...this.props.style}}
						ref={input => { this.input = input }}
						onBlur={event => {this.onBlurHandle(event)}}
						{...this.rent}
					>
					</InputTextarea>
				);
				break;
			default: 
				return (
					<InputText
						style={{width: '100%', ...this.props.style}}
						ref={input => { this.input = input }}
						onBlur={event => {this.onBlurHandle(event)}}
						type = {this.props.type}
						{...this.rent}
					>
					</InputText>
				)
			
		}
	}

	render() {
		this.initial();
		return <div style={{ position: 'relative' }}>
				<ToolTip ref={tooltip => this.tooltip = tooltip}></ToolTip>
				{this.drawInput()}
			</div>

	}
}

export default Input;
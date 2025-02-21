import React, { Component } from 'react'
import Input from './Input'
import(/* webpackMode: "eager" */ './responsive/input.scss')

class FormInput extends Component {

	constructor(props) {
		super(props);

		this.items = {};
		this.initial();
	}

	initial() {
		this.id = get(this.props.id, '');
	}

	getValue() {
		let values = {};
		for (let i in this.props.struct) {
			if (!this.items[i].validate()) return null
			values[i] = this.items[i].getValue();
		}
		return values;
	}

	setValue(values) {

		for (let i in this.props.struct) {
			this.items[i].setValue(get(values[i], ''));
		}
	}

	drawForm() {
		let formInputs = [];
		for (let i in this.props.struct) {
			formInputs.push(
				<div className={"input_item " + i} key={i}>
					<div className="input_item_text">
						<div>{this.props.struct[i]['name']} {this.props.struct[i]['nullable'] === false ? <span style={{ color: 'red' }}>*</span> : ''}</div>
						{this.props.struct[i]['description'] && this.props.struct[i]['description'] != '' && <div style={{ color: '#00bcd4', fontStyle: 'italic' }}>{this.props.struct[i]['description']}</div>}
					</div>
					<div className="">
						<Input className="input_item_input" ref={input => this.items[i] = input} {...this.props.struct[i]['input']} Nullable={this.props.struct[i]['nullable']}></Input>
					</div>
				</div>
			)
		}

		return formInputs;
	}



	render() {

		return (
			<form>{this.drawForm()}</form>
		)
	}
}

export default FormInput;
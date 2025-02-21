import React, { Component } from 'react'
import InputParent from './InputParent';

/**
 * - Direct: true/false
 * - DecoratorIn : (value, this) => {}
 * - DecoratorOut : (value, this) => {}
 * - OnChange : (value, this) => {}
 * - DefaultValue : default value
 * - OnChangeBlur: (value, this)=>{} Onchange and value is modified
 * - DateFormat : DD/MM/YYYY HH:mm:ss
 * - TimeFormat : moment time format x or X
 */

class InputDate extends InputParent {

	constructor(props) {
		super(props);
		this.id = 'dateinput_' + makeId()
	}

	initial() {
		this.makeProps([
			'className',
			'DateFormat',
			'TimeFormat'
		]);
		this.makeDecorator();
	}

	makeDecorator(){
		this.DecoratorOut = this.props.DecoratorOut ? this.props.DecoratorOut : (value, obj) => {
			let dateFormat = get(this.props.DateFormat, 'DD/MM/YYYY HH:mm:ss');
			let timeFormat = get(this.props.TimeFormat, 'X');
			if(value == "" || value == null) 
				return value; 
			else 
				return moment(value, dateFormat).format(timeFormat)
		}

		this.DecoratorIn = this.props.DecoratorIn ? this.props.DecoratorIn : (value, obj) => {
			let dateFormat = get(this.props.DateFormat, 'DD/MM/YYYY HH:mm:ss');
			let timeFormat = get(this.props.DateFormat, 'X');
			if(value == "" || value == null) 
				return ''; 
			else 
				return moment(value,timeFormat).format(dateFormat)
		}
	}

	
	componentDidMount() {
		try {
			$("#" + this.id).datetimepicker({
				format: get(this.props.DateFormat, 'DD/MM/YYYY HH:mm:ss'),
			});
			$("#" + this.id).on('dp.change', function (event) {
				this.onChangeHandle(event)
			}.bind(this))
			
		} catch (err) { console.log(err) }

	}

	render() {
		this.initial();
		if(this.props.Direct){
			this.val = this.props.value;
			if(this.DecoratorIn) this.val = this.DecoratorIn(this.val, this);
		}else{
			this.val = this.state.value;
		}
		return (
			<input
				autoComplete="off"
				id={this.id}
				className={'datepicker ' + get(this.props.className, '')}
				value={this.val}
				onChange={ (event)=>{ this.onChangeHandle(event) }}
				onBlur={ (event)=>{ this.onBlurHandle(event) }}
				ref={input => this.input = input}
				{...this.rent}
			>
			</input>
		)
	}
}

export default InputDate;
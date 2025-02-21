import React, { Component } from 'react'
import InputParent from './InputParent';

class InputMoney extends InputParent {

	constructor(props) {
		super(props)
	}

	makeDecorator() {
		this.DecoratorOut = get(this.props.DecoratorOut, (data, obj) => { return this.clearNumber(data) });
		this.DecoratorIn = get(this.props.DecoratorIn, (data, obj) => { return this.formatNumber(data) });
	}

	clearNumber(string) {
		return string.toString().replace(/[^\d\-\.]/g, '');
	}

	formatNumber(num) {
		num = this.clearNumber(num);
		return num.toString().replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1,')
	}


	render() {
		this.initial();

		if(this.props.Direct){
			var val = this.props.value;
			if(this.DecoratorIn) val = this.DecoratorIn(val, this);
		}else{
			var val = this.state.value;
		}
		
		return (
			<input
				value={this.state.value}
				onChange={event => this.onChangeHandle(event)}
				ref={input => this.input = input}
				type='text'
				onBlur={(e) => this.onBlurHandle(e)}
				{...this.rent}
			>
			</input>
		)
	}
}

export default InputMoney;
import React, { Component } from 'react'
import InputParent from './InputParent';

class InputSelect extends InputParent {

	constructor(props) {
		super(props);
	}


	drawOptions() {
		var optionHtml = [];
		this.revert = {};
		
		if(this.props.Options){
			for (let i in this.props.Options) {
				this.revert[this.props.Options[i]] = i;
			}
	
			var values = Object.keys(this.revert).sort();
	
			if (isset(this.revert['All'])) {
				optionHtml.push(<option key={this.revert['All']} value={this.revert['All']}>{lang('All')}</option>);
			}
			for (let i of values) {
				i != 'All' && optionHtml.push(<option key={this.revert[i]} value={this.revert[i]}>{i}</option>);
			}
		}
		
		return optionHtml;
	}

	render() {

		this.initial();

		if(this.props.Direct){
			var val = this.props.value;
			if(this.props.DecoratorIn) val = this.props.DecoratorIn(val, this);
		}else{
			var val = this.state.value;
		}

		return (
			<select
				value={val}
				onChange={(event) => { this.onChangeHandle(event) }}
				ref={input => this.input = input}
				{...this.rent}
			>
				{this.drawOptions()}
			</select>

		)
	}
}

export default InputSelect;
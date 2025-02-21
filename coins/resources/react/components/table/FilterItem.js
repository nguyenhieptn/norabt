import React, { Component } from 'react'
import Input from '../input/Input'
import Style from '../common/Style'

class FilterItem extends Component {

	constructor(props) {
		super(props);
		this.inputComps = {}
		
	}

	initial() {
		
		var {struct, colID, text, className, ...rent } = this.props;
		this.struct = get(struct, {});
		this.colID = colID;
		this.rent = rent;
		this.logic = get(this.struct[FILTER_LOGIC], this.getLogic())
		this.operation = get(this.struct[FILTER_OPERATION], 'and')
		this.input_truct = {
			[INPUT_NAME]: this.struct[FILTER_NAME],
			[INPUT_TYPE]: this.struct[FILTER_TYPE],
			[INPUT_LIMIT]: this.struct[FILTER_LIMIT],
			[INPUT_FORMAT]: this.struct[FILTER_FORMAT],
			[INPUT_OPTION]: this.struct[FILTER_OPTION],
			[INPUT_STYLE_INPUT]: this.struct[FILTER_STYLE_INPUT],
			[INPUT_DECORATOR_IN]: this.struct[FILTER_DECORATOR_IN],
			[INPUT_DECORATOR_OUT]: this.struct[FILTER_DECORATOR_OUT],
			[INPUT_SUGGEST]: this.struct[FILTER_SUGGEST],
			[INPUT_ONCHANGE]: this.struct[FILTER_ONCHANGE]
		};

		this.onChangeBlur = this.props.onChangeBlur;

	}

	setValue(value) {
		if(this.isEditting) return;
		if (!value) {
			this.logic.map(item => {
				this.inputComps[item].setValue('')
			})
			return;
		}
		
		if (value['data']) {
			if (this.struct[FILTER_TYPE] == 'check') {
				for (let i in value['data']) {
					this.inputComps[i].setValue(value['data'][i]);
					break;
				}
			} else {
				this.logic.map(item => {
					this.inputComps[item].setValue(get(value['data'][item], ''))
				})
			}

		}
	}


	getValue() {

		var logic = get(this.operation, 'and');
		var data = {};
		for (let i in this.inputComps) {
			data[i] = this.inputComps[i].getValue();
		}

		return {
			'logic': logic,
			'data': data
		}

	}

	getInput() {
		return this.input.getInput();
	}

	getLogic() {
		if (isset(this.logic)) return this.logic;
		if (this.struct[FILTER_TYPE] == 'text') return ['contain'];
		if (this.struct[FILTER_TYPE] == 'number') return ['='];
		if (this.struct[FILTER_TYPE] == 'checkbox') return ['='];
		if (this.struct[FILTER_TYPE] == 'date') return ['>=', '<='];
		return ['='];
	}

	drawInput() {
		
		switch (this.struct[FILTER_TYPE]) {
			case 'select': {
				return (
					<>
						<div className={`filter_item ${this.props.className}`}>
							{this.props.text === false ? '' : <div className="filter_text" title={this.struct[FILTER_NAME]}>{this.struct[FILTER_NAME]}</div>}
							<div className="filter_input">
								{this.logic.map(item => {
									return <Input onFocus={()=>{this.isEditting = true}} onBlur={()=>{this.isEditting = false}} key={item} ref={input => this.inputComps[item] = input} className="filter_item_input" struct={this.input_truct} onChange={this.onChangeBlur} {...this.rent}></Input>
								})}
							</div>
						</div>
					</>
				);
			}

			case 'check': {
				this.input_truct[INPUT_TYPE] = 'multiSelect';
				return (
					<>
						<div className={`filter_item ${this.props.className}`}>
							{this.props.text === false ? '' : <div className="filter_text" title={this.struct[FILTER_NAME]}>{this.struct[FILTER_NAME]}</div>}
							<div className="filter_input">
								{this.logic.map(item => {
									return <Input onFocus={()=>{this.isEditting = true}} onBlur={()=>{this.isEditting = false}} key={item} placeholder={lang(item)} ref={input => this.inputComps[item] = input} className="filter_item_input" struct={this.input_truct} onChange={this.onChangeBlur} {...this.rent}></Input>
								})}
							</div>
						</div>
					</>
				);
			}

			case 'date': {
				return (
					<>
						<div className={`filter_item ${this.props.className}`}>
							{this.props.text === false ? '' : <div className="filter_text" title={this.struct[FILTER_NAME]}>{this.struct[FILTER_NAME]}</div>}

							<div className="filter_input" style={{ position: 'relative', display: 'flex' }}>
								{this.logic.map(item => {
									return <Input onFocus={()=>{this.isEditting = true}} onBlur={()=>{this.isEditting = false}} placeholder={lang(item)} key={item} ref={input => this.inputComps[item] = input} className="filter_item_input" struct={this.input_truct} onChangeBlur={this.onChangeBlur} {...this.rent}></Input>
								})}
							</div>
						</div>
					</>
				);
			}

			case 'number': {
				return (
					<>
						<div className={`filter_item ${this.props.className}`}>
							{this.props.text === false ? '' : <div className="filter_text" title={this.struct[FILTER_NAME]}>{this.struct[FILTER_NAME]}</div>}

							<div className="filter_input" style={{ position: 'relative', display: 'flex', width:160 }}>
								{this.logic.map(item => {
									return <Input onFocus={()=>{this.isEditting = true}} onBlur={()=>{this.isEditting = false}} placeholder={lang(item)} key={item} ref={input => this.inputComps[item] = input} className="filter_item_input" struct={this.input_truct} onChangeBlur={this.onChangeBlur} {...this.rent}></Input>
								})}
							</div>
						</div>
					</>
				);
			}

			default:

				return (
					<>
						<div className={`filter_item ${this.props.className}`}>
							{this.props.text === false ? '' : <div className="filter_text" title={this.struct[FILTER_NAME]}>{this.struct[FILTER_NAME]}</div>}
							<div className="filter_input">
								{this.logic.map(item => {
									return <Input onFocus={()=>{this.isEditting = true}} onBlur={()=>{this.isEditting = false}} placeholder={lang(item)} key={item} ref={input => this.inputComps[item] = input} className="filter_item_input" struct={this.input_truct} onChangeBlur={this.onChangeBlur} {...this.rent}></Input>
								})}

							</div>
						</div>
					</>
				);
		}
	}

	render() {
		this.initial();
		return (
			<>
				{this.drawInput()}
			</>
		)
	}
}

export default FilterItem;
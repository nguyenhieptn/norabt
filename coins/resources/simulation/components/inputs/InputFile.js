import React, { Component } from 'react'

class InputFile extends Component {

	constructor(props, context) {
		super(props, context)
		this.state = {
			value: ''
		}

		
		
	}

	initial() {
		var { id, value, decoratorOut, decoratorIn, onChange, upload, children, fileManager, ...rent } = this.props;
		this.id = get(id, '');
		this.onChange = get(onChange, () => { });
		this.decoratorOut = get(decoratorOut, null);
		this.decoratorIn = get(decoratorIn, null);
		this.rent = rent;
		this.fileManager = fileManager && fileManager();

	}

	setValue(value) {
		if (!value) value = '';
		if (this.decoratorIn) value = this.decoratorIn(value);
		return new Promise(resolve => this.setState({
			value: value,
		}, () => { resolve(value) }));
	}

	getValue() {
		var value = this.state.value;
		if (this.decoratorOut) value = this.decoratorOut(value);
		return value;
	}

	getFile() {
		return this.input.file;
	}

	getInput() {
		return this.input;
	}

	revertValue(value) {
		if (this.decoratorOut) value = this.decoratorOut(value);
		return value;
	}

	render() {
		this.initial();


		return (
			<div {...this.rent}>
				<div style={{ textAlign: 'center', padding: 5, background: '', margin:0 }} className='button btn-info' onClick={e => {
					
					if (this.fileManager) {
						this.fileManager.modal();
						this.fileManager.setOnSelect((selected) => {
						
							if (isset(selected[0])) {
								this.setState({ value: selected[0] })
							} else {
								this.setState({ value: '' })
							}
							this.fileManager.modal('hide');
						})

						if(this.state.value != ''){
							this.fileManager.setSelected([this.state.value])
						}
						
					}
				}}>
					{lang('File Gallery')}
				</div>
				<div>
					{ (this.state.value == '' || !this.fileManager)
						? <div className='box_flex' style={{ justifyContent:'center', color:'darkgray', minHeight:100}}></div>
						: <div className='box_flex' style={{ justifyContent:'center', padding:5 }}><i className='fa-file-text-o'></i>&nbsp;{basename(this.state.value)}</div>
					}
				</div>

			</div>
		)
	}
}

export default InputFile;
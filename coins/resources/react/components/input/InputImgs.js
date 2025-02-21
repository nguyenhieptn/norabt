import React, { Component } from 'react'
import LazyImg from '../common/LazyImg';
import FileManager from './FileManager';

class InputImgs extends Component {

	constructor(props, context) {
		super(props, context)
		this.state = {
			value: []
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

	setValue(value, callback) {
		if (!value) value = [];
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
				<div style={{ textAlign: 'center', padding: 5 }} className='button button_gallery' onClick={e => {
					if (this.fileManager) {
						this.fileManager.modal();
						this.fileManager.setOnSelect((selected) => {
							selected = Object.keys(selected);
							this.setState({ value: selected });
							this.fileManager.modal('hide');
						})
						var selects = {};
						this.state.value.map(item => selects[item] = true);
						this.fileManager.setSelected(selects);
					}
				}}>
					{lang('Thư viện File')}
					<div className='close' style={{ fontSize: 14 }} onClick={(e) => { e.stopPropagation(); this.setValue([]) }}>&times;</div>
				</div>
				<div className='d-flex' style={{ textAlign: 'center', padding: 5 }}>
					{this.state.value.map(item => {
						return <div key={item} style={{ padding: 5, width: '25%' }} className='box_border'>
							<LazyImg key={item} id={item} style={{width:'100%'}}></LazyImg>
						</div>
					})}
				</div>

				{!this.fileManager && <FileManager ref={c => this.fileManager = c}></FileManager>}

			</div>
		)
	}
}

export default InputImgs;
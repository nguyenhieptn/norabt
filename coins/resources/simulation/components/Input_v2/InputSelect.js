import React from 'react'
import InputParent from './InputParent';
import { Dropdown } from 'primereact/dropdown';
import Style from '../common/Style';

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
		this.id = 'select'+this.id
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

	componentDidMount(){
		document.getElementById(this.id).addEventListener('click', (e)=>{
			if(this.props.onClick) this.props.onClick(e)
		})
	}

	render() {

		this.initial();

		var val = this.showValue()
		this.rent.style = {...this.rent.style, padding:0, minWidth:'unset', whiteSpace: 'nowrap'}

		return (
			<>
			<Dropdown
				id = {this.id}
				value={val}
				options={this.props.Options}
				onChange={(event) => { this.onChangeHandle(event) }}
				ref={input => this.input = input}
				{...this.rent}
				filter filterBy="name"
				
			></Dropdown>
			<Style id="Dropdow_panel">{`
				.p-dropdown .p-dropdown-panel {
					top: 30px !important;
				}
			`}</Style>
			</>
			

			// <div style={{position:'relative'}}>

			// 	<input ref={c => this.searchBox = c} className={this.props.className} style={{position:'absolute', zIndex:0}} type='text' placeholder='Search'></input>
			// 	<select
			// 		onFocus={()=>{this.searchBox.style.zIndex=3; this.searchBox.focus()}}
			// 		value={val}
			// 		onChange={(event) => { this.onChangeHandle(event) }}
			// 		ref={input => this.input = input}
			// 		{...this.rent}
			// 	>
			// 		{this.drawOptions(val)}
			// 	</select>
			// </div>

		)
	}
}

export default InputSelect;
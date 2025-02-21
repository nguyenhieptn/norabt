import React, { Component } from 'react'

class InputText extends Component {

	constructor(props) {
		super(props);

		this.state = {
			value: get(this.props.value, ''),
			suggest: {},
			loading: false,
		}
	}

	initial() {
		var { id, value, decoratorOut, decoratorIn, onChange, options, suggest, onFocus, ...rent } = this.props;
		this.id = get(id, '');
		this.onFocus = get(onFocus, () => { });
		this.onChange = get(onChange, () => { });
		this.options = get(options, {});
		this.suggest = get(suggest, null);
		this.decoratorOut = get(decoratorOut, null);
		this.decoratorIn = get(decoratorIn, null);
		this.rent = rent;
	}

	async getProduct(code) {
		if (isset(this.state.suggest[code])) return this.state.suggest[code];
		var res = await this.querySuggest(code);
		if (res && isset(res[code])) return res[code];
		return null;
	}

	setValue(value) {
		if (this.options[value]) value = this.options[value];
		if (this.decoratorIn) value = this.decoratorIn(value);
		if (value == null) value = '';
		this.setState({ value: value });
	}

	getValue() {
		var value = this.state.value;
		if (this.decoratorOut) value = this.decoratorOut(value);
		if (isset(this.revert[value])) value = this.revert[value];
		return value;
	}

	getInput() {
		return this.input;
	}

	revertValue(value) {
		if (this.decoratorOut) value = this.decoratorOut(value);
		if (isset(this.revert[value])) value = this.revert[value];
		return value;
	}

	loadSuggest() {

		clearTimeout(this.suggestTimeout);
		if (isset(this.revert[this.state.value])) {
			this.setState({ loading: false });
			return;
		}
		this.setState({ loading: true });
		this.suggestTimeout = setTimeout(() => { this.querySuggest() }, 1000);

	}

	querySuggest(search = null) {
		if (search == null) search = this.state.value;
		if (search == '') return;
		return axios.request({
			url: App.saleApi(`/api/product/search/${App.project[PROJECT_CODE]}/${search}`),
			method: 'get',
		})

			.then(response => {
				response = response['data']['result'];
				var suggest = {};
				response.map(item => {
					suggest[item[PRODUCT_CODE]] = item;
				})
				this.setState({
					loading: false,
					suggest: suggest
				});

				return response;
			})
			.catch((error) => {
				this.setState({
					loading: false,
				});
			})
	}

	onFocusHandle(value) {
		this.onFocus();
		if (value == '') {
			this.querySuggest();
		}
	}

	render() {
		this.initial();

		var datalist = [];
		this.revert = {};

		for (let i in this.state.suggest) {
			datalist.push(<option key={i} value={i}>{this.state.suggest[i][PROJECT_CODE]}</option>);
			this.revert[this.state.suggest[i]] = i;
		}

		for (let i in this.options) {
			if (!this.state.suggest[i]) {
				datalist.push(<option key={i} value={this.options[i]}>{this.options[i]}</option>);
				this.revert[this.options[i]] = i;
			}
		}

		var loading = '';
		if (this.state.loading) {
			loading = <i style={{ margin: 'auto', padding: 5 }} className="fa fa-circle-o-notch fa-spin"></i>
		}

		return (
			<div style={{ display: 'flex' }}>
				<input
					value={this.state.value}
					onChange={(event) => { this.setState({ 'value': event.target.value }, () => { this.onChange(); this.loadSuggest() }) }}
					onFocus={(event) => this.onFocusHandle(event.target.value)}
					ref={input => this.input = input}
					list={"editlist" + this.id}
					{...this.rent}
				/>
				{loading}
				<datalist id={"editlist" + this.id}>
					{datalist}
				</datalist>
			</div>
		)
	}
}

export default InputText;
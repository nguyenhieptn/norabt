
import React, { Component } from 'react'
import FormInput from '../../components/input/FormInput';
import Watchlist from '../../model/admin/Watchlist';


class WatchlistControl extends Component {

	constructor(props) {
		super(props);

		this.struct = {
			[WL_PARAMS_STOPLOSS]: {
				[INPUT_NAME]: lang(WL_PARAMS_STOPLOSS) + ' (%)',
				[INPUT_TYPE]: 'number',
			},
			[WL_PARAMS_TAKEPROFIT]: {
				[INPUT_NAME]: lang(WL_PARAMS_TAKEPROFIT) + ' (%)',
				[INPUT_TYPE]: 'number',
			},
			[WL_PARAMS_TIMELIFE]: {
				[INPUT_NAME]: lang(WL_PARAMS_TIMELIFE) + ' (minute)',
				[INPUT_TYPE]: 'number',
			},

		}

		this.symbol = get(App.parsed['symbol'], '')

	}



	render() {
		return (<>
			<div className='box_shadow box_padding'>
				<h4>System Setting: {this.symbol}</h4>
				<br />
				<div>
					<FormInput ref={e => this.form = e} struct={this.struct}></FormInput>
				</div>

				<div className='box_flex'>
					<button style={{ margin: 'auto 0px auto auto' }} onClick={() => {
						var data = this.form.getValue();
						this.updateData(data)
					}} className="button btn btn-primary">{lang('Save')}</button>
				</div>



			</div>
		</>
		);
	}

	componentDidMount() {

		this.loadData()
	}

	loadData() {

		if (this.symbol == '') return;

		var wlModel = new Watchlist();

		wlModel.read({ [WL_SYMBOL]: this.symbol }).then(res => {
			console.log(res);
			if (res) {
				if (res['result']) {
					try {
						var data = res['data'][0];
						var params = data[WL_PARAMS];

						params = JSON.parse(params);
						this.form.setValue(params);
					} catch (error) {

					}

				} else {
					error_handle(res);
				}
			}
		})
	}

	updateData(data) {

		if (this.symbol == '') return;

		var wlModel = new Watchlist();

		wlModel.edit({ [WL_SYMBOL]: this.symbol }, { [WL_PARAMS]: JSON.stringify(data) }).then(res => {
			if (res) {
				if (res['result']) {
					this.loadData();
				} else {
					error_handle(res);
				}
			}
		})
	}



}

export default WatchlistControl
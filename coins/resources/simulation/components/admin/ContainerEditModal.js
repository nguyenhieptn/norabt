import React, { Component } from 'react'

import FormInput from '../inputs/FormInput';
import InputNumber from '../inputs/InputNumber';
import InputSelect from '../inputs/InputSelect';
import Strategies from '../../model/admin/Lab_strategies';
import Strategy_container from '../../model/admin/Lab_strategy_container';
import InputMultiSelect from '../inputs/InputMultiSelect';
import Watchlist from '../../model/admin/Lab_watchlist';
import InputV2 from '../../components/Input_v2/Input';
class ContainerEditModal extends Component {

	constructor(props) {
		super(props);
		this.state = {
			strategy: {
			},
			children: [],
			update: 0,
			strategyOptions: {},
			strategyOptions1: [],
			watchlist: {},
			optionUser: {},
			optionGroup: {}
		}
	}


	onClickHandle(apply = 0) {
		var strategy = this.form.getValue();
		var children = this.state.children;
		var model = new Strategies();
		strategy[LAB_STRATEGY_CONTAINER] = 1;
		if (isset(this.state.strategy[LAB_STRATEGY_ID])) {
			var id = this.state.strategy[LAB_STRATEGY_ID];
			model.edit({ [LAB_STRATEGY_ID]: id }, strategy, true, { children, apply }).then(res => {
				if (res) {
					this.modal('hide');
					if (this.props.onClickHandle) this.props.onClickHandle();
				}
			})
		} else {
			model.add(strategy, true, { children }).then(res => {
				if (res) {
					this.modal('hide');
					if (this.props.onClickHandle) this.props.onClickHandle();
				}
			})
		}


	}


	modal(cmd = 'show') {
		if (cmd == 'hide') {
			$("#edit_row_modal" + this.id).modal('hide');
		} else {
			$("#edit_row_modal" + this.id).modal();
			this.reload();
		}
	}

	loadData(rowData) {
		this.rowData = rowData;
		this.form.setValue(this.rowData);
		this.setState({ strategy: rowData }, () => {
			this.getChildren();
			this.getChildrenOption();
		})
	}

	setOptionUser(optionUser , optionGroup) {
		this.setState({
			optionUser,
			optionGroup
		});
	}
	reload() {
		this.forceUpdate();
	}

	getChildren() {
		var model = new Strategy_container();
		if (isset(this.state.strategy[LAB_STRATEGY_ID])) {
			model.read({ [LAB_STRA_CON_CONTAINER]: this.state.strategy[LAB_STRATEGY_ID] }).then(res => {
				if (res) {
					this.setState({ children: res['data'] });
				}
			})
		} else {
			this.setState({ children: [] })
		}

	}

	getChildrenOption() {
		var model = new Strategies();
		model.read({ [LAB_STRATEGY_CONTAINER]: null }).then(res => {
			if (res) {
				var strategies = res['data'];
				var strategyOptions = {};
				var strategyOptions1 = [];
				for (let i in strategies) {
					strategyOptions[strategies[i][LAB_STRATEGY_ID]] = strategies[i][LAB_STRATEGY_NAME]
					strategyOptions1.unshift({
						'label': strategies[i][LAB_STRATEGY_NAME],
						'value': strategies[i][LAB_STRATEGY_ID],
					});
				}

				this.setState({ strategyOptions, strategyOptions1 });
			}
		})
	}

	getWatchlist() {
		var model = new Watchlist();
		model.getWatchlist().then(res => {
			this.setState({ watchlist: res })
		})
	}

	componentDidMount() {
		this.getChildrenOption();
		this.getWatchlist();
	}

	render() {
		// console.log(this.state.optionGroup)
		var strategy = this.state.strategy;
		var children = this.state.children;
		children = children.sort((a, b) => { return a[LAB_STRA_CON_WEIGHT] - b[LAB_STRA_CON_WEIGHT] });
		return (
			<div className="modal fade" id={"edit_row_modal" + this.id} onClick={() => { addClass($('body')[0], 'modal-open') }}>
				<div className="modal-dialog modal-lg modal-dialog-centered">
					<div className="modal-content">

						<div className="modal-header">
							<h4 className="modal-title">{strategy[LAB_STRATEGY_NAME]}</h4>
							<button type="button" className="close" data-dismiss="modal">&times;</button>
						</div>

						<div className="modal-body" style={{ textAlign: 'initial' }}>

							<FormInput ref={c => this.form = c} struct={{
								[LAB_STRATEGY_NAME]: {
									name: lang(LAB_STRATEGY_NAME),
									nullable: false,
									input: {
										type: 'text',
									}

								},

								[LAB_STRATEGY_TAKEPROFIT]: {
									name: lang(LAB_STRATEGY_TAKEPROFIT),
									input: {
										type: 'number',
									}

								},
								[LAB_STRATEGY_STOPLOSS]: {
									name: lang(LAB_STRATEGY_STOPLOSS),
									input: {
										type: 'number',
									}

								},
								[LAB_STRATEGY_BASEPROFIT]: {
									name: lang(LAB_STRATEGY_BASEPROFIT),
									input: {
										type: 'number',
									}

								},
								[LAB_STRATEGY_STEPPROFIT]: {
									name: lang(LAB_STRATEGY_STEPPROFIT),
									input: {
										type: 'number',
									},
									description: 'The increment step of base profit'

								},
								[LAB_STRATEGY_BACKPROFIT]: {
									name: lang(LAB_STRATEGY_BACKPROFIT),
									input: {
										type: 'number',
									},
									description: 'Cancle order if profit < baseprofit - backprofit'

								},


								[LAB_STRATEGY_TIMELIFE]: {
									name: lang(LAB_STRATEGY_TIMELIFE),
									input: {
										type: 'number',
										DefaultValue: 6,
									},
									description: 'The time before the Pending order is cancle in minutes',

								},
								[LAB_STRATEGY_INTERVAL]: {
									name: lang(LAB_STRATEGY_INTERVAL),
									input: {
										type: 'number',
										DefaultValue: 0,
									},
									description: 'Interval between 2 Orders in minutes',

								},
								[LAB_STRATEGY_MARGIN]: {
									name: lang(LAB_STRATEGY_MARGIN),
									input: {
										type: 'number',
									},

								},
								[LAB_STRATEGY_USER]: {
									name: lang(LAB_STRATEGY_USER),
									input: {
										type: 'select',
										Options: { '': '', ...this.state.optionUser }
									},

								},
								[LAB_STRATEGY_GROUP]: {
									name: lang(LAB_STRATEGY_GROUP),
									input: {
										type: 'text',
										DefaultValue: App.parsed.group,
										Options: { ...this.state.optionGroup }
									},
								
								},
								[LAB_STRATEGY_NOTE]: {
									name: lang(LAB_STRATEGY_NOTE),
									input: {
										type: 'textarea',
									},

								},
							}}></FormInput>

							<hr></hr>

							<div className='box_flex'>
								<li style={{ padding: 5 }}>Children:</li>
								<div className='button btn btn-primary btn-sm' onClick={() => {
									children.push({
										[LAB_STRA_CON_ID]: makeId(),
										[LAB_STRA_CON_CHILD]: '',
										[LAB_STRA_CON_SLOT]: 1,
										[LAB_STRA_CON_WEIGHT]: children.length,
										[LAB_STRA_CON_BLACKLIST]: '[]',
									})
									this.setState({ children })
								}}>Add</div>
							</div>
							<div>
								{children.map((child, key) => {
									return <div key={child[LAB_STRA_CON_ID]} className='box_flex' style={{ padding: 5, border: 'solid thin #eee', orderRadius: 3, margin: 5 }}>

										<div className='box_flex' style={{ flex: 2 }}>
											<div style={{ padding: 5 }}>Strategy :&nbsp;</div>
											<InputV2  className='input' type="select" DefaultValue={child[LAB_STRA_CON_CHILD]} Options={this.state.strategyOptions1} OnChange={
												(value, obj) => {
													child[LAB_STRA_CON_CHILD] = value;
													this.setState({ children })
												}
											}>
											</InputV2>
										</div>

										{/* <div className='box_flex' style={{ flex: 1 }}>
											<div style={{ padding: 5 }}>Strategy:&nbsp;</div>
											<InputSelect className='input' Options={{ '': '', ...this.state.strategyOptions }} value={child[LAB_STRA_CON_CHILD]} Direct={true} OnChange={(val) => {
												child[LAB_STRA_CON_CHILD] = val;
												this.setState({ children })
											}}></InputSelect>
										</div> */}

										<div className='box_flex' style={{ flex: 1 }}>
											<div style={{ padding: 5 }}>Slot:&nbsp;</div>
											<InputNumber className='input' Direct={true} value={child[LAB_STRA_CON_SLOT]} OnChange={(val) => {
												child[LAB_STRA_CON_SLOT] = val;
												this.setState({ children })
											}}></InputNumber>
										</div>

										<div className='box_flex' style={{ flex: 1 }}>
											<div style={{ padding: 5 }}>Weight:&nbsp;</div>
											<InputNumber className='input' Direct={true} value={child[LAB_STRA_CON_WEIGHT]} OnChange={(val) => {
												child[LAB_STRA_CON_WEIGHT] = val;
												this.setState({ children })
											}}></InputNumber>
										</div>

										<div className='box_flex' style={{ flex: 5 }}>
											<div style={{ padding: 5 }}>Blacklist:&nbsp;</div>
											<InputMultiSelect className='input' style={{ width: '100%' }} Direct={true} value={child[LAB_STRA_CON_BLACKLIST]}
												OnChange={(val) => {
													child[LAB_STRA_CON_BLACKLIST] = val;
													this.setState({ children })
												}}
												Options={this.state.watchlist}
												DecoratorIn={(val, obj) => { return val ? JSON.parse(val) : [] }}
												DecoratorOut={(val, obj) => { return JSON.stringify(val) }}
											></InputMultiSelect>
										</div>

										<div style={{ flex: 1 }}>
											<div className='close' onClick={() => {
												children.splice(key, 1);
												this.setState({ children })
											}}>&times;</div>
										</div>

									</div>
								})}
							</div>



						</div>

						<div className="modal-footer">
							{isset(this.props.extraFunction) ? this.props.extraFunction : ''}
							<button type="button" className="btn btn-warning" onClick={() => { this.onClickHandle(1) }}>{lang('Save and Apply')}</button>
							<button type="button" className="btn btn-danger" data-dismiss="modal">{lang('Close')}</button>
						</div>

					</div>
				</div>
			</div>
		)
	}
}
export default ContainerEditModal

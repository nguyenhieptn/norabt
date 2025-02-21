import React, { Component } from 'react'
import Lab_account from '../../model/admin/Lab_account';
import Lab_campaigns from '../../model/admin/Lab_campaigns';
import Lab_watchlist from '../../model/admin/Lab_watchlist';
import Input from '../inputs/Input';
import Coinmarket from '../../../react/model/admin/Coinmarket'
class LabTradeList extends Component {

	constructor(props) {
		super(props);
		this.id = makeId();

		this.state = {
			campaigns: {},
			account: {},
			watchlist: {},
			mapping: {},
			isHideUnselected: true,
			symbolSearch: '',
			page_active : 1,
			page_quantity : 25,
			page_total_record : 0,
			page_total : 0,


			sortField : LAB_CAMPAIGN_BUDGET,
			sortOrder : 'none',

		}

		this.campaignModel = new Lab_campaigns();
		this.accountModel = new Lab_account();
		this.wlModle = new Lab_watchlist();

		this.oldData = {};

		this.campaignStruct = {

			[LAB_CAMPAIGN_NAME]: {
				name: lang('Campaign Name'),
				flex: 1,
				type: 'text',
			},

			[LAB_CAMPAIGN_STRATEGY]: {
				name: lang(LAB_CAMPAIGN_STRATEGY),
				flex: 1,
				type: 'select_unsort',


			},

			[LAB_CAMPAIGN_PRIORITY]: {
				name: lang(LAB_CAMPAIGN_PRIORITY),
				flex: 1,
				type: 'number',

			},

			[LAB_CAMPAIGN_SIDE]: {
				name: lang(LAB_CAMPAIGN_SIDE),
				flex: 1,
				type: 'select',

			},

			[LAB_CAMPAIGN_BUDGET]: {
				name: lang(LAB_CAMPAIGN_BUDGET),
				flex: 1,
				type: 'number',
				default: 100,
				sort : true,
				sortField : LAB_CAMPAIGN_BUDGET

			},
			[LAB_CAMPAIGN_ACTIVE_BUDGET]: {
				name: lang(LAB_CAMPAIGN_ACTIVE_BUDGET),
				flex: 1,
				type: 'number',
				default: 100,

			},

			[LAB_CAMPAIGN_MONEY]: {
				name: lang(LAB_CAMPAIGN_MONEY),
				flex: 1,
				type: 'number',
				default: 100,

			},

			[LAB_CAMPAIGN_COMPOUND]: {
				name: lang(LAB_CAMPAIGN_COMPOUND),
				flex: 1,
				type: 'select',
			},

			[LAB_CAMPAIGN_START]: {
				name: lang(LAB_CAMPAIGN_START),
				flex: 1,
				type: 'date',
			},

			[LAB_CAMPAIGN_STOP]: {
				name: lang(LAB_CAMPAIGN_STOP),
				flex: 1,
				type: 'date',
			},
		}

		this.coinMarketData = {}
	}

	modal(cmd = 'show') {
		if (cmd == 'hide') {
			$("#bladeModal" + this.id).modal('hide');
		} else {
			$("#bladeModal" + this.id).modal();
		}
	}

	getRankCoinMarket(){
		var model = new Coinmarket();

		return model.getRank()
	}


	async componentDidMount() {

		this.campaignModel.map().then(res => {
			if (res) {
				if (res['result']) {
					var mapping = res['data'];
					for (let i in mapping) {
						mapping[i][''] = '-- Select --';
					}
					this.setState({ mapping })
				}
			}
		})
		this.coinMarketData = await this.getRankCoinMarket()

		this.wlModle.getWatchlist().then(res => {
			if (res) {
				
				this.setState({ 
					watchlist: res , 
					page_total_record : Object.keys(res).length , 
					page_total : Math.ceil(Object.keys(res).length / this.state.page_quantity)  
				});
			}
		})
	}


	async setAccount(account) {
		var campaigns = await this.getCampaigns(account[LAB_ACCOUNT_ID]);

		this.setState({
			campaigns, account, isHideUnselected: Object.keys(campaigns).length > 0
		})
	}


	getCampaigns(id) {

		return this.campaignModel.read({ [LAB_CAMPAIGN_ACCOUNT]: id }).then(res => {
			if (res) {
				if (res['result']) {
					var oldData = {};
					var campaigns = {};
					for (let i in res['data']) {
						oldData[res['data'][i][LAB_CAMPAIGN_SYMBOL]] = { ...res['data'][i] };
						campaigns[res['data'][i][LAB_CAMPAIGN_SYMBOL]] = res['data'][i];
					}
					this.oldData = oldData;
					return campaigns;
				} else {
					error_handle(res);
				}
			}
		})
	}

	editCurrentPage(vector, interval) {
		if (vector == 'up') {
			var newValue = Number(this.state.page_active) + Number(interval)
			if (newValue > this.state.page_total) newValue = 1;
			if (newValue < 1) newValue = this.state.page_total;

		}
		if (vector == 'down') {
			var newValue = Number(this.state.page_active) - Number(interval)
			if (newValue > this.state.page_total) newValue = 1;
			if (newValue < 1) newValue = this.state.page_total;
		}
		this.setState({
			page_active : newValue
		});
		
	}

	editNumberPage(event) {
		var value = Number(event.target.innerText);
		if (value <= 0 || value > 1000) {
			event.target.innerText = this.state.page_quantity;
			return;
		}

		if (value == this.state.page_quantity) return;
		this.setState({
			page_quantity : value,
			page_total : Math.ceil(this.state.page_total_record / value)  
		});
		
	}

	editPage(event) {
		var value = Number(event.target.innerText);
		if (value <= 0 || value > this.state.page_total) {
			event.target.innerText = this.state.page_active;
			return;
		}

		if (value == this.state.page_active) return;
		this.setState({
			page_active : value
		});
	}


	handleSort(name){

		let sortParam = {
			'none': 'desc',
			'desc' : 'asc',
			'asc' : 'desc'
		}


		this.setState({
			sortField : name,
			sortOrder : sortParam[this.state.sortOrder] 
		});
	

		let sortable = [];
		Object.keys(this.state.campaigns).map(sym => {
			sortable.push({
				'key' : sym,
				'value' :  this.state.campaigns[sym][name]
			})
		})

		if(sortParam[this.state.sortOrder]  == 'asc'){
			sortable.sort(function(a, b){return a['value'] - b['value'] });
		}else{
			sortable.sort(function(a, b){return b['value'] - a['value'] });
		}
	
		
		let result = {}
		sortable.map(row => {
			let key = row['key']
			result[key] = key

		})

		this.setState({
			watchlist : result
		});
	}

	renderHeader(struct){

	

		if(struct.sort ){

			if(struct.sortField == this.state.sortField){

				
				return(
					<div className="column_sort" vector={this.state.sortOrder} onClick={() => this.handleSort(struct.sortField)}><b>{struct.name}</b> </div>
				)
			}else{
				return(
					<div className="column_sort" vector="none"><b>{struct.name}</b> </div>
				)
			}

			

		}else{

			return(
			<b>{struct.name}</b>
			)
			
		}



	}


	render() {

		var accountBalance = get(this.state.account[LAB_ACCOUNT_BALANCE], 0);
		var accountReserve = get(this.state.account[LAB_ACCOUNT_RESERVE], 0);
		var totalBallance = 0;
		var campaigns = this.state.campaigns;
		Object.keys(campaigns).map(item => totalBallance += Number(campaigns[item][LAB_CAMPAIGN_BUDGET]));
		var reserve = Math.ceil(accountReserve * accountBalance * 1000 / 100) / 1000;

		return (
			<>
				<div className="modal fade" id={"bladeModal" + this.id}>
					<div className="modal-dialog modal-lg modal-dialog-centered" style={{ maxWidth: '95%' }}>
						<div className="modal-content">

							<div className="modal-header">
								<h4 className="modal-title">{this.state.account[LAB_ACCOUNT_NAME]}</h4>
								<button type="button" className="close" data-dismiss="modal">&times;</button>
							</div>

							<div className="modal-body" style={{ textAlign: 'initial' }}>
								<div className='box_flex' style={{ flexWrap: 'wrap', color: accountBalance - reserve >= totalBallance ? 'green' : 'red' }}>
									Wallet balance: <input style={{ width: 100 }} className='input'
										value={Math.round(accountBalance * 100) / 100}
										onChange={(e) => {
											this.state.account[LAB_ACCOUNT_BALANCE] = e.target.value;
											this.setState({ account: this.state.account })
											this.isBalanceEdited = true;
										}}
										onBlur={e => {
											if (!this.isBalanceEdited) return;
											this.isBalanceEdited = false;
											this.accountModel.edit({ [LAB_ACCOUNT_ID]: this.state.account[LAB_ACCOUNT_ID] }, { [LAB_ACCOUNT_BALANCE]: e.target.value })
										}}
									></input>

									&nbsp;&nbsp;
									Used: <strong>{Math.round(totalBallance * 100) / 100}</strong>&nbsp;&nbsp;
									Free: <strong>{Math.round((accountBalance - totalBallance - reserve) * 100) / 100}</strong>&nbsp;&nbsp;
									Reserve(%): &nbsp; <input style={{ width: 30 }} className='input'
										value={accountReserve}
										onChange={(e) => {
											this.state.account[LAB_ACCOUNT_RESERVE] = e.target.value;
											this.setState({ account: this.state.account })
											this.isReserveEdited = true;
										}}
										onBlur={e => {
											if (!this.isReserveEdited) return;
											this.isReserveEdited = false;
											this.accountModel.edit({ [LAB_ACCOUNT_ID]: this.state.account[LAB_ACCOUNT_ID] }, { [LAB_ACCOUNT_RESERVE]: e.target.value })
										}}
									></input>
									&nbsp;<b>({reserve} USDT)</b>

									<div className='button btn btn-info' onClick={() => {
										var free = accountBalance - totalBallance - reserve;

										if (free < 0) return;
										var increate = Math.floor(free * 1000 / Object.keys(campaigns).length) / 1000;
										for (let i in campaigns) {
											let newBg = Number(campaigns[i][LAB_CAMPAIGN_BUDGET]) + increate;
											campaigns[i][LAB_CAMPAIGN_BUDGET] = newBg;
											campaigns[i][LAB_CAMPAIGN_MONEY] = newBg;
										}
										this.setState({ campaigns })
									}}>Auto Arrange</div>

									<label className='box_flex' style={{ margin: 'auto 0px auto auto' }}>
										<input placeholder='Search Symbol' className='input' value={this.state.symbolSearch} onChange={e => this.setState({ symbolSearch: e.target.value.toLocaleUpperCase() })}></input>
										&nbsp;
										<input type='checkbox' checked={this.state.isHideUnselected}
											onChange={e => this.setState({ isHideUnselected: !this.state.isHideUnselected })}></input>
										&nbsp;Hide Unselected
									</label>

								</div>


								{accountBalance - reserve < totalBallance && <div className="alert alert-danger">Not enough <strong className='button' onClick={() => {
									var reducePercent = (totalBallance) / (accountBalance - reserve);
									for (let i in campaigns) {
										let newBg = Math.floor(Number(campaigns[i][LAB_CAMPAIGN_BUDGET]) * 1000 / reducePercent) / 1000;
										campaigns[i][LAB_CAMPAIGN_BUDGET] = newBg;
										campaigns[i][LAB_CAMPAIGN_MONEY] = newBg;
									}
									this.setState({ campaigns })
								}}>Fix it</strong></div>}

								<div><b>Selected: {Object.keys(this.state.campaigns).length}</b></div>

								<div>

									<div className='box_flex'>
										<div className='box_flex box_line' style={{ flex: 1, padding: 5, margin: 5 }}>
											<label className='box_flex'>
												<input type="checkbox" checked={Object.keys(campaigns).length > 0} onChange={e => {
													if (e.target.checked) {
														for (let i in this.state.watchlist) {
															campaigns[i] = {
																[LAB_CAMPAIGN_SYMBOL]: i,
																[LAB_CAMPAIGN_ACCOUNT]: this.state.account[LAB_ACCOUNT_ID],
																[LAB_CAMPAIGN_BUDGET]: 0,
																[LAB_CAMPAIGN_MONEY]: 0,
																[LAB_CAMPAIGN_STRATEGY]: ''

															}
														}
													} else {
														campaigns = {};
													}
													this.setState({ campaigns });
												}}></input>
												&nbsp;
												<b>All</b>
											</label>
										</div>

										{Object.keys(this.campaignStruct).map(key => {
											let struct = this.campaignStruct[key];



											return <div key={key} style={{ flex: struct.flex, textAlign: 'center', padding: 5 }}>
												<div>

													{
														this.renderHeader(struct)
													}
													
													
												</div>

												<div><Input className="input"
													type={struct.type}
													Direct={false}
													Options={get(this.state.mapping[key], {})}
													OnChangeBlur={(val) => {
														for (let i in campaigns) {
															if (key == LAB_CAMPAIGN_NAME) {
																campaigns[i][key] = val + '-' + campaigns[i][LAB_CAMPAIGN_SYMBOL];
															} else if (key == LAB_CAMPAIGN_PRIORITY) {
																campaigns[i][key] = val;
																val++;
															} else {
																campaigns[i][key] = val;
															}

														}
														this.setState({ campaigns })
													}}
													OnChange={val => {
														if (struct.type == 'select' || struct.type == 'select_unsort') {
															for (let i in campaigns) {
																campaigns[i][key] = val;
															}
															this.setState({ campaigns })
														}
													}}
												></Input></div>
											</div>
										})}



									</div>

									{Object.keys(this.state.watchlist).map((symbol, key) => {


										let show = isset(campaigns[symbol]);
										if (!this.state.isHideUnselected) {
											show = true;
										}

										if (!symbol.includes(this.state.symbolSearch)) {
											show = false
										}
										
										if(this.state.page_quantity * (this.state.page_active - 1) > key || key > this.state.page_quantity * (this.state.page_active ) - 1 ){
											show = false
										}
										var rankData = (symbol == '1000SHIBUSDT' ? 'SHIBUSDT' : symbol);

										return <div key={symbol} className='box_flex box_shadow' style={{ display: (show ? 'flex' : 'none') }}>

											<div className='box_flex box_line' style={{ flex: 1, padding: 5, margin: 5 }}>
												<label className='box_flex'>
													<input type="checkbox" checked={isset(campaigns[symbol])} onChange={e => {
														if (e.target.checked) {
															campaigns[symbol] = {
																[LAB_CAMPAIGN_SYMBOL]: symbol,
																[LAB_CAMPAIGN_ACCOUNT]: this.state.account[LAB_ACCOUNT_ID],
																[LAB_CAMPAIGN_BUDGET]: 0,
																[LAB_CAMPAIGN_MONEY]: 0,
																[LAB_CAMPAIGN_STRATEGY]: ''
															}
														} else {
															delete (campaigns[symbol]);
														}
														this.setState({ campaigns });
													}}></input>
													&nbsp;
													{key + 1}.
													&nbsp;
													{symbol}
													<span style={{ color: 'blue', fontWeight: 'normal' }}> [{get(this.coinMarketData[rankData], '')}]</span>
												</label>
											</div>

											{Object.keys(this.campaignStruct).map(key => {
												let struct = this.campaignStruct[key];
												if (!isset(campaigns[symbol])) return <div key={key} style={{ flex: struct.flex, textAlign: 'center', padding: 5 }}></div>
												return <div key={key} style={{ flex: struct.flex, textAlign: 'center', padding: 5 }}>
													<div><Input className="input"
														type={struct.type}
														Direct={true}
														value={get(campaigns[symbol][key], '')}
														OnChange={val => { campaigns[symbol][key] = val; this.setState({ campaigns }); }}
														Options={get(this.state.mapping[key], {})}
													></Input></div>
												</div>
											})}


										</div>
									})
									}
								</div>


							</div>

							<div className="modal-footer" style={{ justifyContent: 'space-between' }}>

								<div>
									<div style={{ display: 'flex' }}>

										<span className="page_break" style={{ margin: 'auto auto auto 0px', display: 'flex', alignItems: 'center' }}>
											<i className="fa fa-angle-double-left forward_pre" onClick={() => this.editCurrentPage('down', 10)}></i>

											<span className="step step_pre" onClick={() => this.editCurrentPage('down', 1)}>{lang('Period')}</span>

											<div className="current_page" suppressContentEditableWarning={true} style={{ minHeight: 15, minWidth: 5 }}
												contentEditable={true} onBlur={(event) => this.editPage(event)}>{this.state.page_active}</div>

											&nbsp;of&nbsp;

											<span className="total_page">{this.state.page_total}</span>&nbsp;
											<span className="step step_next" onClick={() => this.editCurrentPage('up', 1)}>{lang('Next')}</span>

											<i className="fa fa-angle-double-right forward_next" onClick={() => this.editCurrentPage('up', 10)}></i>

											<div style={{ fontWeight: 'bold' }}>{lang("Total") + ": " + this.state.page_total_record}</div>
										</span>

										<span style={{ margin: "auto 0px auto auto" }}>
											<div style={{ padding: 5, border: 'solid thin darkgray', minHeight: 15, borderRadius: 4 }}
												suppressContentEditableWarning={true} contentEditable={true} onBlur={(event) => this.editNumberPage(event)}>{this.state.page_quantity}</div>
										</span>

									</div>
								</div>
								<div>
									<button type="button" className="btn btn-primary mr-3" onClick={() => {
										this.saveData()
									}}>Save</button>

									<button type="button" className="btn btn-danger mr-3" data-dismiss="modal">Close</button>
								</div>
							</div>

						</div>
					</div>
				</div>

			</>
		)
	}



	async saveData() {

		var campaigns = this.state.campaigns;
		var addData = [];

		for (let sym in this.oldData) {
			if (!isset(campaigns[sym])) {
				var result = await this.campaignModel.delete({ [LAB_CAMPAIGN_ID]: this.oldData[sym][LAB_CAMPAIGN_ID] }, false);
				if (!result['result']) {
					return result;
				}
			}
		}

		for (let sym in campaigns) {
			if (!isset(this.oldData[sym])) {
				addData.push(campaigns[sym]);
			} else {
				var diff = objectDiff(this.oldData[sym], campaigns[sym]);

				if (diff) {
					var result = await this.campaignModel.edit({ [LAB_CAMPAIGN_ID]: this.oldData[sym][LAB_CAMPAIGN_ID] }, diff);
					if (!result['result']) {
						return result;
					}
				}
			}
		}

		if (addData.length > 0) {
			var result = await this.campaignModel.adds(addData);
			if (!result['result']) {
				return result;
			}
		}

		this.modal('hide');
		return { result: true }
	}

}
export default LabTradeList
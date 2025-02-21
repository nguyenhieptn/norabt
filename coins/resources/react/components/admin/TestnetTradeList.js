import React, { Component } from 'react'
import Testnet_account from '../../model/admin/Testnet_account';
import Testnet_campaign from '../../model/admin/Testnet_campaign';
import Watchlist from '../../model/admin/Watchlist';
import Input from '../inputs/Input';

import Coinmarket from '../../model/admin/Coinmarket'

class TestnetTradeList extends Component {

	constructor(props) {
		super(props);
		this.id = makeId();

		this.state = {
			campaigns: {},
			account: {},
			watchlist: {},
			mapping: {},
			isHideUnselected: true,
			symbolSearch: ''
		}

		this.campaignModel = new Testnet_campaign();
		this.accountModel = new Testnet_account();
		this.wlModle = new Watchlist();

		this.oldData = {};

		this.campaignStruct = {

			[TESTNET_NAME]: {
				name: lang('Campaign Name'),
				flex: 1,
				type: 'text',
			},

			[TESTNET_STRATEGY]: {
				name: lang(TESTNET_STRATEGY),
				flex: 1,
				type: 'select',
				
			},

			[TESTNET_PRIORITY]: {
				name: lang(TESTNET_PRIORITY),
				flex: 1,
				type: 'number',

			},

			[TESTNET_SIDE]: {
				name: lang(TESTNET_SIDE),
				flex: 1,
				type: 'select',
				
			},
			
			[TESTNET_BUDGET]: {
				name: lang(TESTNET_BUDGET),
				flex: 1,
				type: 'number',
				default: 100,

			},
			[TESTNET_ACTIVE_BUDGET]: {
				name: lang(TESTNET_ACTIVE_BUDGET),
				flex: 1,
				type: 'number',
				default: 100,

			},

			[TESTNET_MONEY]: {
				name: lang(TESTNET_MONEY),
				flex: 1,
				type: 'number',
				default: 100,

			},

			[TESTNET_COMPOUND]: {
				name: lang(TESTNET_COMPOUND),
				flex: 1,
				type: 'select',
				

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
			if(res){
				if(res['result']){
					var mapping = res['data'];
					for(let i in mapping){
						mapping[i][''] = '-- Select --';
					}
					this.setState({mapping})
				}
			}
		})

		this.coinMarketData = await this.getRankCoinMarket()
		

		this.wlModle.getWatchlist().then(res => {
			
			if (res) {				
				this.setState({ watchlist: res });
			}
		})
	}


	async setAccount(account) {
		var campaigns = await this.getCampaigns(account[TESTNET_ACCOUNT_ID]);
		
		this.setState({
			campaigns, account, isHideUnselected: Object.keys(campaigns).length > 0
		})
	}


	getCampaigns(id) {
		
		return this.campaignModel.read({ [TESTNET_ACCOUNT]: id }).then(res => {
			if (res) {
				if (res['result']) {
					var oldData = {};
					var campaigns = {};
					for(let i in res['data']){
						oldData[res['data'][i][TESTNET_SYMBOL]] = {...res['data'][i]};
						campaigns[res['data'][i][TESTNET_SYMBOL]] = res['data'][i];
					}
					this.oldData = oldData;
					return campaigns;
				} else {
					error_handle(res);
				}
			}
		})
	}


	render() {

		var accountBalance = get(this.state.account[TESTNET_ACCOUNT_BALANCE], 0);
		var accountReserve = get(this.state.account[TESTNET_ACCOUNT_RESERVE], 0);
		var totalBallance = 0;
		var campaigns = this.state.campaigns;
		Object.keys(campaigns).map(item => totalBallance += Number(campaigns[item][TESTNET_BUDGET]));
		var reserve = Math.ceil(accountReserve * accountBalance * 1000 / 100)/1000;

		return (
			<>
				<div className="modal fade" id={"bladeModal" + this.id}>
					<div className="modal-dialog modal-lg modal-dialog-centered" style={{maxWidth:'90%'}}>
						<div className="modal-content">

							<div className="modal-header">
								<h4 className="modal-title">{this.state.account[TESTNET_ACCOUNT_NAME]}</h4>
								<button type="button" className="close" data-dismiss="modal">&times;</button>
							</div>

							<div className="modal-body" style={{ textAlign: 'initial' }}>
								<div className='box_flex' style={{ flexWrap:'wrap', color: accountBalance - reserve >= totalBallance ? 'green' : 'red' }}>
									Wallet balance: <input style={{ width: 100 }} className='input'
										value={Math.round(accountBalance * 100) / 100}
										onChange={(e) => {
											this.state.account[TESTNET_ACCOUNT_BALANCE] = e.target.value;
											this.setState({ account: this.state.account })
											this.isBalanceEdited = true;
										}}
										onBlur={e => {
											if (!this.isBalanceEdited) return;
											this.isBalanceEdited = false;
											this.accountModel.edit({ [TESTNET_ACCOUNT_ID]: this.state.account[TESTNET_ACCOUNT_ID] }, { [TESTNET_ACCOUNT_BALANCE]: e.target.value })
										}}
									></input>
									&nbsp;&nbsp;
									Used: <strong>{Math.round(totalBallance*100)/100}</strong>&nbsp;&nbsp;
									Free: <strong>{Math.round((accountBalance - totalBallance - reserve)*100)/100}</strong>&nbsp;&nbsp;
									Reserve(%): &nbsp; <input style={{width:30}} className='input' 
										value={accountReserve} 
										onChange={(e)=>{
											this.state.account[TESTNET_ACCOUNT_RESERVE] = e.target.value;
											this.setState({account: this.state.account})
											this.isReserveEdited = true;
										}}
										onBlur={e => {
											if(!this.isReserveEdited) return;
											this.isReserveEdited = false;
											this.accountModel.edit({[TESTNET_ACCOUNT_ID]: this.state.account[TESTNET_ACCOUNT_ID]}, {[TESTNET_ACCOUNT_RESERVE]: e.target.value})	
										}}
									></input>
									&nbsp;<b>({reserve} USDT)</b>

									<div className='button btn btn-info' onClick={()=>{
										var free = accountBalance - totalBallance - reserve;
										
										if(free < 0) return;
										var increate = Math.floor(free*1000/Object.keys(campaigns).length)/1000;
										for(let i in campaigns){
											let newBg = Number(campaigns[i][TESTNET_BUDGET])+increate;
											campaigns[i][TESTNET_BUDGET] = newBg;
											campaigns[i][TESTNET_MONEY] = newBg;
										}
										this.setState({campaigns})
									}}>Auto Arrange</div>

									
								<button type="button" className="btn btn-danger" onClick={() => {
									makeQuestion('Do you want to save and restart all Campaigns?').then(res => {
										if(res){
											this.accountModel.stopTrading(this.state.account[TESTNET_ACCOUNT_ID]).then(res=>{
												if(res['result']){
													var ids = res['data'];
													return this.saveData().then((res)=>{
														if(res['result']){
															this.accountModel.restartTrading(ids)
														}
													})
												}
												
											})
										}
									})
									
								}}>Save and Apply</button>

								<label className='box_flex' style={{margin:'auto 0px auto auto'}}>
									<input placeholder='Search Symbol' className='input' value={this.state.symbolSearch} onChange={e => this.setState({symbolSearch: e.target.value.toLocaleUpperCase()})}></input>
									&nbsp;
									<input type='checkbox' checked={this.state.isHideUnselected} 
									onChange={e => this.setState({isHideUnselected: !this.state.isHideUnselected})}></input>
									&nbsp;Hide Unselected
								</label>
									
								</div>


								{accountBalance - reserve < totalBallance && <div className="alert alert-danger">Not enough <strong className='button' onClick={()=>{
									var reducePercent = (totalBallance)/(accountBalance - reserve);
									for(let i in campaigns){
										let newBg = Math.floor(Number(campaigns[i][TESTNET_BUDGET]) * 1000 / reducePercent)/1000;
										campaigns[i][TESTNET_BUDGET] = newBg;
										campaigns[i][TESTNET_MONEY] = newBg;
									}
									this.setState({campaigns})
								}}>Fix it</strong></div>}


								<div className='box_flex'>
									<b>Selected: {Object.keys(this.state.campaigns).length}</b>&nbsp;&nbsp;
								</div>

								<div>

									<div className='box_flex'>
										<div className='box_flex' style={{flex:1, padding:5, margin:5}}>
											<label className='box_flex'>
												<input type="checkbox" checked={Object.keys(campaigns).length > 0} onChange={e => {
													if(e.target.checked){
														for(let i in this.state.watchlist){
															campaigns[i] = {
																[TESTNET_SYMBOL] : i,
																[TESTNET_ACCOUNT]: this.state.account[TESTNET_ACCOUNT_ID],
																[TESTNET_BUDGET]: 0,
																[TESTNET_MONEY]: 0,
																[TESTNET_STRATEGY]: ''

															}
														}
													}else{
														campaigns = {};
													}
													this.setState({campaigns});
												}}></input>
											&nbsp;
											<b>All</b>
											</label>
										</div>

										{Object.keys(this.campaignStruct).map(key => {
											let struct = this.campaignStruct[key];
											
											return <div key={key} style={{flex:struct.flex, textAlign:'center', padding:5}}>
												<div><b>{struct.name}</b></div>
												<div><Input className="input" 
													type = {struct.type} 
													Direct = {false} 
													Options = {get(this.state.mapping[key], {})}
													OnChangeBlur={(val) => {
														for(let i in campaigns){
															if(key == TESTNET_NAME){
																campaigns[i][key] = val + '-' + campaigns[i][TESTNET_SYMBOL];
															}else if(key == TESTNET_PRIORITY){
																campaigns[i][key] = val;
																val++;
															}else{
																campaigns[i][key] = val;
															}
															
														}
														this.setState({campaigns})
													}}
													OnChange = {val => {
														if(struct.type == 'select'){
															for(let i in campaigns){
																campaigns[i][key] = val;
															}
															this.setState({campaigns})
														}
													}}
													></Input></div>
											</div>
										})}

										

									</div>

									{Object.keys(this.state.watchlist).map((symbol) => {

										let show = isset(campaigns[symbol]);
										if(!this.state.isHideUnselected){
											show = true;
										}

										if(!symbol.includes(this.state.symbolSearch)){
											show = false
										}

										var rankData = (symbol == '1000SHIBUSDT' ? 'SHIBUSDT' : symbol);

										return <div key={symbol} className='box_flex box_shadow' style={{display: (show?'flex':'none')}}>

											<div className='box_flex' style={{flex:1, padding:5, margin:5}}>
												<label className='box_flex'>
												<input type="checkbox" checked={isset(campaigns[symbol])} onChange={e => {
													if(e.target.checked){
														campaigns[symbol] = {
															[TESTNET_SYMBOL] : symbol,
															[TESTNET_ACCOUNT]: this.state.account[TESTNET_ACCOUNT_ID],
															[TESTNET_BUDGET]: 0,
															[TESTNET_MONEY]: 0,
															[TESTNET_STRATEGY]: ''
														}
													}else{
														delete(campaigns[symbol]);
													}
													this.setState({campaigns});
												}}></input>
												&nbsp;
												{symbol}
												<span style={{ color: 'blue', fontWeight: 'normal' }}> [{get(this.coinMarketData[rankData], '')}]</span>
												</label>
											</div>

											{Object.keys(this.campaignStruct).map(key => {
												let struct = this.campaignStruct[key];
												if(!isset(campaigns[symbol])) return <div key={key} style={{flex:struct.flex, textAlign:'center', padding:5}}></div>
												return <div key={key} style={{flex:struct.flex, textAlign:'center', padding:5}}>
													<div><Input className="input" 
														type = {struct.type} 
														Direct = {true} 
														value = {get(campaigns[symbol][key], '')}
														OnChange = {val => {campaigns[symbol][key] = val; this.setState({campaigns})}}
														Options = {get(this.state.mapping[key], {})}
													></Input></div>
												</div>
											})}


										</div>
									})
									}
								</div>


							</div>

							<div className="modal-footer">

								<button type="button" className="btn btn-primary" onClick={() => {
									this.saveData()
								}}>Save</button>

								<button type="button" className="btn btn-danger" data-dismiss="modal">Close</button>
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
				var result = await this.campaignModel.delete({ [TESTNET_ID]: this.oldData[sym][TESTNET_ID] }, false);
				if (!result['result']) {
					return result;
				}
			}
		}

		for(let sym in campaigns){
			if(!isset(this.oldData[sym])){
				addData.push(campaigns[sym]);
			}else{
				var diff = objectDiff(this.oldData[sym], campaigns[sym]);
				
				if(diff){
					var result = await this.campaignModel.edit({[TESTNET_ID]: this.oldData[sym][TESTNET_ID]}, diff);
					if(!result['result']) {
						return result;
					}
				}
			}
		}
		if(addData.length > 0){
			var result = await this.campaignModel.adds(addData);
			if(!result['result']) {
				return result;
			}
		}

		this.modal('hide');
		return {result: true}
	}

}
export default TestnetTradeList
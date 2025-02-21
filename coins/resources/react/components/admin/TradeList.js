import React, { Component } from 'react'
import Accounts from '../../model/admin/Accounts';
import Trades from '../../model/admin/Trades';
import Watchlist from '../../model/admin/Watchlist';
import Style from '../common/Style'
import Input from '../input/Input';

class TradeList extends Component {

	constructor(props) {
		super(props);
		this.id = makeId();

		this.state = {
			traceList: [],
			account: {},
			ballance: 0,
			watchlist: {},
			update: 0,
			mapping: {},
			reserve : 0,
		}

		this.traceModel = new Trades();
		this.accountModel = new Accounts();
		this.wlModle = new Watchlist();

		this.oldData = {};
	}

	modal(cmd = 'show') {
		if (cmd == 'hide') {
			$("#bladeModal" + this.id).modal('hide');
		} else {
			$("#bladeModal" + this.id).modal();
		}
	}


	componentDidMount() {

		this.traceModel.map().then(res => {
			if(res){
				if(res['result']){
					var mapping = res['data'];
					for(let i in mapping){
						if( i == TRADE_STRATEGY){
							mapping[i][''] = '-- Select Strategy --';
						}else{
							mapping[i][''] = '-- Select --';
						}

					}
					this.setState({mapping})
				}
			}
		})

		this.wlModle.getWatchlist().then(res => {
			if (res) {
				res[''] = '-- Select Symbol --';
				this.setState({ watchlist: res });
			}
		})
	}


	async setAccount(id, name) {

		var account = {
			[ACCOUNT_ID]: id,
			[ACCOUNT_NAME]: name,
		}
		var traceList = await this.getTraceList(account[ACCOUNT_ID]);
		var ballanceData = await this.accountModel.getAvailableBallance(account[ACCOUNT_ID]);
		if (!ballanceData['result']) {
			error_handle(ballanceData);
			return;
		}
		var ballance = ballanceData['data']['availableBalance'];
		var reserve = ballanceData['data']['reserve'];
		this.setState({
			reserve, traceList, ballance, account, update: this.state.update + 1
		})


	}


	getTraceList(id) {
		
		return this.traceModel.read({ [TRADE_ACCOUNT]: id }).then(res => {
			if (res) {
				if (res['result']) {
					var oldData = {};
					for(let i in res['data']){
						oldData[res['data'][i][TRADE_ID]] = {...res['data'][i]};
					}
					this.oldData = oldData;
					return res['data'];
				} else {
					error_handle(res);
				}
			}
		})
	}


	render() {
		var totalBallance = 0;
		var traceList = this.state.traceList;
		traceList.map(item => totalBallance += Number(item[TRADE_BUDGET]));
		var reserve = Math.ceil(this.state.reserve * this.state.ballance / 100);
		return (
			<>
				<div className="modal fade" id={"bladeModal" + this.id}>
					<div className="modal-dialog modal-lg modal-dialog-centered">
						<div className="modal-content">

							<div className="modal-header">
								<h4 className="modal-title">{this.state.account[ACCOUNT_NAME]}</h4>
								<button type="button" className="close" data-dismiss="modal">&times;</button>
							</div>

							<div className="modal-body" style={{ textAlign: 'initial' }}>
								<div className='box_flex' style={{ color: this.state.ballance - reserve >= totalBallance ? 'green' : 'red' }}>
								Wallet balance: <strong>{Math.round(this.state.ballance*100)/100}</strong>&nbsp;&nbsp;
									Used: <strong>{Math.round(totalBallance*100)/100}</strong>&nbsp;&nbsp;
									Free: <strong>{Math.round((this.state.ballance - totalBallance - reserve)*100)/100}</strong>&nbsp;&nbsp;
									Reserve(%): &nbsp; <input style={{width:30}} className='input' 
										value={this.state.reserve} 
										onChange={(e)=>{
											this.setState({reserve: e.target.value})
											this.isReserveEdited = true;
										}}
										onBlur={e => {
											if(!this.isReserveEdited) return;
											this.isReserveEdited = false;
											this.accountModel.edit({[ACCOUNT_ID]: this.state.account[ACCOUNT_ID]}, {[ACCOUNT_RESERVE]: e.target.value})	
										}}
									></input>
									&nbsp;<b>({reserve} USDT)</b>
									<div className='button btn btn-info' onClick={()=>{
										var free = this.state.ballance - totalBallance - reserve;
										if(free < 0) return;
										var increate = Math.floor(free*1000/traceList.length)/1000;
										for(let i in traceList){
											traceList[i][TRADE_BUDGET] = Number(traceList[i][TRADE_BUDGET])+increate;
										}
										this.setState({traceList, update: this.state.update + 1})
									}}>Auto Arrange</div>

									
								<button type="button" className="btn btn-danger" onClick={() => {
									makeQuestion('Do you want to save and restart all Trading?').then(res => {
										if(res){
											this.accountModel.stopTrading(this.state.account[ACCOUNT_ID]).then(res=>{
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
									
								</div>
								{this.state.ballance - reserve < totalBallance && <div className="alert alert-danger">Not enough <strong className='button' onClick={()=>{
									var reducePercent = (totalBallance)/(this.state.ballance - reserve);
									for(let i in traceList){
										traceList[i][TRADE_BUDGET] = Math.floor(Number(traceList[i][TRADE_BUDGET]) * 1000 / reducePercent)/1000
									}
									this.setState({traceList, update: this.state.update + 1})
								}}>Fix it</strong></div>}

								<div key={this.state.update}>
									{traceList.map((item, key) => {


										return <div key={key} className='box_flex'>

											<div style={{ flex: 10, padding: 5 }}>
												<button className='button btn btn-danger btn-sm' onClick={e => {

													if (item[TRADE_ID]) {
														this.traceModel.delete({
															[TRADE_ID]: item[TRADE_ID],
															[TRADE_ACCOUNT]: item[TRADE_ACCOUNT],
															[TRADE_SYMBOL]: item[TRADE_SYMBOL]
														}).then(res=>{
															if(res && res['result']){
																traceList.splice(key, 1);
																this.setState({traceList, update: this.state.update + 1});
															}
														})
													}else{
														traceList.splice(key, 1);
														this.setState({traceList, update: this.state.update + 1});
													}

													

												}} style={{ width: '100%' }}>{lang('Delete')}</button>
											</div>


											<div style={{ flex: 30, padding: 5, minWidth: 50 }}>

												<Input className='input' placeholder={lang(TRADE_SYMBOL)} struct={{
													[INPUT_TYPE]: 'select',
													[INPUT_DEFAULT]: item[TRADE_SYMBOL],
													[INPUT_NULL]: false,
													[INPUT_OPTION]: get(this.state.mapping[TRADE_SYMBOL], {}),
													[INPUT_ONCHANGE]: (e, obj) => {
														var val = obj.input.getValue();

														traceList[key][TRADE_SYMBOL] = val;
														this.setState({traceList});

													}
												}}></Input>

											</div>


											<div style={{ flex: 20, padding: 5 }}>

												<Input className='input' placeholder={lang(TRADE_BUDGET) + ' (USDT)'} struct={{
													[INPUT_TYPE]: 'number',
													[INPUT_DEFAULT]: item[TRADE_BUDGET],
													[INPUT_NULL]: false,
													[INPUT_ONCHANGE_BLUR]: (e, obj) => {
														var val = obj.input.getValue();
														traceList[key][TRADE_BUDGET] = val;
														this.setState({traceList});
													}
												}}></Input>
											</div>


											<div style={{ flex: 20, padding: 5 }}>

												<Input className='input' placeholder={lang(TRADE_ACTION_BUDGET) + ' (%)'} struct={{
													[INPUT_TYPE]: 'number',
													[INPUT_DEFAULT]: item[TRADE_ACTION_BUDGET],
													[INPUT_NULL]: false,
													[INPUT_ONCHANGE_BLUR]: (e, obj) => {
														var val = obj.input.getValue();
														traceList[key][TRADE_ACTION_BUDGET] = val;
														this.setState({traceList});
													},
													[INPUT_OPTION]: this.typeOptions
												}}></Input>
											</div>

											<div style={{ flex: 20, padding: 5, minWidth: 50 }}>

												<Input className='input' placeholder={lang(TRADE_STRATEGY)} struct={{
													[INPUT_TYPE]: 'select',
													[INPUT_NULL]: false,
													[INPUT_DEFAULT]: item[TRADE_STRATEGY],
													[INPUT_OPTION]: get(this.state.mapping[TRADE_STRATEGY], {}),
													[INPUT_ONCHANGE]: (e, obj) => {
														var val = obj.input.getValue();

														traceList[key][TRADE_STRATEGY] = val;
														this.setState({traceList});

													}
												}}></Input>

											</div>

											<div style={{ flex: 20, padding: 5, minWidth: 50 }}>
												<div className='button btn btn-info' onClick={()=>{
													var free = this.state.ballance - totalBallance - reserve;
													free = Math.floor(free*1000)/1000;
													if(free < 0) return;
													traceList[key][TRADE_BUDGET] = Number(traceList[key][TRADE_BUDGET])+free;
													this.setState({traceList, update: this.state.update + 1})
												}}>All Free</div>
											</div>


										</div>
									})
									}
								</div>


							</div>

							<div className="modal-footer">

								<button type="button" className="btn btn-warning" onClick={() => {
									var coins = get(this.state.mapping[TRADE_SYMBOL], {});
									var index = {};
									for( let i in traceList){
										index[traceList[i][TRADE_SYMBOL]] = true;
									}
									for(let i in coins){
										if(!isset(index[i])){
											traceList.push({
												[TRADE_SYMBOL]: i,
												[TRADE_BUDGET]: '',
												[TRADE_ACTION_BUDGET]: '',
											});
										}
										
									}
									
									this.setState({traceList});
								}}>Add all Coins</button>

								<button type="button" className="btn btn-warning" onClick={() => {
									traceList.push({
										[TRADE_SYMBOL]: '',
										[TRADE_BUDGET]: '',
										[TRADE_ACTION_BUDGET]: '',
									});
									this.setState({traceList});
								}}>Add</button>

								<button type="button" className="btn btn-primary" onClick={() => {
									this.saveData()
								}}>Save</button>
{/* 
								<button type="button" className="btn btn-danger" onClick={() => {
									makeQuestion('Do you want to save and restart all Trading?').then(res => {
										if(res){
											this.accountModel.stopTrading(this.state.account[ACCOUNT_ID]).then(res=>{
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
									
								}}>Save and Apply</button> */}

								<button type="button" className="btn btn-danger" data-dismiss="modal">Close</button>
							</div>

						</div>
					</div>
				</div>

			</>
		)
	}



	async saveData() {
		var trades = this.state.traceList;

		for (let i in trades) {
			if (trades[i][TRADE_SYMBOL] != '')
				if (trades[i][TRADE_ID]) {
					var id = trades[i][TRADE_ID];
					
					if(isset(this.oldData[id])){
						if(trades[i][TRADE_SYMBOL] == this.oldData[id][TRADE_SYMBOL]
							&& trades[i][TRADE_BUDGET] == this.oldData[id][TRADE_BUDGET]
							&& trades[i][TRADE_ACTION_BUDGET] == this.oldData[id][TRADE_ACTION_BUDGET]
							&& trades[i][TRADE_STRATEGY] == this.oldData[id][TRADE_STRATEGY]	
						) continue;
					}

					var result = await this.traceModel.edit(
						{
							[TRADE_ACCOUNT]: this.state.account[ACCOUNT_ID],
							[TRADE_SYMBOL]: trades[i][TRADE_SYMBOL]
						},
						{
							[TRADE_SYMBOL]: trades[i][TRADE_SYMBOL],
							[TRADE_BUDGET]: trades[i][TRADE_BUDGET],
							[TRADE_ACTION_BUDGET]: trades[i][TRADE_ACTION_BUDGET],
							[TRADE_STRATEGY]: trades[i][TRADE_STRATEGY],
						}
					)

					if(!result['result']) {
						error_handle(result);
						return result;
					}
					
				} else {

					var result = await this.traceModel.add(
						{
							[TRADE_ACCOUNT]: this.state.account[ACCOUNT_ID],
							[TRADE_SYMBOL]: trades[i][TRADE_SYMBOL],
							[TRADE_BUDGET]: trades[i][TRADE_BUDGET],
							[TRADE_ACTION_BUDGET]: trades[i][TRADE_ACTION_BUDGET],
							[TRADE_STRATEGY]: trades[i][TRADE_STRATEGY],
						}
					)

					if(!result['result']) {
						error_handle(result);
						return result;
					}

				}
		}
		this.modal('hide');
		this.getTraceList();
		return {result: true};
	}

}
export default TradeList
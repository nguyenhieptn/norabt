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
		}

		this.traceModel = new Trades();
		this.accountModel = new Accounts();
		this.wlModle = new Watchlist();
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
						mapping[i][''] = '-- Select --'
					}
					this.setState({mapping})
				}
			}
		})

		this.wlModle.getWatchlist().then(res => {
			if (res) {
				res[''] = '-- Select --';
				this.setState({ watchlist: res });
			}
		})
	}


	async setAccount(account) {

		var traceList = await this.getTraceList(account[ACCOUNT_ID]);
		var ballance = await this.accountModel.getAvailableBallance(account[ACCOUNT_ID]);
		if (!ballance['result']) {
			error_handle(ballance);
			return;
		}
		ballance = ballance['data']['availableBalance'];

		this.setState({
			traceList, ballance, account
		})


	}


	getTraceList(id) {
		return this.traceModel.read({ [TRADE_ACCOUNT]: id }).then(res => {
			if (res) {
				if (res['result']) {
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
								<div style={{ color: this.state.ballance >= totalBallance ? 'green' : 'red' }}>
									Ballance: <strong>{Math.round(this.state.ballance*100)/100}</strong>&nbsp;&nbsp;
									Used: <strong>{Math.round(totalBallance*100)/100}</strong>&nbsp;&nbsp;
									Free: <strong>{Math.round((this.state.ballance - totalBallance)*100)/100}</strong>&nbsp;&nbsp;
								</div>
								{this.state.ballance < totalBallance && <div className="alert alert-danger">Not enough <strong className='button' onClick={()=>{
									var reducePercent = totalBallance/this.state.ballance;
									for(let i in traceList){
										var bg = Number(traceList[i][TRADE_BUDGET]) / reducePercent;
										traceList[i][TRADE_BUDGET] = bg;
										traceList[i][TRADE_MONEY] = bg;
									}
									this.setState({traceList, update: this.state.update + 1})
								}}>Fix it</strong></div>}

								<div key={this.state.update}>
									{traceList.map((item, key) => {


										return <div key={key} className='box_flex'>

											<div style={{ width: '10%', padding: 5 }}>
												<button className='button btn btn-danger btn-sm' onClick={e => {

													if (item[TRADE_ID]) {
														this.traceModel.delete({
															[TRADE_ID]: item[TRADE_ID],
															[TRADE_ACCOUNT]: item[TRADE_ACCOUNT],
															[TRADE_SYMBOL]: item[TRADE_SYMBOL]
														}).then(res=>{
															if(res && res['result']){
																traceList.splice(key, 1);
																this.setState(traceList);
															}
														})
													}else{
														traceList.splice(key, 1);
														this.setState(traceList);
													}

													

												}} style={{ width: '100%' }}>{lang('Delete')}</button>
											</div>


											<div style={{ width: '30%', padding: 5, minWidth: 50 }}>

												<Input className='input' placeholder={lang(TRADE_SYMBOL)} struct={{
													[INPUT_TYPE]: 'select',
													[INPUT_DEFAULT]: item[TRADE_SYMBOL],
													[INPUT_NULL]: false,
													[INPUT_OPTION]: get(this.state.mapping[TRADE_SYMBOL], {}),
													[INPUT_ONCHANGE]: (e, obj) => {
														var val = obj.input.getValue();

														traceList[key][TRADE_SYMBOL] = val;
														this.setState(traceList);

													}
												}}></Input>

											</div>


											<div style={{ width: '20%', padding: 5 }}>

												<Input className='input' placeholder={lang(TRADE_BUDGET) + ' (USDT)'} struct={{
													[INPUT_TYPE]: 'number',
													[INPUT_DEFAULT]: item[TRADE_BUDGET],
													[INPUT_NULL]: false,
													[INPUT_ONCHANGE_BLUR]: (e, obj) => {
														var val = obj.input.getValue();
														traceList[key][TRADE_BUDGET] = val;
														this.setState(traceList);
													}
												}}></Input>
											</div>


											<div style={{ width: '20%', padding: 5 }}>

												<Input className='input' placeholder={lang(TRADE_ACTION_BUDGET) + ' (%)'} struct={{
													[INPUT_TYPE]: 'number',
													[INPUT_DEFAULT]: item[TRADE_ACTION_BUDGET],
													[INPUT_NULL]: false,
													[INPUT_ONCHANGE_BLUR]: (e, obj) => {
														var val = obj.input.getValue();
														traceList[key][TRADE_ACTION_BUDGET] = val;
														this.setState(traceList);
													},
													[INPUT_OPTION]: this.typeOptions
												}}></Input>
											</div>

											<div style={{ width: '20%', padding: 5, minWidth: 50 }}>

												<Input className='input' placeholder={lang(TRADE_PARAM)} struct={{
													[INPUT_TYPE]: 'select',
													[INPUT_NULL]: false,
													[INPUT_DEFAULT]: item[TRADE_PARAM],
													[INPUT_OPTION]: get(this.state.mapping[TRADE_PARAM], {}),
													[INPUT_ONCHANGE]: (e, obj) => {
														var val = obj.input.getValue();

														traceList[key][TRADE_PARAM] = val;
														this.setState(traceList);

													}
												}}></Input>

											</div>


										</div>
									})
									}
								</div>


							</div>

							<div className="modal-footer">
								<button type="button" className="btn btn-warning" onClick={() => {
									traceList.push({
										[TRADE_SYMBOL]: '',
										[TRADE_BUDGET]: '',
										[TRADE_ACTION_BUDGET]: '',
										[TRADE_PARAM]: '',
									});
									this.setState(traceList);
								}}>Add</button>
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
		var trades = this.state.traceList;

		for (let i in trades) {
			if (trades[i][TRADE_SYMBOL] != '')
				if (trades[i][TRADE_ID]) {

					await this.traceModel.edit(
						{
							[TRADE_ACCOUNT]: this.state.account[ACCOUNT_ID],
							[TRADE_SYMBOL]: trades[i][TRADE_SYMBOL]
						},
						{
							[TRADE_SYMBOL]: trades[i][TRADE_SYMBOL],
							[TRADE_BUDGET]: trades[i][TRADE_BUDGET],
							[TRADE_ACTION_BUDGET]: trades[i][TRADE_ACTION_BUDGET],
							[TRADE_PARAM]: trades[i][TRADE_PARAM],
						}
					)
					
				} else {

					await this.traceModel.add(
						{
							[TRADE_ACCOUNT]: this.state.account[ACCOUNT_ID],
							[TRADE_SYMBOL]: trades[i][TRADE_SYMBOL],
							[TRADE_BUDGET]: trades[i][TRADE_BUDGET],
							[TRADE_ACTION_BUDGET]: trades[i][TRADE_ACTION_BUDGET],
							[TRADE_PARAM]: trades[i][TRADE_PARAM],
						}
					)

				}
		}
		this.modal('hide');
		this.getTraceList();
	}

}
export default TradeList
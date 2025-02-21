import React, { Component } from 'react'

import '../../components/Dashboard/index.scss';

import Lab_results from '../../model/admin/Lab_results'
import Lab_campaigns from '../../model/admin/Lab_campaigns'
import Lab_account from '../../model/admin/Lab_account'
import Strategy from '../../model/admin/Lab_strategies'
import ChartLSProfitPerDay from '../../components/Dashboard/ChartLSProfitPerDay';
import ChartStrategy from '../../components/Dashboard/ChartStrategy';

import Input from '../../components/input/Input'
import ChartProfitPerDay from '../../components/admin/ChartProfitPerDay';
import ChartMaxOrder from '../../components/admin/ChartMaxOrder';
import ChartAvgCoinStrategy from '../../components/admin/ChartAvgCoinStrategy';
import ChartParse from '../../components/admin/ChartParse';
import ChartPNLDaily from '../../components/Dashboard/ChartPNLDaily';
import ChartPNLAccumulated from '../../components/Dashboard/ChartPNLAccumulated';
import ChartPNLProfit from '../../components/Dashboard/ChartPNLProfit';
import ChartFlow from '../../components/Dashboard/ChartFlow';
import ChartAvgTime from '../../components/Dashboard/ChartAvgTime';
import ChartFlowRisky1 from '../../components/Dashboard/ChartFlowRisky1';
import ChartFlowRisky3 from '../../components/Dashboard/ChartFlowRisky3';
import ChartFlowSafe from '../../components/Dashboard/ChartFlowSafe';
import ChartFlowRisky2 from '../../components/Dashboard/ChartFlowRisky2';
import ChartFlowRisky4 from '../../components/Dashboard/ChartFlowRisky4';
import ChartBalance from '../../components/Dashboard/ChartBalance';
import ChartContainer from '../../components/admin/ChartContainer';
import ChartProfitPhase from '../../components/admin/ChartProfitPhase';
import ChartStopLoss from '../../components/Dashboard/ChartStopLoss';
import ChartStopLossPer from '../../components/Dashboard/ChartStopLossPer';
import ChartBalanceMax from '../../components/Dashboard/ChartBalanceMax';
import ChartFlow15m from '../../components/Dashboard/ChartFlow15m';
import ChartFlow1hLong from '../../components/Dashboard/ChartFlow1hLong';
import ChartTotalOrderPerPhase from '../../components/Dashboard/ChartTotalOrderPerPhase';
import ChartTotalRealProfitPerFlow from '../../components/Dashboard/ChartTotalRealProfitPerFlow';
import ChartTotalRealPNLPerFlow from '../../components/Dashboard/ChartTotalRealPNLPerFlow';
import ChartTotalRealPNLPerFlowPerStrategy from '../../components/Dashboard/ChartTotalRealPNLPerFlowPerStrategy';
import ChartTotalRealProfitPerStrategy from '../../components/Dashboard/ChartTotalRealProfitPerStrategy ';


class DashboardView extends Component {

	constructor(props) {
		super(props);
		this.state = {
			strategy: null,
			count: 1,
			totalProfit: 0,
			totalProfitDay: 0,
			totalLongShort: 0,
			totalTakeprofitstoploss: 0,
			watchlist: [],
			lab: [],
			totalInvestment: 0,
			totalProfit2: 0,
			Per: 0,

			totalPosition: 0,
			winrate : 0

		};

		this.startDate = 0;
		this.stopDate = moment().format('x');
		this.strategy = null;

	}


	render() {

		return (

			<div>
				<div className='p-grid dashboard' >
					<div className='p-col-12 p-lg-3' >
						<div className='box-cus box-1 '>
							<div className='box-cus-title'>
								<i className="pi pi-money-bill"></i>
								{/* <span>Total Profit / Today</span> */}
								<span>Total Investment</span>

							</div>
							<div className="overview-box-count">{`${formatNumber(this.state.totalInvestment)}`}</div>
						</div>

					</div>
					<div className='p-col-12 p-lg-3' >
						<div className='box-cus box-2'>
							<div className='box-cus-title'>
								<i className="pi pi-shopping-cart"></i>
								{/* <span className='box-cus-title'>Total LONG / SHORT</span> */}
								<span className='box-cus-title'>Total Profit / %</span>

							</div>
							<div className="overview-box-count">{`${formatNumber(this.state.totalProfit2)} / ${formatNumber(this.state.Per)}`}</div>
						</div>

					</div>

					<div className='p-col-12 p-lg-3' >
						<div className='box-cus box-3'>
							<div className='box-cus-title'>
								<i className="pi pi-chart-bar"></i>
								{/* <span className='box-cus-title'>Total Take Profit / Stoploss</span> */}
								{/* <span className='box-cus-title'>Total Position</span> */}
								<span className='box-cus-title'>Total LONG / SHORT</span>

							</div>
							{/* <div className="overview-box-count">{this.state.totalTakeprofitstoploss}</div> */}
							{/* <div className="overview-box-count">{this.state.totalPosition}</div> */}
							<div className="overview-box-count">{this.state.totalLongShort}</div>
						</div>
					</div>


					<div className='p-col-12 p-lg-3' >
						<div className='box-cus box-4'>
							<div className='box-cus-title'>
								<i className="pi pi-star-o"></i>
								{/* <span className='box-cus-title'>Total Crypto Online / Offline</span> */}
								{/* <span className='box-cus-title'>Total LONG / SHORT</span> */}
								{/* <span className='box-cus-title'>Total Take Profit / Stoploss</span> */}
								<span className='box-cus-title'>Winrate</span>

							</div>
							{/* <div className="overview-box-count">{this.state.totalTakeprofitstoploss}</div> */}
							{/* <div className="overview-box-count">{this.state.totalLongShort}</div> */}
							<div className="overview-box-count">{this.state.winrate}</div>

						</div>

					</div>

			

					{/* <ChartBalance ref={c => this.ChartBalance = c}></ChartBalance> */}
					{/* <ChartBalanceMax key={makeId()}></ChartBalanceMax> */}

					<ChartPNLDaily ref={c => this.ChartPNLDaily = c}></ChartPNLDaily>

					<ChartPNLProfit ref={c => this.ChartPNLProfit = c}></ChartPNLProfit>

					<ChartPNLAccumulated totalInvestment={this.state.totalInvestment} ref={c => this.ChartPNLAccumulated = c}></ChartPNLAccumulated>
					<ChartLSProfitPerDay key={makeId()} />
					<ChartTotalOrderPerPhase ref={c => this.ChartTotalOrderPerPhase = c}></ChartTotalOrderPerPhase>
					<ChartTotalRealProfitPerFlow ref={c => this.ChartTotalRealProfitPerFlow = c}></ChartTotalRealProfitPerFlow>
					<ChartTotalRealProfitPerStrategy ref={c => this.ChartTotalRealProfitPerStrategy= c} ></ChartTotalRealProfitPerStrategy>
					
					<ChartTotalRealPNLPerFlow ref={c => this.ChartTotalRealPNLPerFlow = c}></ChartTotalRealPNLPerFlow>
					<ChartTotalRealPNLPerFlowPerStrategy ref={c => this.ChartTotalRealPNLPerFlowPerStrategy = c}></ChartTotalRealPNLPerFlowPerStrategy>
					<div className='p-col-12 p-md-12 ' style={{ position: 'relative' }} >
						{!App.isMobile() &&
							<div style={{ display: 'flex', height: '300px', position: 'absolute', top: 50, right: 36, zIndex: 100 }}>

								<div style={{ width: '30%', marginRight: '10px' }}>
									<Input placeholder="Select Date" ref={c => this.day = c} className='input' struct={{
										[INPUT_TYPE]: 'date',
										[INPUT_NULL]: true,
										[INPUT_FORMAT]: 'DD/MM/YYY',
										[INPUT_ONBLUR]: (e, obj) => {
											var val = obj.input.getValue();
											this.startDate = moment(val, 'X').startOf("day").format('x');
											this.stopDate = moment(val, 'X').endOf("day").format('x');
											this.inputFromDate.setValue(this.startDate / 1000);
											this.inputEndDate.setValue(this.stopDate / 1000);
											this.getData();
										}
									}}></Input>
								</div>

								<div style={{ width: '30%', marginRight: '10px' }}>
									<Input placeholder="From" ref={c => this.inputFromDate = c} className='input' struct={{
										[INPUT_TYPE]: 'date',
										[INPUT_NULL]: true,
										[INPUT_ONBLUR]: (e, obj) => {
											var val = obj.input.getValue();
											this.startDate = moment(val, 'X').format('x');
											this.getData();
										}
									}}></Input>
								</div>

								<div style={{ width: '30%', marginRight: '10px' }}>
									<Input placeholder="To" ref={c => this.inputEndDate = c} className='input' struct={{
										[INPUT_TYPE]: 'date',
										[INPUT_NULL]: true,
										[INPUT_ONBLUR]: (e, obj) => {
											var val = obj.input.getValue();
											this.stopDate = moment(val, 'X').format('x');
											this.getData();
										}
									}}></Input>
								</div>

							</div>
						}

						<ChartStrategy key={makeId()} />
					</div>
					<ChartStopLoss ref={c => this.ChartStopLoss = c}></ChartStopLoss>
					<ChartStopLossPer ref={c => this.ChartStopLossPer = c} ></ChartStopLossPer>
					<ChartAvgCoinStrategy ref={c => this.ChartAvgCoinStrategy = c}></ChartAvgCoinStrategy>
					
					

					
					<ChartFlow ref={c => this.ChartFlow = c}></ChartFlow>
					{/* <ChartFlow15m ref={c => this.ChartFlow15m = c}></ChartFlow15m> */}
					{/* <ChartFlow1hLong ref={c => this.ChartFlow1hLong = c}></ChartFlow1hLong> */}
					<ChartFlowSafe ref={c => this.ChartFlowSafe = c} ></ChartFlowSafe>
					<ChartFlowRisky1 ref={c => this.ChartFlowRisky1 = c} ></ChartFlowRisky1>
					<ChartFlowRisky2 ref={c => this.ChartFlowRisky2 = c}></ChartFlowRisky2>
					<ChartFlowRisky3 ref={c => this.ChartFlowRisky3 = c}> </ChartFlowRisky3>
					{/* <ChartFlowRisky4 ref={c => this.ChartFlowRisky4 = c} ></ChartFlowRisky4> */}

					<ChartAvgTime ref={c => this.ChartAvgTime = c}></ChartAvgTime>
				
					





					{/* <ChartProfitPerDay ref={c => this.profitPerDayChart = c}></ChartProfitPerDay> */}

					<ChartProfitPhase ref={c => this.ChartProfitPhase = c} ></ChartProfitPhase>


					<ChartParse ref={c => this.ChartParse = c} ></ChartParse>
					<ChartContainer ref={c => this.ChartContainer = c}></ChartContainer>

					<ChartMaxOrder></ChartMaxOrder>







				</div>

			</div>


		)
	}

	async getData() {

		var start = this.startDate;
		var end = this.stopDate;

		var lab = new Lab_results();

		// var res = await lab.get([[[LAB_RESULT_ACCOUNT, '=', App.accountSelectorLab.selected()], [LAB_RESULT_ORDER_TIME, '>', start], [LAB_RESULT_ORDER_TIME, '<', end]]]);
		var res = await lab.get([[[LAB_RESULT_ACCOUNT, '=', App.accountSelectorLab.selected()]]]);
		App.getStrategy = res.data;
		var totalProfit = 0;
		var totalLong = 0;
		var totalShort = 0;
		var totalTakeProfit = 0;
		var totalStopLoss = 0;

		var totalPosition = res.data.length;

		Object.values(res.data).map(data => {

			if (data[LAB_RESULT_PENDING] == 0) {
				totalProfit += Number(data[LAB_RESULT_REAL_PROFIT]);
			}

			if (data[LAB_RESULT_TYPE] == [LAB_RESULT_TYPE_LONG]) {
				totalLong++;
			}
			if (data[LAB_RESULT_TYPE] == [LAB_RESULT_TYPE_SHORT]) {
				totalShort++;
			}

			if (data[LAB_RESULT_STATUS] == [LAB_RESULT_STATUS_TAKEPROFIT]) {
				totalTakeProfit++;
			}
			if (data[LAB_RESULT_STATUS] == [LAB_RESULT_STATUS_STOPLOSS]) {
				totalStopLoss++;
			}

		})

		this.setState({
			totalProfit: totalProfit.toFixed(3),
			totalLongShort: `${formatNumber(totalLong)} / ${formatNumber(totalShort)}`,
			totalTakeprofitstoploss: `${formatNumber(totalTakeProfit)} / ${formatNumber(totalStopLoss)}`,
			totalPosition: `${formatNumber(totalPosition)}`,
			winrate : ((totalTakeProfit / totalPosition) * 100).toFixed(2) + '%'
		})
		// var start1;
		// var end1;
		// start1 = moment().startOf("day").format('X');
		// end1 = moment().format('X');

		// var resday = await lab.get([[[LAB_RESULT_STRATEGY, '=', strategy], [LAB_RESULT_ORDER_TIME, '>', start1], [LAB_RESULT_ORDER_TIME, '<', end1]]]);

		// var totalProfit = 0;
		// Object.values(resday.data).map(data => {

		// 	if (data[LAB_RESULT_PENDING] == 0) {
		// 		totalProfit += Number(data[LAB_RESULT_REAL_PROFIT]);
		// 	}
		// })
		// this.setState({
		// 	totalProfitDay: totalProfit.toFixed(3)
		// })
	}

	async getDataLabCampaigns() {
		var resultModel = new Lab_campaigns();

		var accountModel = new Lab_account();

		var accountData = await accountModel.read({ [LAB_ACCOUNT_ID]: App.accountSelectorLab.selected() });
		var reserve = 100 - Number(accountData['data'][0][LAB_ACCOUNT_RESERVE]);
		var balance = accountData['data'][0][LAB_ACCOUNT_BALANCE];
		// balance = Math.round(balance * 100) / 100;



		// resultModel.read({ [LAB_CAMPAIGN_ACCOUNT]: App.accountSelectorLab.selected() }).then(res => {
		var res = await resultModel.read({ [LAB_CAMPAIGN_ACCOUNT]: App.accountSelectorLab.selected() })
		var totalProfit = 0;
		var totalInvestment = 0;
		if (res['data']) {
			res = res['data'];

			
			var totalProfit2 = 0;

		

			for (let i in res) {
				totalInvestment += res[i][LAB_CAMPAIGN_MONEY];

				// totalProfit += res[i][LAB_CAMPAIGN_BUDGET] - res[i][LAB_CAMPAIGN_MONEY];

			}
			
			totalInvestment = totalInvestment / reserve * 100;

			totalProfit = balance - totalInvestment;

			this.setState({
				totalInvestment: Math.round(totalInvestment * 100) / 100,
				totalProfit2: Math.round(totalProfit * 100) / 100,
				// totalProfit2: Math.round(totalProfit * 100) / 100,
				// Per: (((balance - totalInvestment) / totalInvestment) * 100).toFixed(2)
				Per: ((totalProfit / totalInvestment) * 100).toFixed(2)
			});

		}

	}

	componentDidMount() {

		// if (App.strategySelector) {
		// 	App.strategySelector.register('dashboard_view', (strategy) => {
		// 		if (!strategy) return;
		// 		this.strategy = strategy[LAB_STRATEGY_ID];
		// 		this.stopDate = moment().format('x');
		// 		this.getData();
		// 		this.getDataLabCampaigns();
		// 		// this.profitPerDayChart.getData();




		// 	})
		// 	App.strategySelector.selectStrategy();
		// }
		if (App.accountSelectorLab) {
			App.accountSelectorLab.register('dashboard_view', () => {
				this.getData();
				this.getDataLabCampaigns();

				// this.ChartPNLDaily.getData();
				// this.ChartFlow15m.getData();
				// this.ChartFlow1hLong.getData();
				this.ChartFlow.getData();
				this.ChartFlowRisky1.getData();
				this.ChartFlowRisky2.getData();
				this.ChartFlowRisky3.getData();
				// this.ChartFlowRisky4.getData();
				this.ChartFlowSafe.getData();
				this.ChartAvgTime.getData();
				this.ChartPNLDaily.getData('week');
				this.ChartPNLAccumulated.getData();
				this.ChartPNLProfit.getData();
				this.ChartAvgCoinStrategy.getData();
				this.ChartParse.getData();
				// this.ChartBalance.getData();
				this.ChartContainer.getData();
				this.ChartProfitPhase.getData();

				this.ChartStopLoss.getData();
				this.ChartStopLossPer.getData();

				this.ChartTotalOrderPerPhase.getData();
				this.ChartTotalRealProfitPerFlow.getData();
				this.ChartTotalRealPNLPerFlow.getData();
				this.ChartTotalRealPNLPerFlowPerStrategy.getData();
				this.ChartTotalRealProfitPerStrategy.getData();


			})
			this.getData();
			this.getDataLabCampaigns();
			this.ChartPNLDaily.getData('week');
			// this.ChartFlow15m.getData();
			// this.ChartFlow1hLong.getData();
			this.ChartFlow.getData();
			this.ChartFlowRisky1.getData();
			this.ChartFlowRisky2.getData();
			this.ChartFlowRisky3.getData();
			// this.ChartFlowRisky4.getData();
			this.ChartFlowSafe.getData();
			this.ChartAvgTime.getData();
			this.ChartPNLProfit.getData();
			this.ChartPNLAccumulated.getData();
			this.ChartAvgCoinStrategy.getData();
			this.ChartParse.getData();
			// this.ChartBalance.getData();
			this.ChartContainer.getData();
			this.ChartProfitPhase.getData();

			this.ChartStopLoss.getData();
			this.ChartStopLossPer.getData();
			this.ChartTotalOrderPerPhase.getData();
			this.ChartTotalRealProfitPerFlow.getData();
			this.ChartTotalRealPNLPerFlow.getData();
			this.ChartTotalRealPNLPerFlowPerStrategy.getData();
			this.ChartTotalRealProfitPerStrategy.getData();


		}




	}

	componentWillUnmount() {
		// if (this.updateInterval) clearInterval(this.updateInterval);
		if (App.accountSelectorLab) {
			App.accountSelectorLab.unregister('dashboard_view');
		}


	}


}
export default DashboardView
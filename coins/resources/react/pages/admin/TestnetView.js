import React, { Component } from 'react'

import '../../components/Dashboard/index.scss';
import Watchlist from '../../model/admin/Watchlist'
import ChartLongShort from '../../components/Dashboard/ChartLongShort';
import ChartProfitPerDay from '../../components/Dashboard/Testnet/ChartProfitPerDay';
import ChartLSProfitPerDay from '../../components/Dashboard/Testnet/ChartLSProfitPerDay';
import ChartCryptoPerDay from '../../components/Dashboard/Testnet/ChartCryptoPerDay';
import LSPerDay from '../../components/Dashboard/LSPerDay';
import Input from '../../components/input/Input'
import Testnet_results from '../../model/admin/Testnet_results';
import Testnet_campaigns from '../../model/admin/Testnet_campaign';
import Strategies from '../../model/admin/Strategies';
import ChartProfitStrategy from '../../components/Dashboard/Testnet/ChartProfitStrategy';
import TestnetChartLine from '../../components/admin/TestnetChartLine';
import Testnet_campaign from '../../model/admin/Testnet_campaign';
import ChartAvgCoinStrategy from '../../components/Dashboard/Testnet/ChartAvgCoinStrategy';
import ChartPNLDaily from '../../components/Dashboard/Testnet/ChartPNLDaily';
import ChartPNLAccumulated from '../../components/Dashboard/Testnet/ChartPNLAccumulated';
import ChartPNLProfit from '../../components/Dashboard/Testnet/ChartPNLProfit';
import ChartFlow from '../../components/Dashboard/Testnet/ChartFlow';
import ChartFlowSafe from '../../components/Dashboard/Testnet/ChartFlowSafe';

import ChartFlowRisky1 from '../../components/Dashboard/Testnet/ChartFlowRisky1';
import ChartFlowRisky3 from '../../components/Dashboard/Testnet/ChartFlowRisky3';
import ChartFlowRisky2 from '../../components/Dashboard/Testnet/ChartFlowRisky2';
import ChartFlowRisky4 from '../../components/Dashboard/Testnet/ChartFlowRisky4';
import ChartAvgTime from '../../components/Dashboard/Testnet/ChartAvgTime';
import ChartParse from '../../components/Dashboard/Testnet/ChartParse';
import ChartBalance from '../../components/Dashboard/Testnet/ChartBalance';
import Testnet_account from '../../model/admin/Testnet_account';
import ChartStopLoss from '../../components/Dashboard/Testnet/ChartStopLoss';
import ChartStopLossPer from '../../components/Dashboard/Testnet/ChartStopLossPer';
class TestnetView extends Component {

	constructor(props) {
		super(props);
		this.state = {
			count: 0,
			totalProfit: 0,
			totalProfitDay: 0,
			totalLongShort: 0,
			totalTakeprofitstoploss: 0,
			watchlist: [],
			lab: [],
			totalCoin: 0,
			trading: 0,

			totalInvestment: 0,
			totalProfit2: 0,
			Per: 0,
			winrate : 0



		};
	}


	render() {


		return (

			<div>
				<div className='p-grid dashboard' >
					{/* <div className='p-col-12 p-md-6 p-lg-3 d-flex' >
						<div className='box-cus box-1' style={{ width: '100%' }}>
							<div className='box-cus-title'>
								<i className="pi pi-money-bill"></i>
								<span className='box-cus-title'>Total Profit / Today</span>

							</div>
							<div className="overview-box-count ">{`${this.state.totalProfit} / ${this.state.totalProfitDay}`}</div>
						</div>

					</div> */}
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
					{/* <div className='p-col-12 p-md-6 p-lg-3 d-flex' >
						<div className='box-cus box-2' style={{ width: '100%' }}>
							<div className='box-cus-title'>
								<i className="pi pi-shopping-cart"></i>
								<span className='box-cus-title' >Total LONG / SHORT</span>

							</div>
							<div className="overview-box-count ">{this.state.totalLongShort}</div>
						</div>

					</div> */}

					<div className='p-col-12 p-lg-3' >
						<div className='box-cus box-2'>
							<div className='box-cus-title'>
								<i className="pi pi-shopping-cart"></i>
								{/* <span className='box-cus-title'>Total LONG / SHORT</span> */}
								<span className='box-cus-title'>Total Profit / %</span>

							</div>
							<div className="overview-box-count">{`${formatNumber(this.state.totalProfit2)} / ${this.state.Per}`}</div>
						</div>

					</div>

					{/* <div className='p-col-12 p-md-6 p-lg-3 d-flex' >
						<div className='box-cus box-3' style={{ width: '100%' }}>
							<div className='box-cus-title'>
								<i className="pi pi-chart-bar"></i>
								<span className='box-cus-title'>Total Take Profit / Stoploss</span>

							</div>
							<div className="overview-box-count ">{this.state.totalTakeprofitstoploss}</div>
						</div>
					</div> */}

					<div className='p-col-12 p-lg-3' >
						<div className='box-cus box-3'>
							<div className='box-cus-title'>
								<i className="pi pi-chart-bar"></i>
								{/* <span className='box-cus-title'>Total Take Profit / Stoploss</span> */}
								{/* <span className='box-cus-title'>Total Position</span> */}
								<span className='box-cus-title' >Total LONG / SHORT</span>

							</div>
							{/* <div className="overview-box-count">{this.state.totalTakeprofitstoploss}</div> */}
							{/* <div className="overview-box-count">{this.state.totalPosition}</div> */}
							<div className="overview-box-count ">{this.state.totalLongShort}</div>
						</div>
					</div>

					<div className='p-col-12 p-md-6 p-lg-3 d-flex' >
						<div className='box-cus box-4' style={{ width: '100%' }}>
							<div className='box-cus-title'>
								<i className="pi pi-star-o"></i>
								{/* <span className='box-cus-title'>Total Coin / Trading</span> */}
								{/* <span className='box-cus-title' >Total LONG / SHORT</span> */}
								<span className='box-cus-title'>Winrate</span>

							</div>
							{/* <div className="overview-box-count">{this.state.totalStrategy}</div> */}
							{/* <div className="overview-box-count">{`${this.state.totalCoin} / ${this.state.trading}`}</div> */}
							{/* <div className="overview-box-count ">{this.state.totalLongShort}</div> */}
							<div className="overview-box-count ">{this.state.winrate}</div>


						</div>

					</div>

					{/* <div className='p-col-12 p-md-6 p-lg-3 d-flex' >
						<div className='box-cus box-2' style={{ width: '100%' }}>
							<div className='box-cus-title'>
								<i className="pi pi-shopping-cart"></i>
								<span className='box-cus-title' >Total LONG / SHORT</span>

							</div>
							<div className="overview-box-count ">{this.state.totalLongShort}</div>
						</div>

					</div> */}

				

					<ChartBalance ref={c => this.ChartBalance = c}></ChartBalance>
					<ChartProfitPerDay ref={c => this.chartProfitPerDay = c} />

					<ChartPNLProfit ref={c => this.ChartPNLProfit = c}></ChartPNLProfit>
					<ChartPNLAccumulated totalInvestment={this.state.totalInvestment} ref={c => this.ChartPNLAccumulated = c} ></ChartPNLAccumulated>

					<ChartLSProfitPerDay ref={c => this.ChartLSProfitPerDay = c} ></ChartLSProfitPerDay>
					<ChartCryptoPerDay ref={c => this.ChartCryptoPerDay = c} />
					<ChartStopLoss ref={c => this.ChartStopLoss = c}></ChartStopLoss>

					<ChartStopLossPer ref={c => this.ChartStopLossPer = c} ></ChartStopLossPer>

					<ChartAvgCoinStrategy ref={c => this.ChartAvgCoinStrategy = c}></ChartAvgCoinStrategy>

				

					{/* <ChartPNLDaily ref={c => this.ChartPNLDaily = c} ></ChartPNLDaily> */}
					

					<ChartFlow ref={c => this.ChartFlow = c}></ChartFlow>

					<ChartFlowSafe ref={c => this.ChartFlowSafe = c} ></ChartFlowSafe>

					<ChartFlowRisky1 ref={c => this.ChartFlowRisky1 = c} ></ChartFlowRisky1>
					<ChartFlowRisky2 ref={c => this.ChartFlowRisky2 = c}></ChartFlowRisky2>
					<ChartFlowRisky3 ref={c => this.ChartFlowRisky3 = c}> </ChartFlowRisky3>
					<ChartFlowRisky4 ref={c => this.ChartFlowRisky4 = c} ></ChartFlowRisky4>

					<ChartAvgTime ref={c => this.ChartAvgTime = c} ></ChartAvgTime>

					
					<ChartProfitStrategy ref={c => this.chartProfitStrategy = c} />

					<ChartParse ref={c => this.ChartParse = c}></ChartParse>



					<TestnetChartLine></TestnetChartLine>






					{/* <LSPerDay ref={c => this.LSPerDay = c} key={makeId()} />
					<ChartTopCoin />
					<ChartLSProfitPerDay key={makeId()} />
					<ChartCrypto key={makeId()} />
					<ChartLongShort key={makeId()} /> */}

				</div>

			</div>


		)
	}


	calBox() {

		var labModel = new Testnet_results();
		// var testnetCampaignModel = new Testnet_campaign();

		labModel.getByAccountTestnet(App.accountSelectorTestnet.selected()).then(res => {
			// labModel.getByStrategy(App.strategySelector.selected()).then(res => {

			var totalProfit = 0;
			var totalPNL = 0;
			var totalDayProfit = 0;
			var totalLong = 0;
			var totalShort = 0;
			var totalTakeProfit = 0;
			var totalStopLoss = 0;

			var totaltrading = 0;

			var totalPosition = res.data.length;

			var start = moment().startOf("day").format('x');

			Object.values(res.data).map(data => {

				if (data[TESTNET_RESULT_PENDING] == 0 && data[TESTNET_RESULT_STATUS] != TESTNET_RESULT_STATUS_CANCLE) {
					totalProfit += Number(data[TESTNET_RESULT_REAL_PROFIT]);
					totalPNL += Number(data[TESTNET_RESULT_REAL_PNL])
				}

				if (data[TESTNET_RESULT_TYPE] == [TESTNET_RESULT_TYPE_LONG]) {
					totalLong++;
				}

				if (data[TESTNET_RESULT_TYPE] == [TESTNET_RESULT_TYPE_SHORT]) {
					totalShort++;
				}

				if (data[TESTNET_RESULT_STATUS] == [TESTNET_RESULT_STATUS_TAKEPROFIT]) {
					totalTakeProfit++;
				}

				if (data[TESTNET_RESULT_STATUS] == [TESTNET_RESULT_STATUS_STOPLOSS]) {
					totalStopLoss++;
				}

				if (Number(data[TESTNET_RESULT_SELL_TIME]) >= start && data[TESTNET_RESULT_PENDING] == 0 && data[TESTNET_RESULT_STATUS] != TESTNET_RESULT_STATUS_CANCLE) {
					totalDayProfit += Number(data[TESTNET_RESULT_REAL_PROFIT]);
				}

				if (data[TESTNET_RESULT_PENDING] == 1) {
					totaltrading++;
				}


			})


			this.getDataLabCampaigns(totalPNL);


			this.setState({
				totalProfit: totalProfit.toFixed(3),
				totalPNL: totalPNL.toFixed(3),
				totalProfitDay: totalDayProfit.toFixed(3),
				totalLongShort: `${totalLong} / ${totalShort}`,
				totalTakeprofitstoploss: `${totalTakeProfit} / ${totalStopLoss}`,
				trading: totaltrading,
				totalPosition: totalPosition,
				winrate : ((totalTakeProfit / totalPosition) * 100).toFixed(2) + '%'
			})
		})


	}

	

	async getDataLabCampaigns(totalPNL) {
		var resultModel = new Testnet_campaigns();

		var testAccoutModel = new Testnet_account();
		var accountData = await testAccoutModel.read({ [TESTNET_ACCOUNT_ID]: App.accountSelectorTestnet.selected() });
		var reserve = 100 - Number(accountData['data'][0][TESTNET_ACCOUNT_RESERVE]);
		resultModel.read({ [TESTNET_ACCOUNT]: App.accountSelectorTestnet.selected() }).then(res => {

			if (res['data']) {
				res = res['data'];
				var totalInvestment = 0;
				var totalProfit2 = 0;

				for (let i in res) {
				
						// totalInvestment += res[i][TESTNET_BUDGET];
						totalInvestment += res[i][TESTNET_MONEY];
						totalProfit2 += res[i][TESTNET_BUDGET] - res[i][TESTNET_MONEY];
					

				}
	

				totalInvestment = totalInvestment / reserve * 100;
				

				this.setState({
					totalInvestment: Math.round(totalInvestment * 100) / 100 ,
					totalProfit2: Math.round(totalPNL * 100) / 100 ,
					Per: formatNumber(((totalPNL / totalInvestment) * 100).toFixed(2))
				});

			}
		})
	}



	componentDidMount() {

		// this.getTotalStra();

		if (App.accountSelectorTestnet) {
			App.accountSelectorTestnet.register('testnet_dashboard', () => {
				this.calBox();
				this.getDataLabCampaigns();
				this.chartProfitPerDay.getData('day');

				this.ChartAvgCoinStrategy.getData();


				// this.ChartPNLDaily.getData();
				this.ChartFlow.getData();
				this.ChartFlowSafe.getData();
				this.ChartFlowRisky1.getData();
				this.ChartFlowRisky2.getData();
				this.ChartFlowRisky3.getData();
				this.ChartFlowRisky4.getData();
				this.ChartAvgTime.getData();
				this.ChartPNLAccumulated.getData();
				this.ChartPNLProfit.getData();

				this.ChartCryptoPerDay.getData();
				this.ChartLSProfitPerDay.getData();
				this.ChartParse.getData();
				this.chartProfitStrategy.getData();

				this.ChartBalance.getData();

				this.ChartStopLoss.getData();
				this.ChartStopLossPer.getData();


			});


			this.calBox();
			
			this.chartProfitPerDay.getData('day');

			this.ChartAvgCoinStrategy.getData();

			// this.ChartPNLDaily.getData();
			this.ChartFlow.getData();
			this.ChartFlowSafe.getData();
			this.ChartFlowRisky1.getData();
			this.ChartFlowRisky2.getData();
			this.ChartFlowRisky3.getData();
			this.ChartFlowRisky4.getData();
			this.ChartAvgTime.getData();
			this.ChartPNLAccumulated.getData();
			this.ChartPNLProfit.getData();

			this.ChartCryptoPerDay.getData();
			this.ChartLSProfitPerDay.getData();
			this.ChartParse.getData();
			this.chartProfitStrategy.getData();

			this.ChartBalance.getData();

			this.ChartStopLoss.getData();
			this.ChartStopLossPer.getData();
		}



	}

	componentWillUnmount() {
		if (this.updateInterval) clearInterval(this.updateInterval);
		App.accountSelectorTestnet.unregister('testnet_dashboard');

	}


}
export default TestnetView
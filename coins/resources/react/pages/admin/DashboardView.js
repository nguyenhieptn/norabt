import React, { Component } from 'react'

import '../../components/Dashboard/index.scss';
import ChartProfitPerDay from '../../components/Dashboard/Real/ChartProfitPerDay';
import ChartCryptoPerDay from '../../components/Dashboard/Real/ChartCryptoPerDay';
import Actions from '../../model/admin/Actions';
import Trades from '../../model/admin/Trades';
import Accounts from '../../model/admin/Accounts';
import ChartChange24h from '../../components/Dashboard/Real/ChartChange24h';
import ExchangeChartLine from '../../components/admin/ExchangeChartLine';
import Account_summaryView from './Account_summaryView';

class DashboardView extends Component {

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

			totalBudget: 0,
			investing: 0,

			totalTrade: 0,
			trading: 0,
			totalInvest: 0,

			

		};
	}


	render() {


		return (

			<div>


				<div className='p-grid dashboard' >

					<div className='p-col-12 p-lg-3 d-flex' >
						<div className='box-cus box-2' style={{ width: '100%' }}>
							<div className='box-cus-title'>
								<i className="pi pi-shopping-cart"></i>
								<span className='box-cus-title'>Total Invest / Budget</span>

							</div>
							<div className="overview-box-count ">{`${this.state.totalInvest} / ${this.state.totalBudget} `}</div>
						</div>

					</div>

					<div className='p-col-12 p-lg-3 d-flex' >
						<div className='box-cus box-1' style={{ width: '100%' }}>
							<div className='box-cus-title'>
								<i className="pi pi-money-bill"></i>
								<span className='box-cus-title'>Total Profit / Today</span>

							</div>
							<div className="overview-box-count">{`${this.state.totalProfit} / ${this.state.totalProfitDay} `}</div>
						</div>

					</div>


					<div className='p-col-12 p-lg-3 d-flex' >
						<div className='box-cus box-3' style={{ width: '100%' }}>
							<div className='box-cus-title'>
								<i className="pi pi-chart-bar"></i>
								<span className='box-cus-title' >Investing</span>

							</div>
							<div className="overview-box-count">{`${this.state.investing}`}</div>
						</div>
					</div>

					<div className='p-col-12 p-lg-3 d-flex' >
						<div className='box-cus box-4' style={{ width: '100%' }}>
							<div className='box-cus-title'>
								<i className="pi pi-chart-bar"></i>
								<span className='box-cus-title' >Total Coin / Trading</span>

							</div>
							<div className="overview-box-count">{`${this.state.totalTrade} / ${this.state.trading}`}</div>

						</div>

					</div>


					<div className="p-col-12 box_shadow box_padding" style={{ marginBottom: 15 }}>
						<Account_summaryView isDashboard={true} onClickAccount={(id) => {
							if (App.accountSelector) App.accountSelector.selectAccount(id);
						}}></Account_summaryView>
					</div>


					{/* <ExchangeChartLine></ExchangeChartLine> */}

					<ChartProfitPerDay setTotalProfit={ (data) => this.getTotalProfitFromChart(data)} ref={c => this.chartProfitPerDay = c} />

					<ChartCryptoPerDay ref={c => this.ChartCryptoPerDay = c} />

					{/* <ChartChange24h></ChartChange24h> */}



					{/* <LSPerDay ref={c => this.LSPerDay = c} key={makeId()} />
					<ChartTopCoin />
					<ChartLSProfitPerDay key={makeId()} />
					<ChartCrypto key={makeId()} />
					<ChartLongShort key={makeId()} /> */}

				</div>

			</div>


		)
	}

	

	getTotalProfitFromChart(data){
		this.setState({
			totalProfit : data
		});
	}


	calBox() {

		var labModel = new Actions();
		labModel.getAll(App.accountSelector.selected()).then(res => {

			var totalProfit = 0;
			var totalDayProfit = 0;
			var totalLong = 0;
			var totalShort = 0;
			var totalTakeProfit = 0;
			var totalStopLoss = 0;
			var trading = 0;
			var investing = 0;

			var start = moment().startOf("day").format('x');

			Object.values(res.data).map(data => {

				var realPNL = Number(data[ACTION_PNL]) - Number(data[ACTION_COMMIT]);

				if (data[ACTION_PENDING] == 0 && data[ACTION_STATUS] != ACTION_STATUS_CANCLE) {
					// totalProfit += Number(data[ACTION_TOTALPROFIT]);
					totalProfit += realPNL;
				}

				if (data[ACTION_PENDING] == 1) {
					trading++;
					investing += Number(data[ACTION_MATCHED_PRICE]) * Number(data[ACTION_MATCHED_QTY]) / Number(data[ACTION_MARGIN]);
				}

				if (data[ACTION_TYPE] == [ACTION_TYPE_LONG]) {
					totalLong++;
				}

				if (data[ACTION_TYPE] == [ACTION_TYPE_SHORT]) {
					totalShort++;
				}

				if (data[ACTION_STATUS] == [ACTION_STATUS_TAKEPROFIT]) {
					totalTakeProfit++;
				}

				if (data[ACTION_STATUS] == [ACTION_STATUS_STOPLOSS]) {
					totalStopLoss++;
				}

				if (Number(data[ACTION_SELL_TIME]) >= start && data[ACTION_PENDING] == 0 && data[ACTION_STATUS] != ACTION_STATUS_CANCLE) {
					// totalDayProfit += Number(data[ACTION_TOTALPROFIT]);
					totalDayProfit += realPNL;
				}



			})


			this.setState({
				totalProfit: totalProfit.toFixed(3),
				totalProfitDay: totalDayProfit.toFixed(3),
				totalLongShort: `${totalLong} / ${totalShort}`,
				totalTakeprofitstoploss: `${totalTakeProfit} / ${totalStopLoss}`,
				trading: trading,
				investing: investing.toFixed(2),
			})
		})


	}


	calTrade() {
		var tradeModel = new Trades();
		tradeModel.read({ [TRADE_ACCOUNT]: App.accountSelector.selected() }).then(res => {
			if (res['result']) {
				var data = res['data'];
				var totalTrade = data.length;

				var totalBudget = 0;

				for (let i in data) {
					totalBudget += Number(data[i][TRADE_MONEY])
				}

				this.setState({
					totalBudget: totalBudget.toFixed(2),
					totalTrade: totalTrade,
				})
			}
		})
	}

	calTotalInvest(){
		var accountModel = new Accounts();
		accountModel.read({ [ACCOUNT_ID]: App.accountSelector.selected() }).then(res => {

			var data = res.data;

			var totalInvest = data[0][ACCOUNT_TOTAL_INVEST];
			this.setState({
				totalInvest
			})
		}
				
		)
	}


	getTotalAccount() {
		var accountModel = new Accounts();
		accountModel.count().then(res => this.setState({ totalAccount: res }))
	}


	componentDidMount() {

		this.getTotalAccount();

	

		if (App.accountSelector) {
			App.accountSelector.register('real_dashboard', () => {
				this.calBox();
				this.calTrade();
				this.calTotalInvest();
				this.chartProfitPerDay.getData();
				this.ChartCryptoPerDay.getData();
			});

			this.calBox();
			this.calTrade();
			this.calTotalInvest();
			this.chartProfitPerDay.getData();
			this.ChartCryptoPerDay.getData();
		}

		this.updateInterval = setInterval(() => {
			this.calBox();
			this.calTrade();
			this.calTotalInvest();
			this.chartProfitPerDay.getData();
			this.ChartCryptoPerDay.getData();
		}, 120000)

		// var b = await this.getWatchList();
		// var c = this.getData();

		// this.updateInterval = setInterval(() => {
		// 	this.getDateTotalProfit(false);
		//  this.getDataTotalTakeprofitStoploss();
		// }, 2000);

	}

	componentWillUnmount() {
		App.accountSelector.unregister('real_dashboard');
		if (this.updateInterval) clearInterval(this.updateInterval);

	}


}
export default DashboardView
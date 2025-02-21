import React, { Component } from 'react'
import Highcharts from 'highcharts/highstock'
import HighchartsReact from 'highcharts-react-official'
import Input from '../../components/input/Input'
import SelectAccount from '../../components/admin/SelectAccount'
import ChartTooltip from '../../components/admin/ChartTooltip'
import SelectSymbol from '../../components/admin/SelectSymbol'

// Load Highcharts modules
require('highcharts/indicators/indicators')(Highcharts)
require('highcharts/indicators/pivot-points')(Highcharts)
require('highcharts/indicators/macd')(Highcharts)
require('highcharts/modules/exporting')(Highcharts)
require('highcharts/modules/map')(Highcharts)
require('../../components/Dashboard/hollowcandlestick')(Highcharts)

class TradechartView extends Component {

	constructor(props) {
		super(props);

		// var groupingUnits = [[
		// 	'week',                         // unit name
		// 	[1]                             // allowed multiples
		// ], [
		// 	'month',
		// 	[1, 2, 3, 4, 6]
		// ]]

		this.khung = ['1m', '3m', '15m', '1h', '4h'];

		var dt = new Date();

		App.chartView = this;

		this.state = {
			// To avoid unnecessary update keep all options in the state.
			khung: get(localStorage.getItem('default_frame'), '15m'),
			histogram: get(localStorage.getItem('default_histogram'), '4'),
			account: App.accountSelector.selected(),

			chartOptions: {


				plotOptions: {
					candlestick: {
						color: '#ffcdd2',
						lineColor: '#ff5252',
						upColor: '#b2dfdb',
						upLineColor: '#26a69a',

					},


					series: {
						turboThreshold: 0 // Comment out this code to display error
					}

				},



				rangeSelector: {
					buttonPosition: {
						align: 'left',
						// x: '0',
						y: '-1',
					},

					allButtonsEnabled: true,
					buttons:
						[
							{
								text: '1H',
								type: 'hour',
								count: 1,

							},
							{
								text: '2H',
								type: 'hour',
								count: 2,
							},
							{
								text: '6H',
								type: 'hour',
								count: 6,

							}, {
								text: '12H',
								type: 'hour',
								count: 12,

							}, {
								text: '24H',
								type: 'hour',
								count: 24,

							}, {
								type: 'all',
								text: 'All'
							},
						],
					inputEnabled: false,
					selected: 2,
					buttonSpacing: 10,
				},




				chart: {
					height: (8 / 16 * 100) + '%', // 16:9 ratio

					panning: {
						enabled: true,
						type: 'x'
					},
					panKey: 'shift',
					zoomType: 'x'



				},

				legend: {
					enabled: true
				},

				// rangeSelector: {
				// 	selected: 2
				// },

				title: {
					text: 'Symbol',
					align: 'right',
					x: -50
				},

				yAxis: [{
					labels: {
						// distance: '75%',
						align: 'auto',
						style: {
							fontSize: "10px"
						}
					},

					title: {
						text: '',
					},

					height: '75%',
					lineWidth: 2,
					resize: {
						enabled: true
					}
				}, {
					top: '75%',
					height: '25%',
					labels: {
						// distance: '75%',
						align: 'auto',
						style: {
							fontSize: "10px"
						}
					},
					offset: 0,
					title: {
						text: 'MACD',
						x: 50
					}
				}
				],

				tooltip: {
					useHTML: true,
					backgroundColor: null,
					borderWidth: 0,
					shadow: false,
					shared: true,
					formatter: function () {
						var points = this.points;
						if(!points) points = [this];

						var price = [];
						var ema = [];
						var macd = [];
						var histogram = [];
						var showTooltip = [];
						var lab1 = [];
						var lab2 = [];
						var lab3 = [];
						var lab4 = [];

						var time = null;
						var x = null;
						var y = null;
						var bottom = null;

						for (let i in points) {
							var point = points[i];
							time = point.x;
							x = point.point.plotX;
							y = point.point.plotY;
							if (point.series.yAxis.bottom && point.series.yAxis.bottom > bottom) bottom = point.series.yAxis.bottom;
							var id = point.series.userOptions.id;
							if (id == 'aapl') {
								price.push({ name: 'Open', value: point.point.open, color: get(point.point.graphic.stroke, 'black') });
								price.push({ name: 'High', value: point.point.high, color: get(point.point.graphic.stroke, 'black') });
								price.push({ name: 'Low', value: point.point.low, color: get(point.point.graphic.stroke, 'black') });
								price.push({ name: 'Close', value: point.point.close, color: get(point.point.graphic.stroke, 'black') });

							} else if (id == 'Histogram') {
								histogram.push({ name: id, value: point.y, color: get(point.color, 'black') });
							} else if (id == 'MACD') {
								macd.push({ name: id, value: point.y, color: get(point.color, 'black') });
							} else if (id == 'EMA5' || id == 'EMA9' || id == 'EMA13') {
								ema.push({ name: id, value: point.y, color: get(point.color, 'black') });
							} else if (id == 'Action') {
								var color = (point.point.options.profit > 0 ? 'green' : 'red')
								lab1.push({ name: 'Order Price', value: point.point.options.price, color: color });
								lab1.push({ name: 'Order Time', value: point.point.options.time, color: color });
								lab1.push({ name: '|| Matched Price', value: point.point.options.matched, color: color });
								lab1.push({ name: 'Matched Time', value: point.point.options.matched_time, color: color });
								lab1.push({ name: '|| Sell Price', value: point.point.options.sell, color: color });
								lab1.push({ name: 'Sell Time', value: point.point.options.sell_time, color: color });
								lab3.push({ name: 'Profit', value: point.point.options.profit + '%', color: color });
								lab4.push({ name: 'Result', value: point.point.options.param, color: color });
							} else {
								showTooltip.push({ name: id, value: point.y, color: get(point.color, 'black') });
							}
						}

						var tooltip = `<div style="background:white; border:solid thin darkgray; padding:5px; top:-20px">
						<div style="margin-left:5px; color:blue"><b>Time: </b>${moment(time, 'x').format('DD/MM HH:mm')}</div>
						${price.length == 0 ? '' : `<div class="box_flex">${price.map(item => { return `<div style="margin-left:5px; color:${item.color}"><b>${item.name + "</b>: <span>" + item.value + '</span>'}</div>` }).join('')}</div>`}
						${ema.length == 0 ? '' : `<div class="box_flex">${ema.map(item => { return `<div style="margin-left:5px; color:${item.color}"><b>${item.name + "</b>: <span>" + item.value + '</span>'}</div>` }).join('')}</div>`}
						${histogram.length == 0 ? '' : `<div class="box_flex">${histogram.map(item => { return `<div style="margin-left:5px; color:${item.color}"><b>${item.name + "</b>: <span>" + item.value + '</span>'}</div>` }).join('')}</div>`}
						${macd.length == 0 ? '' : `<div class="box_flex">${macd.map(item => { return `<div style="margin-left:5px; color:${item.color}"><b>${item.name + "</b>: <span>" + item.value + '</span>'}</div>` }).join('')}</div>`}
						${showTooltip.length == 0 ? '' : `<div class="box_flex">${showTooltip.map(item => { return `<div style="margin-left:5px; color:${item.color}"><b>${item.name + "</b>: <span>" + item.value + '</span>'}</div>` }).join('')}</div>`}
						${lab1.length == 0 ? '' : `<div class="box_flex">${lab1.map(item => { return `<div style="margin-left:5px; color:${item.color}"><b>${item.name + "</b>: <span>" + item.value + '</span>'}</div>` }).join('')}</div>`}
						${lab2.length == 0 ? '' : `<div class="box_flex">${lab2.map(item => { return `<div style="margin-left:5px; color:${item.color}"><b>${item.name + "</b>: <span>" + item.value + '</span>'}</div>` }).join('')}</div>`}
						${lab3.length == 0 ? '' : `<div class="box_flex">${lab3.map(item => { return `<div style="margin-left:5px; color:${item.color}"><b>${item.name + "</b>: <span>" + item.value + '</span>'}</div>` }).join('')}</div>`}
						${lab4.length == 0 ? '' : `<div class="box_flex">${lab4.map(item => { return `<div style="margin-left:5px; color:${item.color}"><b>${item.name + "</b>: <span>" + item.value + '</span>'}</div>` }).join('')}</div>`}
						</div>`
						if(App.chartView && App.chartView.tooltip) App.chartView.tooltip.setTooltip(tooltip);

						return `
						${time == null ? '' : `<div style="background:white; border:solid thin darkgray; padding:2px; border-radius:5px ; position:absolute; top:${bottom}px; left:${x - 35}px">${moment(time, 'x').format('DD/MM HH:mm')}</div>`}
						
						`

					},

					positioner: function () {
						return { x: 0, y: 0 };
					},
					// shadow: false,
					// borderWidth: 1,
					// backgroundColor: 'rgba(255,255,255,1)'
				},

				series: [
					{
						type: 'candlestick',
						name: App.symbol,
						id: 'aapl',
						data: [],


					},


					{
						yAxis: 1,
						type: 'column',
						name: 'Histogram',
						id: 'Histogram',
						linkedTo: 'aapl',
						groupPadding: 0.025,
						pointPadding: 0.025,
						data: [[0, null], [dt.getTime(), null]],



					},

					{
						yAxis: 1,
						name: 'MACD',
						id: 'MACD',
						lineWidth: 1,
						color: 'black',
						visible: false,
						data: [],


					},

					{
						name: 'EMA5',
						id: 'EMA5',
						color: 'black',
						lineWidth: 1,
						data: [],


					},
					{
						name: 'EMA9',
						id: 'EMA9',
						color: 'blue',
						lineWidth: 1,
						// visible: false,
						data: [],


					},
					{
						name: 'EMA13',
						id: 'EMA13',
						color: 'red',
						lineWidth: 1,
						// visible: false,
						data: [],


					},

					{
						type: 'flags',
						id: 'Action',
						// onSeries: 'aapl',  // Id of which series it should be placed on. If not defined 
						shape: 'squarepin',  // Defines the shape of the flags.
						name: 'Action',

					}
				]

			}
		};

		this.updateChartWidth = this.updateChartWidth.bind(this)

		Highcharts.setOptions({
			time: {
				timezoneOffset: moment().utcOffset(),
				useUTC: false
			}
		});



	}



	render() {
		const { chartOptions } = this.state;


		return (<>
		
			<ChartTooltip ref={c => this.tooltip = c}></ChartTooltip>
			<br/>
			<div style={{ position: 'relative', resize: 'both', overflow: 'auto' }} ref={c => this.chartContainer = c} onDoubleClick={() => {
				this.chartContainer.style.width = 'unset'
				this.chartContainer.style.height = 'unset'
			}}>
				<div style={{ display: 'flex', alignItems: 'center', position: 'absolute', top: 0, left: 0, zIndex: 100 }}>
					{this.khung.map(item => {
						return <div key={item} className='button btn' style={{ border: 'solid thin darkgray', borderRadius: 5, padding: '2px 5px', fontWeight: 'bold', background: (this.state.khung == item ? 'orange' : 'none') }} onClick={() => {
							this.setState({ khung: item }, () => this.getData(true));
							localStorage.setItem('default_frame', item);
						}}>{item.toUpperCase()}</div>
					})}

					<Input ref={c => this.histogramInput = c} placeholder="Histogram" className='input' struct={{
						[INPUT_TYPE]: 'select',
						[INPUT_DEFAULT]: this.state.histogram,
						[INPUT_ONCHANGE]: (e, obj) => {
							var id = obj.getValue();
							localStorage.setItem('default_histogram', id);
							this.setState({
								histogram: id,
							}, () => this.getData(true))
						},
						[INPUT_OPTION]: {
							9: 'Histogram 9',
							7: 'Histogram 7',
							4: 'Histogram 4',
							5: 'Histogram 5',
							6: 'Histogram 6',
							2: 'Histogram 2',
							3: 'Histogram 3',
						}
					}}></Input>
					&nbsp;
					<SelectSymbol onSelect={id => {
						App.symbol = id;
						this.getData(true);
					}}></SelectSymbol>
					&nbsp;
					{/* <SelectAccount style={{padding:0}} ref={c => this.selectAccount = c} onSelect={id => {
						this.setState({ account: id }, () => this.getData(true));
					}}></SelectAccount> */}

				</div>
				<HighchartsReact
					highcharts={Highcharts}
					options={chartOptions}
					constructorType={'stockChart'}
					ref={c => this.chart = c}

				/>

				<style>{`
					html, body, #app {
						height:100%;
					}
					.main {
						height: calc(100% - 60px)
					}
				`}</style>
			</div>
			</>
		)
	}


	updateChartWidth() {
		if (this.updateWidthTimeout) clearTimeout(this.updateWidthTimeout);
		this.updateWidthTimeout = setTimeout(() => {
			console.log("Update Chart width");
			this.setState({
				chartOptions: {
					...this.setState.chartOptions,
					chart: {
						width: this.chartContainer.clientWidth
					}

				}
			})
		}, 500);
	}


	componentDidMount() {
		this.getData();
		this.updateInterval = setInterval(() => { this.getData(false, 5, false) }, 2000);

		this.updateChartWidth();

		this.resize_ob = new ResizeObserver((entries) => {
			this.updateChartWidth()
		});
		this.resize_ob.observe(this.chartContainer);

		if(App.accountSelector) App.accountSelector.register('trade_chart', (account)=>{
			this.setState({ account: account[ACCOUNT_ID] }, () => this.getData(true));
		})

	}

	componentWillUnmount() {
		if (this.updateInterval) clearInterval(this.updateInterval);
		if (this.resize_ob) this.resize_ob.unobserve(this.chartContainer);
	}



	getData(loading = true, limit = 1000, reset = true) {
		if (App.symbol == null || App.symbol == '' || this.state.account == '') return;
		if (loading) App.loading(true)
		return axios.request({
			url: `/admin/tradechart/getCandleData`,
			method: 'POST',
			data: {
				symbol: App.symbol,
				interval: this.state.khung,
				account: this.state.account,
				limit: limit
			}
		})

			.then(response => {
				if (loading) App.loading(false);
				response = response['data'];

				if (response['result']) {
					if (!this.chart) return;
					var ohlc = [];
					var allData = response['data'];
					var data = allData['data'];
					var flag = allData['flag'];
					var dataLength = data.length;
					var macdData = [];
					var signalData = [];
					var histogramData = [];
					var ema5Data = [];
					var ema9Data = [];
					var ema13Data = [];
					var flagData = [];

					if (dataLength > 0 && data[dataLength - 1]['histogram'] == null) return;


					if (!reset) {
						var serials = this.chart.chart.series;
						for (let i in serials) {
							var serial = serials[i].userOptions;
							if (serial['id'] == 'aapl') ohlc = serial['data'].slice(0, serial['data'].length - 2);
							else if (serial['id'] == 'Histogram') histogramData = serial['data'].slice(0, serial['data'].length - 2);
							else if (serial['id'] == 'MACD') macdData = serial['data'].slice(0, serial['data'].length - 2);
							else if (serial['id'] == 'EMA5') ema5Data = serial['data'].slice(0, serial['data'].length - 2);
							else if (serial['id'] == 'EMA9') ema9Data = serial['data'].slice(0, serial['data'].length - 2);
							else if (serial['id'] == 'EMA13') ema13Data = serial['data'].slice(0, serial['data'].length - 2);
						}
						// if (histogramData.length <= 2) histogramData = [];
					}






					for (let i in flag) {
						var fillColor = "white";
						if (flag[i][ACTION_STATUS] == ACTION_STATUS_MATCHED) fillColor = 'orange';
						else if (flag[i][ACTION_STATUS] == ACTION_STATUS_TAKEPROFIT) fillColor = 'green';
						else if (flag[i][ACTION_STATUS] == ACTION_STATUS_STOPLOSS) fillColor = 'red';
						else if (flag[i][ACTION_STATUS] == ACTION_STATUS_CANCLE) fillColor = 'yellow';
						flagData.push(
							{
								x: get(flag[i][ACTION_MATCHED_TIME], flag[i][ACTION_TIME]),      // Point where the flag appears
								y: get(flag[i][ACTION_MATCHED_PRICE], flag[i][ACTION_ENTER_PRICE]),
								title: flag[i][ACTION_TYPE] == '1' ? 'Lab Long' : 'Lab Short', // Title of flag displayed on the chart 
								text: flag[i][ACTION_MATCHED_PRICE],  // Text displayed when the flag are highlighted.
								fillColor: fillColor,
								profit: Number(flag[i][ACTION_PROFIT]),
								price: flag[i][ACTION_ENTER_PRICE],
								time: moment(flag[i][ACTION_TIME], 'x').format('HH:mm:ss'),
								matched: flag[i][ACTION_MATCHED_PRICE],
								matched_time: moment(flag[i][ACTION_MATCHED_TIME], 'x').format('HH:mm:ss'),
								sell: flag[i][ACTION_SELL_PRICE],
								sell_time: moment(flag[i][ACTION_SELL_TIME], 'x').format('HH:mm:ss'),
								param: flag[i][ACTION_STOP_REASON]
							}
						)
					}


					



					var lastTime = 0;
					if (ohlc.length > 0) lastTime = ohlc[ohlc.length - 1][0];



					for (var i = 0; i < dataLength; i += 1) {
						if (data[i]['open_time'] <= lastTime) continue;
						var item = data[i];
						ohlc.push([
							Number(data[i]['open_time']), // the date
							Number(data[i]['open']), // open
							Number(data[i]['high']), // high
							Number(data[i]['low']), // low
							Number(data[i]['close']) // close
						]);

						if (data[i]['macd'] != null) {

							macdData.push([
								Number(data[i]['open_time']),
								Number(data[i]['macd']),

							])
						}

						var histoCol = this.state.histogram == 9 ? 'histogram' : `histogram${this.state.histogram}`;

						if (data[i][histoCol] != null) {
							var h0 = Number(data[i][histoCol]);
							var color = h0 > 0 ? '#26a69a' : '#ff5252';

							if (data[i - 1]) {
								var h1 = Number(data[i - 1][histoCol]);
								if (h0 > 0 && h0 < h1) color = '#b2dfdb';
								if (h0 < 0 && h0 > h1) color = '#ffcdd2';
							}

							histogramData.push({
								x: Number(data[i]['open_time']),
								y: Number(data[i][histoCol]),
								color: color
							})
						}

						if (data[i]['ema5'] != null) {
							ema5Data.push([
								Number(data[i]['open_time']),
								Number(data[i]['ema5'])
							])
						}

						if (data[i]['ema9'] != null) {
							ema9Data.push([
								Number(data[i]['open_time']),
								Number(data[i]['ema9'])
							])
						}

						if (data[i]['ema13'] != null) {
							ema13Data.push([
								Number(data[i]['open_time']),
								Number(data[i]['ema13'])
							])
						}

					}


					this.setState({
						chartOptions: {

							title: {
								text: App.symbol,
								align: 'right',
								x: -50
							},

							series: [
								{
									// type: 'candlestick',
									// name: App.symbol,
									data: ohlc,
									id: 'aapl'
								},


								{
									// yAxis: 1,
									// type: 'column',
									// name: 'Histogram',
									// linkedTo: 'aapl',
									data: histogramData,
									id: 'Histogram',

									// groupPadding: 0.025,
									// pointPadding: 0.025,


								},

								{
									// yAxis: 1,
									// name: 'MACD',
									data: macdData,
									id: 'MACD',
									// lineWidth: 1,
									// color: 'black'

								},

								{
									// name: 'EMA5',
									data: ema5Data,
									id: 'EMA5',
									// color: 'black',
									// lineWidth: 1,

								},
								{
									// name: 'EMA9',
									data: ema9Data,
									id: 'EMA9',
									// color: 'blue',
									// lineWidth: 1,

								},
								{
									// name: 'EMA13',
									data: ema13Data,
									id: 'EMA13',
									// color: 'red',
									// lineWidth: 1,

								},

								{
									// type: 'flags',
									data: flagData,
									// onSeries: 'aapl',  // Id of which series it should be placed on. If not defined 
									// shape: 'flag',  // Defines the shape of the flags.
									// name: 'Price',
								}
							]
						}
					})


				} else {
					error_handle(response);
				}

				return response;
			})

			.catch((error) => {
				if (loading) App.loading(false);
				error_handle(error)
				return false;
			})
	}




}

export default TradechartView
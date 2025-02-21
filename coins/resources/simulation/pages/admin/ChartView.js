import React, { Component } from 'react'
import Highcharts from 'highcharts/highstock'
import HighchartsReact from 'highcharts-react-official'
import Input from '../../components/input/Input'
import Lab_campaigns from '../../model/admin/Lab_campaigns'
import ChartTooltip from '../../components/admin/ChartTooltip'
import SelectSymbol from '../../components/admin/SelectSymbol'

// Load Highcharts modules
require('highcharts/indicators/indicators')(Highcharts)
require('highcharts/indicators/pivot-points')(Highcharts)
require('highcharts/indicators/macd')(Highcharts)
require('highcharts/modules/exporting')(Highcharts)
require('highcharts/modules/map')(Highcharts)
require('../../components/Dashboard/hollowcandlestick')(Highcharts)

class ChartView extends Component {

	constructor(props) {
		super(props);

		// var groupingUnits = [[
		// 	'week',                         // unit name
		// 	[1]                             // allowed multiples
		// ], [
		// 	'month',
		// 	[1, 2, 3, 4, 6]
		// ]]

		this.khung = ['1m', '3m', '15m', '1h', '4h', '1d'];

		var dt = new Date();

		App.chartView = this;

		var min = get(App.parsed['min'], null);
		var max = get(App.parsed['max'], null);

		if(max <= min) max = null;

		this.state = {
			// To avoid unnecessary update keep all options in the state.
			khung: get(localStorage.getItem('default_lab_frame'), '15m'),
			histogram: get(localStorage.getItem('default_lab_histogram'), '4'),
			campaign: get(localStorage.getItem('default_lab_campaign'), null),
			rsi_ema: get(localStorage.getItem('default_lab_rsi_ema'), 9),
			start: min,
			stop: max,
			campaigns: {},

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
					text: App.symbol,
					align: 'right',
					// x: -50
				},

				xAxis: {
					crosshair: true,
					
				},

				yAxis: [{
					crosshair: true,
					height: '75%',
					lineWidth: 2,
					resize: {
						enabled: true
					},
					labels: {
						align: 'left'
					}
				}, 
				{
					top: '75%',
					height: '25%',
					labels: {
						align: 'left'
					}
				},

				{
					height: '75%',
					lineWidth: 2,
					resize: {
						enabled: true
					},
					opposite: false,
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

						if (!points) points = [this];

						var price = [];
						var ema = [];
						var macd = [];
						var histogram = [];
						var showTooltip = [];
						var lab1 = [];
						var lab2 = [];
						var lab3 = [];
						var lab4 = [];
						var lab5 = [];

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
							} else if (id == 'Event') {
								var color = (point.point.options.profit > 0 ? 'green' : 'red')
								lab1.push({ name: 'Order Price', value: point.point.options.price, color: color });
								lab1.push({ name: 'Order Time', value: point.point.options.time, color: color });
								lab1.push({ name: '|| Matched Price', value: point.point.options.matched, color: color });
								lab1.push({ name: 'Matched Time', value: point.point.options.matched_time, color: color });
								lab1.push({ name: '|| Sell Price', value: point.point.options.sell, color: color });
								lab1.push({ name: 'Sell Time', value: point.point.options.sell_time, color: color });
								lab4.push({ name: 'Profit', value: point.point.options.profit + '%', color: color });
								lab5.push({ name: 'Result', value: point.point.options.param, color: color });
							} else if (id == 'Order') {
								var color = 'black';
								lab1.push({ name: 'Order Price', value: point.point.options.price, color: color });
								lab1.push({ name: 'Order Time', value: point.point.options.time, color: color });
								lab1.push({ name: 'Order Qty', value: point.point.options.qty, color: color });
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
						${lab5.length == 0 ? '' : `<div class="box_flex">${lab5.map(item => { return `<div style="margin-left:5px; color:${item.color}"><b>${item.name + "</b>: <span>" + item.value + '</span>'}</div>` }).join('')}</div>`}
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
						data: [],

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
						yAxis: 2,
						name: 'RSI',
						id: 'RSI',
						lineWidth: 1,
						color: 'orange',
						visible: false,
						data: [],
					},
					{
						yAxis: 2,
						name: 'RSI EMA',
						id: 'RSI_EMA',
						lineWidth: 1,
						color: 'green',
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
						id: 'Event',
						// onSeries: 'aapl',  // Id of which series it should be placed on. If not defined 
						shape: 'squarepin',  // Defines the shape of the flags.
						name: 'Lab Event',

					},

					{
						type: 'flags',
						id: 'Order',
						shape: "circlepin",
						name: 'Lab Order',
						color: 'black'

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


	setRangeSelector() {

		var max = this.state.stop;
		var min = this.state.start;
		
		if (max > 0 && min > 0) {
			this.chart.chart.xAxis[0].setExtremes(min * 1000, max * 1000);
		} else {
			console.log('Set rangselector to 4')
			this.setState({
				chartOptions: { rangeSelector: { selected: 4 } },
			})

		}
	}



	render() {
		const { chartOptions } = this.state;

		var campaigns = this.state.campaigns;
		var campaignOption = {};
		for (let i in campaigns) {
			campaignOption[i] = campaigns[i][LAB_CAMPAIGN_NAME];
		}

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
							localStorage.setItem('default_lab_frame', item);
							this.setState({ khung: item }, () => this.getData(true));
						}}>{item.toUpperCase()}</div>
					})}
					&nbsp;
					<Input ref={c => this.startInput = c} placeholder="Start Time" className='input' struct={{
						[INPUT_TYPE]: 'date',
						[INPUT_ONCHANGE_BLUR]: (e, obj) => { this.setState({ start: obj.getValue() }, () => this.getData(true)) }
					}}></Input>

					&nbsp;

					<Input ref={c => this.stopInput = c} placeholder="Stop Time" className='input' struct={{
						[INPUT_TYPE]: 'date',
						[INPUT_ONCHANGE_BLUR]: (e, obj) => { this.setState({ stop: obj.getValue() }, () => this.getData(true)) }
					}}></Input>

					&nbsp;

					<Input ref={c => this.campaignInput = c} placeholder="Stop Time" className='input' struct={{
						[INPUT_TYPE]: 'select',
						[INPUT_ONCHANGE]: (e, obj) => {
							var id = obj.getValue();
							this.selectCampaign(id);

						},
						[INPUT_OPTION]: campaignOption
					}}></Input>

					&nbsp;

					<Input ref={c => this.histogramInput = c} placeholder="Histogram" className='input' struct={{
						[INPUT_TYPE]: 'select',
						[INPUT_DEFAULT]: this.state.histogram,
						[INPUT_ONCHANGE]: (e, obj) => {
							var id = obj.getValue();
							localStorage.setItem('default_lab_histogram', id);
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

					<Input ref={c => this.rsiEmaInput = c} placeholder="RSI EMA" className='input' struct={{
						[INPUT_TYPE]: 'select',
						[INPUT_DEFAULT]: this.state.rsi_ema,
						[INPUT_ONCHANGE]: (e, obj) => {
							var id = obj.getValue();
							localStorage.setItem('default_lab_rsi_ema', id);
							this.setState({
								rsi_ema: id,
							}, () => this.getData(true))
						},
						[INPUT_OPTION]: {
							9: 'RSI EMA 9',
							5: 'RSI EMA 5',
							4: 'RSI EMA 4',
						}
					}}></Input>

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


	selectCampaign(id) {
		if (!id) return;
		var campaigns = this.state.campaigns;
		if(!isset(campaigns[id])) return;
		var timeUnit = {
			'1m': 60 ,
			'3m': 3 * 60 ,
			'15m': 15 * 60 ,
			'1h': 60 * 60 ,
			'4h': 4*60 * 60 ,
			'1d': 24*60 * 60 ,
		}
		var startTime = Number(get(this.state.start, campaigns[id][LAB_CAMPAIGN_START])) - timeUnit['1h'] * 3
		var stopTime = Number(get(this.state.stop, campaigns[id][LAB_CAMPAIGN_STOP])) + timeUnit['1h'] * 3
		this.startInput.setValue(startTime);
		this.stopInput.setValue(stopTime);
		if (App.selectSymbol) App.selectSymbol.setState({ symbolSelected: campaigns[id][LAB_CAMPAIGN_SYMBOL] })
		App.symbol = campaigns[id][LAB_CAMPAIGN_SYMBOL]
		this.campaignInput.setValue(id);
		localStorage.setItem('default_lab_campaign', id);
		this.setState({
			campaign: id,
			start: startTime,
			stop: stopTime,
		}, () => this.getData(true))
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

		this.getData().then(res=>{
			this.setRangeSelector();
		})
		// this.updateInterval = setInterval(() => { this.getData(false, 5, false) }, 2000);

		this.updateChartWidth();

		this.resize_ob = new ResizeObserver((entries) => {
			this.updateChartWidth()
		});
		this.resize_ob.observe(this.chartContainer);

		var campaignModel = new Lab_campaigns();
		campaignModel.read(null).then(res => {
			if (res && res['result']) {
				var selected = null;
				var campaignIndex = {};
				if (res['data'].length > 0) {

					selected = localStorage.getItem('default_lab_campaign');
					if(selected == null) selected = res['data'][0][LAB_CAMPAIGN_ID];

					for (let i in res['data']) {
						campaignIndex[res['data'][i][LAB_CAMPAIGN_ID]] = res['data'][i];
						if (res['data'][i][LAB_CAMPAIGN_ID] == App.parsed['campaign']) {
							selected = res['data'][i][LAB_CAMPAIGN_ID]
						}
					}
				}

				this.setState({ campaigns: campaignIndex }, () => { this.selectCampaign(selected) });
			}
		})

	}

	componentWillUnmount() {
		// if (this.updateInterval) clearInterval(this.updateInterval);
		if (this.resize_ob) this.resize_ob.unobserve(this.chartContainer);
	}

	getData(loading = true) {
		if (App.symbol == null || App.symbol == '' || this.state.campaign == null) return Promise.reject(false);
		if (loading) App.loading(true)
		return axios.request({
			url: `/admin/simulation/getLabCandleData`,
			method: 'POST',
			data: {
				symbol: App.symbol,
				interval: this.state.khung,
				start: this.state.start,
				stop: this.state.stop,
				campaign: this.state.campaign,
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
					var orderFlag = allData['order_flag'];
					var eventFlag = allData['event_flag'];
					var dataLength = data.length;
					var macdData = [];
					var signalData = [];
					var histogramData = [];
					var ema5Data = [];
					var ema9Data = [];
					var ema13Data = [];
					var orderFlagData = [];
					var eventFlagData = [];
					var rsi = [];
					var rsi_ema = [];

					// if (dataLength > 0 && data[dataLength - 1]['histogram'] == null) return;


					for (let i in eventFlag) {
						var fillColor = "white";
						if (eventFlag[i][LAB_RESULT_STATUS] == LAB_RESULT_STATUS_MATCHED) fillColor = 'orange';
						else if (eventFlag[i][LAB_RESULT_STATUS] == LAB_RESULT_STATUS_TAKEPROFIT) fillColor = 'green';
						else if (eventFlag[i][LAB_RESULT_STATUS] == LAB_RESULT_STATUS_STOPLOSS) fillColor = 'red';
						else if (eventFlag[i][LAB_RESULT_STATUS] == LAB_RESULT_STATUS_CANCLE) fillColor = 'gray';
						eventFlagData.push(
							{
								x: Math.floor(eventFlag[i][LAB_RESULT_CHART]/60000) * 60000,      // Point where the eventFlag appears
								y: get(eventFlag[i][LAB_RESULT_MATCHED_PRICE], eventFlag[i][LAB_RESULT_ENTER_PRICE]),
								title: eventFlag[i][LAB_RESULT_TYPE] == '1' ? 'Long' : 'Short', // Title of eventFlag displayed on the chart 
								text: eventFlag[i][LAB_RESULT_ORDER_PRICE],  // Text displayed when the eventFlag are highlighted.
								fillColor: fillColor,
								profit: Number(eventFlag[i][LAB_RESULT_PROFIT]),
								price: eventFlag[i][LAB_RESULT_ORDER_PRICE],
								time: moment(eventFlag[i][LAB_RESULT_ORDER_TIME], 'x').format('HH:mm:ss'),
								matched: eventFlag[i][LAB_RESULT_MATCHED_PRICE],
								matched_time: moment(eventFlag[i][LAB_RESULT_MATCHED_TIME], 'x').format('HH:mm:ss'),
								sell: eventFlag[i][LAB_RESULT_SELL_PRICE],
								sell_time: moment(eventFlag[i][LAB_RESULT_SELL_TIME], 'x').format('HH:mm:ss'),
								param: eventFlag[i][LAB_RESULT_PARAMS]
							}
						)
					}


					for (let i in orderFlag) {
						var fillColor = "white";
						orderFlagData.push(
							{
								x: Math.floor(orderFlag[i][LAB_ORDER_TIME]/60000) * 60000,      // Point where the orderFlag appears
								y: orderFlag[i][LAB_ORDER_PRICE],
								title: (orderFlag[i][LAB_ORDER_TYPE] == '1' ? 'Buy' : 'Sell') + " " + orderFlag[i][LAB_ORDER_PHASE], // Title of orderFlag displayed on the chart 
								text: orderFlag[i][LAB_ORDER_PRICE],  // Text displayed when the orderFlag are highlighted.
								fillColor: fillColor,
								price: orderFlag[i][LAB_ORDER_PRICE],
								time: moment(orderFlag[i][LAB_ORDER_TIME], 'x').format('HH:mm:ss'),
								qty: orderFlag[i][LAB_ORDER_QTY],

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
						var rsiEmaCol = 'rsi_ema' + this.state.rsi_ema; 



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

						if (data[i]['rsi'] != null) {
							rsi.push([
								Number(data[i]['open_time']),
								Number(data[i]['rsi'])
							])
						}

						if (data[i][rsiEmaCol] != null) {
							rsi_ema.push([
								Number(data[i]['open_time']),
								Number(data[i][rsiEmaCol])
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
									name: App.symbol,
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
									// yAxis: 1,
									// name: 'MACD',
									data: rsi,
									id: 'RSI',
									// lineWidth: 1,
									// color: 'black'

								},
								{
									// yAxis: 1,
									// name: 'MACD',
									data: rsi_ema,
									id: 'RSI_EMA',
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
									
									data: eventFlagData,
									
								},
								{
									
									data: orderFlagData,
									
								}
							]
						}
					}, ()=>{this.setRangeSelector()})


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

export default ChartView
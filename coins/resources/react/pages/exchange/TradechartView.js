import React, { Component } from 'react'
import Highcharts from 'highcharts/highstock'
import HighchartsReact from 'highcharts-react-official'
import Input from '../../components/input/Input'
import SelectSymbol from '../../components/admin/SelectSymbol'
import ChartTooltip from '../../components/admin/ChartTooltip'
import Watchlist from '../../model/admin/Watchlist'

// Load Highcharts modules
require('highcharts/indicators/indicators')(Highcharts)
require('highcharts/indicators/pivot-points')(Highcharts)
require('highcharts/indicators/ema')(Highcharts)
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

		this.khung = ['1m', '3m', '15m', '1h', '4h'];
		var dt = new Date();

		App.chartView = this;

		var symbol = get(localStorage.getItem('testnet_default_symbol'), 'BTCUSDT');
		var symbol1 = get(localStorage.getItem('testnet_default_symbol1'), 'BTCUSDT');
		var symbol2 = get(localStorage.getItem('testnet_default_symbol2'), 'BTCUSDT');

		if (App.parsed.symbol) {
			symbol = App.parsed.symbol;
			symbol1 = App.parsed.symbol;
			symbol2 = App.parsed.symbol;
		}

		this.state = {
			// To avoid unnecessary update keep all options in the state.
			khung: get(localStorage.getItem('testnet_default_frame'), '15m'),
			khung1: get(localStorage.getItem('testnet_default_frame1'), '1h'),
			khung2: get(localStorage.getItem('testnet_default_frame2'), '4h'),
			histogram: get(localStorage.getItem('testnet_default_histogram'), '4'),
			histogram1: get(localStorage.getItem('testnet_default_histogram1'), '4'),
			histogram2: get(localStorage.getItem('testnet_default_histogram2'), '4'),
			rsi_ema: get(localStorage.getItem('testnet_default_rsi_ema'), '9'),
			rsi_ema1: get(localStorage.getItem('testnet_default_rsi_ema1'), '9'),
			rsi_ema2: get(localStorage.getItem('testnet_default_rsi_ema2'), '9'),
			symbol: symbol,
			symbol1: symbol1,
			symbol2: symbol2,
			tooltip: true,
			symbolOptions: {},

			chartOptions: {


				plotOptions: {
					candlestick: {
						color: '#ffcdd2',
						lineColor: '#ff5252',
						upColor: '#b2dfdb',
						upLineColor: '#26a69a',

					},


					series: {
						turboThreshold: 0, // Comment out this code to display error
						states: {
							inactive: {
								opacity: 1
							}
						},

						
						dataLabels: {
							enabled: false
						},
						lineWidth: 1,
						marker: {
							enabled: false
						}
						
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
					text: ''
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

				xAxis: {
					crosshair: true,
					events: {
						setExtremes: this.syncExtremes
					}
				},

				tooltip: {
					useHTML: true,
					backgroundColor: null,
					borderWidth: 0,
					shadow: false,
					shared: true,
					formatter: function () {
						var points = this.points;

						var tooltipComp = App.chartView.tooltip

						if (!points) {
							points = [this];
							tooltipComp = App.chartView.tooltipEvent
						}

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
						var symbol = '';



						for (let i in points) {
							var point = points[i];
							time = point.x;
							x = point.point.plotX;
							y = point.point.plotY;
							if (point.series.yAxis.bottom && point.series.yAxis.bottom > bottom) bottom = point.series.yAxis.bottom;
							var id = point.series.userOptions.id;
							if (id == 'aapl') {
								symbol = point.series.name;
								price.push({ name: 'Open', value: point.point.open, color: get(point.point.graphic.stroke, 'black') });
								price.push({ name: 'High', value: point.point.high, color: get(point.point.graphic.stroke, 'black') });
								price.push({ name: 'Low', value: point.point.low, color: get(point.point.graphic.stroke, 'black') });
								price.push({ name: 'Close', value: point.point.close, color: get(point.point.graphic.stroke, 'black') });

							} else if (id == 'Histogram') {
								histogram.push({ name: id, value: point.y, color: get(point.color, 'black') });
							} else if (id == 'MACD') {
								macd.push({ name: id, value: point.y, color: get(point.color, 'black') });
							} else if (id == 'EMA5' || id == 'EMA9' || id == 'EMA13') {
								ema.push({ name: id, value: Math.round(point.y * 10000) / 10000, color: get(point.color, 'black') });
							} else if (id == 'flag_event') {
								symbol = 'Event'
								var color = (point.point.options.profit > 0 ? 'green' : 'red')
								lab1.push({ name: 'Order Price', value: point.point.options.price, color: color });
								lab1.push({ name: 'Order Time', value: point.point.options.time, color: color });
								lab1.push({ name: '|| Matched Price', value: point.point.options.matched, color: color });
								lab1.push({ name: 'Matched Time', value: point.point.options.matched_time, color: color });
								lab1.push({ name: '|| Sell Price', value: point.point.options.sell, color: color });
								lab1.push({ name: 'Sell Time', value: point.point.options.sell_time, color: color });
								lab4.push({ name: 'Profit', value: point.point.options.profit + '%', color: color });
								lab5.push({ name: 'Result', value: point.point.options.param, color: color });
							} else {
								showTooltip.push({ name: id, value: point.y, color: get(point.color, 'black') });
							}
						}

						var tooltip = `<div style="background:white; border:solid thin darkgray; padding:5px; top:-20px">
						<div style="margin-left:5px; color:blue"><b>${symbol} Time: </b>${moment(time, 'x').format('DD/MM HH:mm:ss')}</div>
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

						tooltipComp.setTooltip(tooltip);

						return `
						${time == null ? '' : `<div style="background:white; border:solid thin darkgray; padding:2px; border-radius:5px ; position:absolute; top:${0}px; left:${x - 35}px">${moment(time, 'x').format('DD/MM HH:mm')}</div>`}
						
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
						name: 'Candle',
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
						id: 'flag_event',
						shape: 'squarepin',
						name: 'Event',

					},

					{
						type: 'flags',
						id: 'Order',
						shape: "circlepin",
						name: 'Lab Order',
						color: 'black'

					},

					{
						yAxis: 2,
						name: 'Alts Up',
						id: 'Alts Up',
						visible: true,
						color:'black',
						data: [],
						
					}


				]

			},

			chartOptions1: {


				plotOptions: {
					candlestick: {
						color: '#ffcdd2',
						lineColor: '#ff5252',
						upColor: '#b2dfdb',
						upLineColor: '#26a69a',

					},


					series: {
						turboThreshold: 0, // Comment out this code to display error
						states: {
							inactive: {
								opacity: 1
							}
						}
					}

				},

				rangeSelector: {
					enabled: false
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

				xAxis: {
					crosshair: true,
					events: {
						setExtremes: this.syncExtremes
					}
				},

				tooltip: {
					useHTML: true,
					backgroundColor: null,
					borderWidth: 0,
					shadow: false,
					shared: true,
					formatter: function () {
						var points = this.points;

						var tooltipComp = App.chartView.tooltip1

						if (!points) {
							points = [this];
							tooltipComp = App.chartView.tooltipEvent
						}

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
						var symbol = '';



						for (let i in points) {
							var point = points[i];
							time = point.x;
							x = point.point.plotX;
							y = point.point.plotY;
							if (point.series.yAxis.bottom && point.series.yAxis.bottom > bottom) bottom = point.series.yAxis.bottom;
							var id = point.series.userOptions.id;
							if (id == 'aapl') {
								symbol = point.series.name;
								price.push({ name: 'Open', value: point.point.open, color: get(point.point.graphic.stroke, 'black') });
								price.push({ name: 'High', value: point.point.high, color: get(point.point.graphic.stroke, 'black') });
								price.push({ name: 'Low', value: point.point.low, color: get(point.point.graphic.stroke, 'black') });
								price.push({ name: 'Close', value: point.point.close, color: get(point.point.graphic.stroke, 'black') });

							} else if (id == 'Histogram') {
								histogram.push({ name: id, value: point.y, color: get(point.color, 'black') });
							} else if (id == 'MACD') {
								macd.push({ name: id, value: point.y, color: get(point.color, 'black') });
							} else if (id == 'EMA5' || id == 'EMA9' || id == 'EMA13') {
								ema.push({ name: id, value: Math.round(point.y * 10000) / 10000, color: get(point.color, 'black') });
							} else if (id == 'flag_event') {
								symbol = 'Event'
								var color = (point.point.options.profit > 0 ? 'green' : 'red')
								lab1.push({ name: 'Order Price', value: point.point.options.price, color: color });
								lab1.push({ name: 'Order Time', value: point.point.options.time, color: color });
								lab1.push({ name: '|| Matched Price', value: point.point.options.matched, color: color });
								lab1.push({ name: 'Matched Time', value: point.point.options.matched_time, color: color });
								lab1.push({ name: '|| Sell Price', value: point.point.options.sell, color: color });
								lab1.push({ name: 'Sell Time', value: point.point.options.sell_time, color: color });
								lab4.push({ name: 'Profit', value: point.point.options.profit + '%', color: color });
								lab5.push({ name: 'Result', value: point.point.options.param, color: color });
							} else {
								showTooltip.push({ name: id, value: point.y, color: get(point.color, 'black') });
							}
						}

						var tooltip = `<div style="background:white; border:solid thin darkgray; padding:5px; top:-20px">
						<div style="margin-left:5px; color:blue"><b>${symbol} Time: </b>${moment(time, 'x').format('DD/MM HH:mm:ss')}</div>
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


						tooltipComp.setTooltip(tooltip);

						return `
						${time == null ? '' : `<div style="background:white; border:solid thin darkgray; padding:2px; border-radius:5px ; position:absolute; top:${0}px; left:${x - 35}px">${moment(time, 'x').format('DD/MM HH:mm')}</div>`}
						
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
						name: 'Candle',
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
						id: 'flag_event',
						shape: 'squarepin',
						name: 'Event',

					},

					{
						type: 'flags',
						id: 'Order',
						shape: "circlepin",
						name: 'Lab Order',
						color: 'black'

					},

				]

			},

			chartOptions2: {


				plotOptions: {
					candlestick: {
						color: '#ffcdd2',
						lineColor: '#ff5252',
						upColor: '#b2dfdb',
						upLineColor: '#26a69a',

					},


					series: {
						turboThreshold: 0, // Comment out this code to display error
						states: {
							inactive: {
								opacity: 1
							}
						}
					}

				},



				rangeSelector: {
					enabled: false
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

				xAxis: {
					crosshair: true,
					events: {
						setExtremes: this.syncExtremes
					}
				},

				tooltip: {
					useHTML: true,
					backgroundColor: null,
					borderWidth: 0,
					shadow: false,
					shared: true,
					formatter: function () {
						var points = this.points;
						var tooltipComp = App.chartView.tooltip2

						if (!points) {
							points = [this];
							tooltipComp = App.chartView.tooltipEvent
						}

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
						var symbol = '';



						for (let i in points) {
							var point = points[i];
							time = point.x;
							x = point.point.plotX;
							y = point.point.plotY;
							if (point.series.yAxis.bottom && point.series.yAxis.bottom > bottom) bottom = point.series.yAxis.bottom;
							var id = point.series.userOptions.id;
							if (id == 'aapl') {
								symbol = point.series.name;
								price.push({ name: 'Open', value: point.point.open, color: get(point.point.graphic.stroke, 'black') });
								price.push({ name: 'High', value: point.point.high, color: get(point.point.graphic.stroke, 'black') });
								price.push({ name: 'Low', value: point.point.low, color: get(point.point.graphic.stroke, 'black') });
								price.push({ name: 'Close', value: point.point.close, color: get(point.point.graphic.stroke, 'black') });

							} else if (id == 'Histogram') {
								histogram.push({ name: id, value: point.y, color: get(point.color, 'black') });
							} else if (id == 'MACD') {
								macd.push({ name: id, value: point.y, color: get(point.color, 'black') });
							} else if (id == 'EMA5' || id == 'EMA9' || id == 'EMA13') {
								ema.push({ name: id, value: Math.round(point.y * 10000) / 10000, color: get(point.color, 'black') });
							} else if (id == 'flag_event') {
								symbol = 'Event'
								var color = (point.point.options.profit > 0 ? 'green' : 'red')
								lab1.push({ name: 'Order Price', value: point.point.options.price, color: color });
								lab1.push({ name: 'Order Time', value: point.point.options.time, color: color });
								lab1.push({ name: '|| Matched Price', value: point.point.options.matched, color: color });
								lab1.push({ name: 'Matched Time', value: point.point.options.matched_time, color: color });
								lab1.push({ name: '|| Sell Price', value: point.point.options.sell, color: color });
								lab1.push({ name: 'Sell Time', value: point.point.options.sell_time, color: color });
								lab4.push({ name: 'Profit', value: point.point.options.profit + '%', color: color });
								lab5.push({ name: 'Result', value: point.point.options.param, color: color });
							} else {
								showTooltip.push({ name: id, value: point.y, color: get(point.color, 'black') });
							}
						}

						var tooltip = `<div style="background:white; border:solid thin darkgray; padding:5px; top:-20px">
						<div style="margin-left:5px; color:blue"><b>${symbol} Time: </b>${moment(time, 'x').format('DD/MM HH:mm:ss')}</div>
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


						tooltipComp.setTooltip(tooltip);

						return `
						${time == null ? '' : `<div style="background:white; border:solid thin darkgray; padding:2px; border-radius:5px ; position:absolute; top:${0}px; left:${x - 35}px">${moment(time, 'x').format('DD/MM HH:mm')}</div>`}
						
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
						name: 'Candle',
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
						id: 'flag_event',
						shape: 'squarepin',
						name: 'Event',

					},

					{
						type: 'flags',
						id: 'Order',
						shape: "circlepin",
						name: 'Order',
						color: 'black'

					},


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
		const { chartOptions, chartOptions1, chartOptions2 } = this.state;


		return (
			<>
				<div style={{ position: 'fixed', zIndex: 2000, width: 'calc(100% - 15px)' }}>

					<div style={{ overflow: 'hidden', height: (this.state.tooltip ? 'auto' : 0) }}>
						<div style={{ display: 'flex', width: '100%' }}>
							<ChartTooltip ref={c => this.tooltip = c}></ChartTooltip>
							<ChartTooltip ref={c => this.tooltip1 = c}></ChartTooltip>
							<ChartTooltip ref={c => this.tooltip2 = c}></ChartTooltip>
						</div>
						<ChartTooltip ref={c => this.tooltipEvent = c}></ChartTooltip>
					</div>

					<div style={{
						position: 'absolute',
						top: '100%',
						right: 250,
						border: 'solid thin darkgray',
						borderBottomLeftRadius: 3,
						borderBottomRightRadius: 3,
						borderTop: 'none',
						padding: '2px 10px',
						cursor: 'pointer',
						background: 'white'
					}}
						onClick={() => this.setState({ tooltip: !this.state.tooltip })}
					>
						<i className={this.state.tooltip ? 'fa fa-chevron-up' : 'fa fa-chevron-down'} aria-hidden="true"></i>
					</div>
				</div>
				<div style={{ width: '120%', height: (this.state.tooltip ? 85 * 2 : 0), border: 'solid thin darkgray' }}></div>

				<br />

				<div style={{ position: 'relative', resize: 'both', overflow: 'auto' }} ref={c => this.chartContainer = c} onDoubleClick={() => {
					this.chartContainer.style.width = 'unset'
					this.chartContainer.style.height = 'unset'
				}}>




					<div id="chartContainer">
						<div style={{ display: 'flex', alignItems: 'center', marginBottom: 15 }}>
							{this.khung.map(item => {
								return <div key={item} className='button btn' style={{ border: 'solid thin darkgray', borderRadius: 5, padding: '2px 5px', fontWeight: 'bold', background: (this.state.khung == item ? 'orange' : 'none') }} onClick={() => {
									this.setState({ khung: item }, () => this.getAllData(0));
									localStorage.setItem('testnet_default_frame', item);
								}}>{item}</div>
							})}
							<Input ref={c => this.histogramInput = c} placeholder="Histogram" className='input' struct={{
								[INPUT_TYPE]: 'select',
								[INPUT_DEFAULT]: this.state.histogram,
								[INPUT_ONCHANGE]: (e, obj) => {
									var id = obj.getValue();
									localStorage.setItem('testnet_default_histogram', id);
									this.setState({
										histogram: id,
									}, () => this.getAllData(0))
								},
								[INPUT_OPTION]: {
									9: 'Histogram 9',
									7: 'Histogram 7',
									4: 'Histogram 4',
									2: 'Histogram 2',
									3: 'Histogram 3',
									5: 'Histogram 5',
									6: 'Histogram 6',
								}
							}}></Input>
							&nbsp;
							<Input ref={c => this.rsiEmaInput = c} placeholder="RSI EMA" className='input' struct={{
							[INPUT_TYPE]: 'select',
							[INPUT_DEFAULT]: this.state.rsi_ema,
							[INPUT_ONCHANGE]: (e, obj) => {
								var id = obj.getValue();
								localStorage.setItem('testnet_default_rsi_ema', id);
								this.setState({
									rsi_ema: id,
								}, () => this.getAllData(0))
							},
							[INPUT_OPTION]: {
								9: 'RSI EMA 9',
								5: 'RSI EMA 5',
								4: 'RSI EMA 4',
							}
						}}></Input>
						&nbsp;
							<Input ref={c => this.symbolInput = c} placeholder="Symbol" className='input' struct={{
								[INPUT_TYPE]: 'select',
								[INPUT_DEFAULT]: this.state.symbol,
								[INPUT_ONCHANGE]: (e, obj) => {
									var id = obj.getValue();
									localStorage.setItem('testnet_default_symbol', id);
									this.setState({
										symbol: id,
									}, () => this.getAllData(0))
								},
								[INPUT_OPTION]: this.state.symbolOptions
							}}></Input>

						</div>

						<HighchartsReact
							highcharts={Highcharts}
							options={chartOptions}
							constructorType={'stockChart'}
							ref={c => this.chart = c}

						/>
						<div style={{ display: 'flex', alignItems: 'center', marginBottom: 15 }}>
							{this.khung.map(item => {
								return <div key={item} className='button btn' style={{ border: 'solid thin darkgray', borderRadius: 5, padding: '2px 5px', fontWeight: 'bold', background: (this.state.khung1 == item ? 'orange' : 'none') }} onClick={() => {
									this.setState({ khung1: item }, () => this.getAllData(1));
									localStorage.setItem('testnet_default_frame1', item);
								}}>{item}</div>
							})}
							<Input ref={c => this.histogramInput1 = c} placeholder="Histogram" className='input' struct={{
								[INPUT_TYPE]: 'select',
								[INPUT_DEFAULT]: this.state.histogram1,
								[INPUT_ONCHANGE]: (e, obj) => {
									var id = obj.getValue();
									localStorage.setItem('testnet_default_histogram1', id);
									this.setState({
										histogram1: id,
									}, () => this.getAllData(1))
								},
								[INPUT_OPTION]: {
									9: 'Histogram 9',
									7: 'Histogram 7',
									4: 'Histogram 4',
									2: 'Histogram 2',
									3: 'Histogram 3',
									5: 'Histogram 5',
									6: 'Histogram 6',
								}
							}}></Input>
							&nbsp;
							<Input ref={c => this.rsiEmaInput1 = c} placeholder="RSI EMA" className='input' struct={{
							[INPUT_TYPE]: 'select',
							[INPUT_DEFAULT]: this.state.rsi_ema1,
							[INPUT_ONCHANGE]: (e, obj) => {
								var id = obj.getValue();
								localStorage.setItem('testnet_default_rsi_ema1', id);
								this.setState({
									rsi_ema1: id,
								}, () => this.getAllData(1))
							},
							[INPUT_OPTION]: {
								9: 'RSI EMA 9',
								5: 'RSI EMA 5',
								4: 'RSI EMA 4',
							}
						}}></Input>
						&nbsp;

							<Input ref={c => this.symbolInput1 = c} placeholder="Symbol" className='input' struct={{
								[INPUT_TYPE]: 'select',
								[INPUT_DEFAULT]: this.state.symbol1,
								[INPUT_ONCHANGE]: (e, obj) => {
									var id = obj.getValue();
									localStorage.setItem('testnet_default_symbol1', id);
									this.setState({
										symbol1: id,
									}, () => this.getAllData(1))
								},
								[INPUT_OPTION]: this.state.symbolOptions
							}}></Input>

						</div>
						<HighchartsReact
							highcharts={Highcharts}
							options={chartOptions1}
							constructorType={'stockChart'}
							ref={c => this.chart1 = c}
						/>
						<div style={{ display: 'flex', alignItems: 'center', marginBottom: 15 }}>
							{this.khung.map(item => {
								return <div key={item} className='button btn' style={{ border: 'solid thin darkgray', borderRadius: 5, padding: '2px 5px', fontWeight: 'bold', background: (this.state.khung2 == item ? 'orange' : 'none') }} onClick={() => {
									this.setState({ khung2: item }, () => this.getAllData(2));
									localStorage.setItem('testnet_default_frame2', item);
								}}>{item}</div>
							})}
							<Input ref={c => this.histogramInput2 = c} placeholder="Histogram" className='input' struct={{
								[INPUT_TYPE]: 'select',
								[INPUT_DEFAULT]: this.state.histogram2,
								[INPUT_ONCHANGE]: (e, obj) => {
									var id = obj.getValue();
									localStorage.setItem('testnet_default_histogram2', id);
									this.setState({
										histogram2: id,
									}, () => this.getAllData(2))
								},
								[INPUT_OPTION]: {
									9: 'Histogram 9',
									7: 'Histogram 7',
									4: 'Histogram 4',
									2: 'Histogram 2',
									3: 'Histogram 3',
									5: 'Histogram 5',
									6: 'Histogram 6',
								}
							}}></Input>
							&nbsp;
							<Input ref={c => this.rsiEmaInput2 = c} placeholder="RSI EMA" className='input' struct={{
							[INPUT_TYPE]: 'select',
							[INPUT_DEFAULT]: this.state.rsi_ema2,
							[INPUT_ONCHANGE]: (e, obj) => {
								var id = obj.getValue();
								localStorage.setItem('testnet_default_rsi_ema2', id);
								this.setState({
									rsi_ema2: id,
								}, () => this.getAllData(2))
							},
							[INPUT_OPTION]: {
								9: 'RSI EMA 9',
								5: 'RSI EMA 5',
								4: 'RSI EMA 4',
							}
						}}></Input>
						&nbsp;
							<Input ref={c => this.symbolInput2 = c} placeholder="Symbol" className='input' struct={{
								[INPUT_TYPE]: 'select',
								[INPUT_DEFAULT]: this.state.symbol2,
								[INPUT_ONCHANGE]: (e, obj) => {
									var id = obj.getValue();
									localStorage.setItem('testnet_default_symbol2', id);
									this.setState({
										symbol2: id,
									}, () => this.getAllData(2))
								},
								[INPUT_OPTION]: this.state.symbolOptions
							}}></Input>

						</div>
						<HighchartsReact
							highcharts={Highcharts}
							options={chartOptions2}
							constructorType={'stockChart'}
							ref={c => this.chart2 = c}

						/>
					</div>

					<style>{`
					html, body, #app {
						height:100%;
						overflow-x: hidden;
					}
					.main {
						height: calc(100% - 60px)
					}
					.tooltip_chart {
						flex: 1
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
					chart: {
						width: this.chartContainer.clientWidth
					}

				},
				chartOptions1: {
					chart: {
						width: this.chartContainer.clientWidth
					}

				},
				chartOptions2: {
					chart: {
						width: this.chartContainer.clientWidth
					}

				}
			})
		}, 500);
	}


	getAllData(chart = null) {
		if (chart === null) {
			this.getData().then(res => {
				return this.getData(true, 5000, true, 1);
			}).then(res => {
				return this.getData(true, 5000, true, 2);
			}).then(res => {
				this.setRangeSelector(0);
			});
		} else {
			this.getData(true, 5000, true, chart).then(() => {
				this.setRangeSelector(chart);

			})
		}

	}
 

	setRangeSelector(chart=0){
		
		var max = Number(App.parsed['max']);
		var min = Number(App.parsed['min']);
		
		if(max > 0 && min > 0){
			this.chart.chart.xAxis[0].setExtremes(min, max);
		}else{
			if (chart == 1) {
				this.setState({
					chartOptions1: { rangeSelector: { selected: 4 } },
				})
			} else if (chart == 2) {
				this.setState({
					chartOptions2: { rangeSelector: { selected: 4 } },
				})
			} else {
				this.setState({
					chartOptions: { rangeSelector: { selected: 4 } },
				})
			}
		}
	}


	componentDidMount() {
		this.getAllData();
		this.updateInterval = setInterval(() => {
			this.getData(false, 5, false, 0);
			this.getData(false, 5, false, 1);
			this.getData(false, 5, false, 2);
		}, 5000);

		this.updateChartWidth();

		this.resize_ob = new ResizeObserver((entries) => {
			this.updateChartWidth()
		});
		this.resize_ob.observe(this.chartContainer);

		this.syncChart();
		this.getSymbol();

		if (App.accountSelector) {
			App.accountSelector.register('testnes_chart', () => {
				this.getAllData();
			});
		}



		
		

	}

	syncChart() {
		/**
 * In order to synchronize tooltips and crosshairs, override the
 * built-in events with handlers defined on the parent element.
 */
		['mousemove', 'touchmove', 'touchstart'].forEach(function (eventType) {
			document.getElementById('chartContainer').addEventListener(
				eventType,
				function (e) {
					var chart,
						point,
						i,
						event;

					for (i = Highcharts.charts.length - 1; i >= 0; i--) {
						chart = Highcharts.charts[i];
						// Find coordinates within the chart
						if (!chart) continue;
						event = chart.pointer.normalize(e);
						// Get the hovered point
						// point = chart.series[chart.series.length - 2].searchPoint(event, true);
						point = chart.series[0].searchPoint(event, true);

						if (point) {
							point.highlight(e);
						}
					}
				}
			);
		});

		/**
		 * Override the reset function, we don't need to hide the tooltips and
		 * crosshairs.
		 */
		Highcharts.Pointer.prototype.reset = function () {
			return undefined;
		};

		/**
		 * Highlight a point by showing tooltip, setting hover state and draw crosshair
		 */
		Highcharts.Point.prototype.highlight = function (event) {
			event = this.series.chart.pointer.normalize(event);
			this.onMouseOver(); // Show the hover marker
			// this.series.chart.tooltip.refresh(this); // Show the tooltip
			this.series.chart.xAxis[0].drawCrosshair(event, this); // Show the crosshair
		};



		// Get the data. The contents of the data file can be viewed at
	}

	/**
	 * Synchronize zooming through the setExtremes event handler.
	 */
	syncExtremes(e) {
		var thisChart = this.chart;

		if (e.trigger !== 'syncExtremes') { // Prevent feedback loop
			Highcharts.each(Highcharts.charts, function (chart) {

				if (chart && chart !== thisChart) {
					if (chart.xAxis[0].setExtremes) { // It is null while updating
						chart.xAxis[0].setExtremes(
							e.min,
							e.max,
							undefined,
							false,
							{ trigger: 'syncExtremes' }
						);
					}
				}
			});
		}
	}

	componentWillUnmount() {
		if (this.updateInterval) clearInterval(this.updateInterval);
		if (this.resize_ob) this.resize_ob.unobserve(this.chartContainer);
		App.accountSelector.unregister('testnes_chart')
	}



	getData(loading = true, limit = 1000, reset = true, chart = 0) {

		if (chart == 0) {
			var symbol = this.state.symbol;
			var frame = this.state.khung;
			var histogram = this.state.histogram;
			var rsi_ema_col = this.state.rsi_ema;
		} else if (chart == 1) {
			var symbol = this.state.symbol1;
			var frame = this.state.khung1;
			var histogram = this.state.histogram1;
			var rsi_ema_col = this.state.rsi_ema1;
		} else {
			var symbol = this.state.symbol2;
			var frame = this.state.khung2;
			var histogram = this.state.histogram2;
			var rsi_ema_col = this.state.rsi_ema2;
		}

		var account = App.accountSelector.selected();

		if (!symbol || !account) return Promise.reject(false);
		if (loading) App.loading(true)

		var url = '/admin/tradechart/getCandleData';
		return axios.request({
			url: url,
			method: 'POST',
			data: {
				symbol: symbol,
				interval: frame,
				limit: limit,
				account: account,
				
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
					var flag = get(allData['flag'], []);
					var altsData = get(response['data']['alts_coin'], []);
					// var labFlag = allData['lab_flag'];
					var dataLength = data.length;
					var macdData = [];
					// var signalData = [];
					var histogramData = [];
					var ema5Data = [];
					var ema9Data = [];
					var ema13Data = [];
					var flagData = [];
					var altsUp = [];
					var rsi = [];
					var rsi_ema = [];

					var orderFlag = allData['order_flag'];
					var orderFlagData = [];

					if (dataLength > 0 && data[dataLength - 1]['histogram'] == null) return;

					if (!reset) {
						if (chart == 1) {
							var serials = this.chart1.chart.series;
						} else if (chart == 2) {
							var serials = this.chart2.chart.series;
						} else {
							var serials = this.chart.chart.series;
						}

						for (let i in serials) {
							var serial = serials[i].userOptions;
							if (serial['id'] == 'aapl') ohlc = serial['data'].slice(0, serial['data'].length - 2);
							else if (serial['id'] == 'Histogram') histogramData = serial['data'].slice(0, serial['data'].length - 2);
							else if (serial['id'] == 'MACD') macdData = serial['data'].slice(0, serial['data'].length - 2);
							else if (serial['id'] == 'EMA5') ema5Data = serial['data'].slice(0, serial['data'].length - 2);
							else if (serial['id'] == 'EMA9') ema9Data = serial['data'].slice(0, serial['data'].length - 2);
							else if (serial['id'] == 'EMA13') ema13Data = serial['data'].slice(0, serial['data'].length - 2);
							else if (serial['id'] == 'Alts Up') altsUp = serial['data'];
							else if (serial['id'] == 'flag_event') flagData = serial['data'];
							else if (serial['id'] == 'Order') orderFlagData = serial['data'];
							else if (serial['id'] == 'RSI') rsi = serial['data'].slice(0, serial['data'].length - 2);
							else if (serial['id'] == 'RSI_EMA') rsi_ema = serial['data'].slice(0, serial['data'].length - 2);
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
								x: flag[i][ACTION_CHART],      // Point where the flag appears
								y: flag[i][ACTION_MATCHED_PRICE] == 0 ? flag[i][ACTION_ENTER_PRICE] : flag[i][ACTION_MATCHED_PRICE],
								title: flag[i][ACTION_TYPE] == '1' ? 'Long' : 'Short', // Title of flag displayed on the chart 
								text: flag[i][ACTION_MATCHED_PRICE],  // Text displayed when the flag are highlighted.
								fillColor: fillColor,
								profit: Number(flag[i][ACTION_PROFIT]),
								price: flag[i][ACTION_ENTER_PRICE],
								time: moment(flag[i][ACTION_CHART], 'x').format('HH:mm:ss'),
								matched: flag[i][ACTION_MATCHED_PRICE],
								matched_time: moment(flag[i][ACTION_MATCHED_TIME], 'x').format('HH:mm:ss'),
								sell: flag[i][ACTION_SELL_PRICE],
								sell_time: moment(flag[i][ACTION_SELL_TIME], 'x').format('HH:mm:ss'),
								param: flag[i][ACTION_STOP_REASON]
							}
						)
					}

					for (let i in orderFlag) {
						var fillColor = "white";
						orderFlagData.push(
							{
								x: orderFlag[i][ORDER_TIME],      // Point where the orderFlag appears
								y: orderFlag[i][ORDER_PRICE],
								title: orderFlag[i][ORDER_SIDE], // Title of orderFlag displayed on the chart 
								text: orderFlag[i][ORDER_PRICE],  // Text displayed when the orderFlag are highlighted.
								fillColor: fillColor,
								
								price: orderFlag[i][ORDER_PRICE],
								time: moment(orderFlag[i][ORDER_TIME], 'x').format('HH:mm:ss'),
								qty: orderFlag[i][ORDER_QTY],

							}
						)
					}



					if (altsData.length > 0) {
						for (let i in altsData) {
							altsUp.unshift(
								{
									x: altsData[i][CHANGE24H_TIME],      // Point where the flag appears
									y: altsData[i][CHANGE24H_UP]
								}
							)
						}
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

						var histoCol = histogram == 9 ? 'histogram' : `histogram${histogram}`;
						var rsiEmaCol = 'rsi_ema' + rsi_ema_col; 

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

					var chartOptions = {



						series: [

							{

								name: symbol + ' ' + frame,
								data: ohlc,
								id: 'aapl'
							},


							{

								data: histogramData,
								id: 'Histogram',

							},

							{

								data: macdData,
								id: 'MACD',


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

								data: ema5Data,
								id: 'EMA5',


							},
							{

								data: ema9Data,
								id: 'EMA9',


							},
							{

								data: ema13Data,
								id: 'EMA13',


							},

							{
								data: flagData,
							},

							{
								
								data: orderFlagData,
								
							}


							

						]
					}

					if (chart == 1) {
						
						this.setState({ chartOptions1: chartOptions })
					} else if (chart == 2) {
						this.setState({ chartOptions2: chartOptions })
					} else {
						chartOptions.series.push({
							data: altsUp,
						});
						chartOptions.series.push({
							yAxis: 2,
							name : 'Ema5',
							id: 'Alts Up Ema5',
							type: 'ema',
							linkedTo: 'Alts Up',
							params: {
								period: 5
							}
						});
						chartOptions.series.push({
							yAxis: 2,
							name : 'Ema9',
							id: 'Alts Up Ema9',
							type: 'ema',
							linkedTo: 'Alts Up',
							params: {
								period: 9
							}
						});
						chartOptions.series.push({
							yAxis: 2,
							name : 'Ema13',
							type: 'ema',
							id: 'Alts Up Ema13',
							linkedTo: 'Alts Up',
							params: {
								period: 13
							}
						});
						
						this.setState({ chartOptions });
					}

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


	getSymbol() {

		var wlModel = new Watchlist();
		wlModel.read(null, false).then((res) => {
			if (res['data']) {
				var response = res['data'];
				var symbolOptions = {};

				response.map(item => {
					symbolOptions[item[WL_SYMBOL]] = item[WL_SYMBOL];
				});

				this.setState({ symbolOptions })

			}
		})
	}





}

export default ChartView
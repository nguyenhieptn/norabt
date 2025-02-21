import React, { Component } from 'react'
import Highcharts from 'highcharts/highstock'
import HighchartsReact from 'highcharts-react-official'
import Input from '../../components/input/Input'
import SelectSymbol from '../../components/admin/SelectSymbol'
import ChartTooltip from '../../components/admin/ChartTooltip'

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

		this.khung = ['1m', '3m', '15m', '1h', '4h'];
		var dt = new Date();

		App.chartView = this;



		this.state = {
			// To avoid unnecessary update keep all options in the state.
			khung: get(localStorage.getItem('default_frame'), '15m'),
			histogram: get(localStorage.getItem('default_histogram'), '4'),
			rsi_ema: get(localStorage.getItem('default_lab_rsi_ema'), 9),
			tooltip: true,
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
					// crosshair: true,
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
						if (!points) return '';
						if (points.length == 1) return '';

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
								histogram.push({ name: id, value: Math.round(point.y * 10000) / 10000, color: get(point.color, 'black') });
							} else if (id == 'MACD') {
								macd.push({ name: id, value: Math.round(point.y * 10000) / 10000, color: get(point.color, 'black') });
							} else if (id == 'EMA5' || id == 'EMA9' || id == 'EMA13') {
								ema.push({ name: id, value: Math.round(point.y * 10000) / 10000, color: get(point.color, 'black') });
							} else if (id == 'Lab Price') {
								var color = (point.point.options.profit > 0 ? 'green' : 'red')
								lab1.push({ name: 'Order Price', value: point.point.options.price, color: color });
								lab1.push({ name: 'Order Time', value: point.point.options.time, color: color });
								lab2.push({ name: 'Sell Price', value: point.point.options.sell, color: color });
								lab2.push({ name: 'Sell Time', value: point.point.options.sell_time, color: color });
								lab3.push({ name: 'Profit', value: point.point.options.profit + '%', color: color });
								lab4.push({ name: 'Result', value: point.point.options.param, color: color });
							} else {
								showTooltip.push({ name: id, value: point.y, color: get(point.color, 'black') });
							}
						}

						var tooltip = `<div style="background:white; border:solid thin darkgray; padding:5px; top:-20px">
						<div style="margin-left:5px; color:blue"><b>${symbol} Time: </b>${moment(time, 'x').format('DD/MM HH:mm')}</div>
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

						if (App.chartView && App.chartView.tooltip) App.chartView.tooltip.setTooltip(tooltip);

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


				]

			},

			chartBTCOptions: {


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
						if (!points) return '';
						if (points.length == 1) return '';


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
								histogram.push({ name: id, value: Math.round(point.y * 10000) / 10000, color: get(point.color, 'black') });
							} else if (id == 'MACD') {
								macd.push({ name: id, value: Math.round(point.y * 10000) / 10000, color: get(point.color, 'black') });
							} else if (id == 'EMA5' || id == 'EMA9' || id == 'EMA13') {
								ema.push({ name: id, value: Math.round(point.y * 10000) / 10000, color: get(point.color, 'black') });
							} else if (id == 'Lab Price') {
								var color = (point.point.options.profit > 0 ? 'green' : 'red')
								lab1.push({ name: 'Order Price', value: point.point.options.price, color: color });
								lab1.push({ name: 'Order Time', value: point.point.options.time, color: color });
								lab2.push({ name: 'Sell Price', value: point.point.options.sell, color: color });
								lab2.push({ name: 'Sell Time', value: point.point.options.sell_time, color: color });
								lab3.push({ name: 'Profit', value: point.point.options.profit + '%', color: color });
								lab4.push({ name: 'Result', value: point.point.options.param, color: color });
							} else {
								showTooltip.push({ name: id, value: point.y, color: get(point.color, 'black') });
							}
						}

						var tooltip = `<div style="background:white; border:solid thin darkgray; padding:5px; top:-20px">
						<div style="margin-left:5px; color:blue"><b>${symbol} Time: </b>${moment(time, 'x').format('DD/MM HH:mm')}</div>
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

						if (App.chartView && App.chartView.tooltipBTC) App.chartView.tooltipBTC.setTooltip(tooltip);

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

				]

			},

			chartBTCDOMOptions: {


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
						if (!points) return '';
						if (points.length == 1) return '';

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
								histogram.push({ name: id, value: Math.round(point.y * 10000) / 10000, color: get(point.color, 'black') });
							} else if (id == 'MACD') {
								macd.push({ name: id, value: Math.round(point.y * 10000) / 10000, color: get(point.color, 'black') });
							} else if (id == 'EMA5' || id == 'EMA9' || id == 'EMA13') {
								ema.push({ name: id, value: Math.round(point.y * 10000) / 10000, color: get(point.color, 'black') });
							} else if (id == 'Lab Price') {
								var color = (point.point.options.profit > 0 ? 'green' : 'red')
								lab1.push({ name: 'Order Price', value: point.point.options.price, color: color });
								lab1.push({ name: 'Order Time', value: point.point.options.time, color: color });
								lab2.push({ name: 'Sell Price', value: point.point.options.sell, color: color });
								lab2.push({ name: 'Sell Time', value: point.point.options.sell_time, color: color });
								lab3.push({ name: 'Profit', value: point.point.options.profit + '%', color: color });
								lab4.push({ name: 'Result', value: point.point.options.param, color: color });
							} else {
								showTooltip.push({ name: id, value: point.y, color: get(point.color, 'black') });
							}
						}

						var tooltip = `<div style="background:white; border:solid thin darkgray; padding:5px; top:-20px">
						<div style="margin-left:5px; color:blue"><b>${symbol} Time: </b>${moment(time, 'x').format('DD/MM HH:mm')}</div>
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

						if (App.chartView && App.chartView.tooltipBTCDOM) App.chartView.tooltipBTCDOM.setTooltip(tooltip);

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
		const { chartOptions, chartBTCOptions, chartBTCDOMOptions } = this.state;


		return (
			<>
				<div style={{ position: 'fixed', zIndex: 10000, width: 'calc(100% - 15px)' }}>
					<div style={{ display: 'flex', width: '100%', overflow: 'hidden', height: (this.state.tooltip ? 'auto' : 0) }}>
						<ChartTooltip ref={c => this.tooltip = c}></ChartTooltip>
						<ChartTooltip ref={c => this.tooltipBTC = c}></ChartTooltip>
						<ChartTooltip ref={c => this.tooltipBTCDOM = c}></ChartTooltip>
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
				<div style={{ width: '100%', height: (this.state.tooltip ? 85 : 0) }}>

				</div>
				<br />

				<div style={{ position: 'relative', resize: 'both', overflow: 'auto' }} ref={c => this.chartContainer = c} onDoubleClick={() => {
					this.chartContainer.style.width = 'unset'
					this.chartContainer.style.height = 'unset'
				}}>


					<div style={{ display: 'flex', alignItems: 'center', position: 'absolute', top: 0, left: 0, zIndex: 100 }}>
						{this.khung.map(item => {
							return <div key={item} className='button btn' style={{ border: 'solid thin darkgray', borderRadius: 5, padding: '2px 5px', fontWeight: 'bold', background: (this.state.khung == item ? 'orange' : 'none') }} onClick={() => {
								this.setState({ khung: item }, () => this.getAllData(true));
								localStorage.setItem('default_frame', item);
							}}>{item}</div>
						})}
						<Input ref={c => this.histogramInput = c} placeholder="Histogram" className='input' struct={{
							[INPUT_TYPE]: 'select',
							[INPUT_DEFAULT]: this.state.histogram,
							[INPUT_ONCHANGE]: (e, obj) => {
								var id = obj.getValue();
								localStorage.setItem('default_histogram', id);
								this.setState({
									histogram: id,
								}, () => this.getAllData(true))
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
						&nbsp;
						<SelectSymbol onSelect={pro => {
							App.symbol = pro;
							this.getAllData();
						}}></SelectSymbol>

					</div>

					<div id="chartContainer" style={{ marginTop: 35 }}>
						<HighchartsReact
							highcharts={Highcharts}
							options={chartOptions}
							constructorType={'stockChart'}
							ref={c => this.chart = c}

						/>
						<HighchartsReact
							highcharts={Highcharts}
							options={chartBTCOptions}
							constructorType={'stockChart'}
							ref={c => this.chartBTC = c}

						/>
						<HighchartsReact
							highcharts={Highcharts}
							options={chartBTCDOMOptions}
							constructorType={'stockChart'}
							ref={c => this.chartBTCDOM = c}

						/>
					</div>

					<style>{`
					html, body, #app {
						height:100%;
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
				chartBTCOptions: {
					chart: {
						width: this.chartContainer.clientWidth
					}

				},
				chartBTCDOMOptions: {
					chart: {
						width: this.chartContainer.clientWidth
					}

				}
			})
		}, 500);
	}


	getAllData() {
		this.getData().then(res => {
			return this.getData(true, 1000, true, 'BTCUSDT');
		}).then(res => {
			return this.getData(true, 1000, true, 'BTCDOMUSDT');
		}).then(res => {
			this.setState({
				chartOptions: { rangeSelector: { selected: 2 } },
			})
		});
	}


	componentDidMount() {
		this.getAllData();



		this.updateInterval = setInterval(() => {
			this.getData(false, 5, false);
			this.getData(false, 5, false, 'BTCUSDT');
			this.getData(false, 5, false, 'BTCDOMUSDT');
		}, 5000);

		this.updateChartWidth();

		this.resize_ob = new ResizeObserver((entries) => {
			this.updateChartWidth()
		});
		this.resize_ob.observe(this.chartContainer);

		this.syncChart();

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

					for (i = 0; i < Highcharts.charts.length; i = i + 1) {
						chart = Highcharts.charts[i];
						// Find coordinates within the chart
						if (!chart) continue;
						event = chart.pointer.normalize(e);
						// Get the hovered point
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
			this.series.chart.tooltip.refresh(this); // Show the tooltip
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
	}



	getData(loading = true, limit = 1000, reset = true, symbol = null) {
		if (symbol == null) symbol = App.symbol;
		if (!symbol) return Promise.reject(false);
		if (loading) App.loading(true)
		return axios.request({
			url: `/admin/dashboard/getCandleData`,
			method: 'POST',
			data: {
				symbol: symbol,
				interval: this.state.khung,
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
					// var flag = allData['flag'];
					// var labFlag = allData['lab_flag'];
					var dataLength = data.length;
					var macdData = [];
					// var signalData = [];
					var histogramData = [];
					var ema5Data = [];
					var ema9Data = [];
					var ema13Data = [];
					// var flagData = [];
					// var labFlagData = [];
					var rsi = [];
					var rsi_ema = [];

					if (dataLength > 0 && data[dataLength - 1]['histogram'] == null) return;



					if (!reset) {
						if (symbol == 'BTCUSDT') {
							var serials = this.chartBTC.chart.series;
						} else if (symbol == 'BTCDOMUSDT') {
							var serials = this.chartBTCDOM.chart.series;
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
							else if (serial['id'] == 'RSI') rsi = serial['data'].slice(0, serial['data'].length - 2);
							else if (serial['id'] == 'RSI_EMA') rsi_ema = serial['data'].slice(0, serial['data'].length - 2);
						}
						// if (histogramData.length <= 2) histogramData = [];
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

					var chartOptions = {



						series: [

							{
								// type: 'candlestick',
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

						]
					}

					if (symbol == "BTCUSDT") {
						this.setState({ chartBTCOptions: chartOptions })
					} else if (symbol == 'BTCDOMUSDT') {
						this.setState({ chartBTCDOMOptions: chartOptions })
					} else {
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




}

export default ChartView
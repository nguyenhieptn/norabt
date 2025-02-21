import React, { Component } from 'react'
import Highcharts from 'highcharts/highstock'
import HighchartsReact from 'highcharts-react-official'
import Input from '../input/Input'
import Lab_campaigns from '../../model/admin/Lab_campaigns'
import ChartTooltip from '../admin/ChartTooltip'

// Load Highcharts modules
require('highcharts/indicators/indicators')(Highcharts)
require('highcharts/indicators/pivot-points')(Highcharts)
require('highcharts/indicators/macd')(Highcharts)
require('highcharts/modules/exporting')(Highcharts)
require('highcharts/modules/map')(Highcharts)
require('../Dashboard/hollowcandlestick')(Highcharts)

class Candle extends Component {

	constructor(props) {
		super(props);

		this.state = {

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
					text: get(this.props.title, ''),
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
					// useHTML: true,
					// backgroundColor: null,
					// borderWidth: 0,
					// shadow: false,
					// shared: true,
					// formatter: function () {
					// 	var points = this.points;
					// 	console.log(points)

					// 	if (!points) points = [this];


					// 	if (App.Candle && App.Candle.tooltip) App.Candle.tooltip.setTooltip(tooltip);

					// 	return `<div style="background:white; border:solid thin darkgray; padding:2px; border-radius:5px ; position:absolute;}</div>`

					// },

					// positioner: function () {
					// 	return { x: 0, y: 0 };
					// },
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

		var campaigns = this.state.campaigns;
		var campaignOption = {};
		for (let i in campaigns) {
			campaignOption[i] = campaigns[i][LAB_CAMPAIGN_NAME];
		}

		return (<>

			
			
			<div style={{ position: 'relative', resize: 'both', overflow: 'auto' }} ref={c => this.chartContainer = c} onDoubleClick={() => {
				this.chartContainer.style.width = 'unset'
				this.chartContainer.style.height = 'unset'
			}}>
				<ChartTooltip ref={c => this.tooltip = c}></ChartTooltip>
				<HighchartsReact
					highcharts={Highcharts}
					options={chartOptions}
					constructorType={'stockChart'}
					ref={c => this.chart = c}

				/>

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

		if(this.props.sourceMaker){
			this.props.sourceMaker(get(this.props.sourceMakerParams, {})).then(res => {
				this.processData(res)
			})
		}
		// this.updateInterval = setInterval(() => { this.getData(false, 5, false) }, 2000);

		this.updateChartWidth();

		this.resize_ob = new ResizeObserver((entries) => {
			this.updateChartWidth()
		});
		this.resize_ob.observe(this.chartContainer);

		
	}

	componentWillUnmount() {
		if (this.resize_ob) this.resize_ob.unobserve(this.chartContainer);
	}

	processData(data) {
		let ohlc = []
		for (var i = 0; i < data.length; i += 1) {
			ohlc.push([
				Number(data[i]['open_time']), // the date
				Number(data[i]['open']), // open
				Number(data[i]['high']), // high
				Number(data[i]['low']), // low
				Number(data[i]['close']) // close
			]);

		}

		console.log(ohlc)


		this.setState({
			chartOptions: {

				series: [
					{
						// type: 'candlestick',
						name: App.symbol,
						data: ohlc,
						id: 'aapl'
					},

				]
			}
		})


	}








}

export default Candle
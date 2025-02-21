import React, { Component } from 'react'
import Highcharts from 'highcharts/highstock'
import HighchartsReact from 'highcharts-react-official'

class TopBTCModal extends Component {

	constructor(props) {
		super(props);
		this.id = makeId();

		Highcharts.setOptions({
			time: {
				timezoneOffset: moment().utcOffset(),
				useUTC: false
			}
		});

		this.state = {

			address : '',

			chartOptions: {
				rangeSelector: {

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

				title: {

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
						text: '_____',
						x: 25,
					},

					resize: {
						enabled: true
					}
				}],

				series: [
					{
						name: 'BTC',
						id: 'max_profit',
						color: 'green',
						type : 'line',
						// lineWidth: 1,
						data: [],
					},
					{
						name: 'USD',
						id: 'min_profit',
						color: 'red',
						type : 'line',
						// lineWidth: 1,
						data: [],

					}
				]
			}

		}


	}

	modal(cmd = 'show') {
		if (cmd == 'hide') {
			$("#bladeModal" + this.id).modal('hide');
		} else {
			$("#bladeModal" + this.id).modal();
		}
	}


	componentDidMount() {
		// this.updateChartWidth()

	}


	getData(data) {
	
		this.setState({
			address : data
		});
		App.loading(true);
		return axios.request({
			url: `/admin/top_btc/getDataChart`,
			method: 'POST',
			data: {
				address: data
			}
		})

			.then(response => {
				App.loading(false);
				response = response['data']['data'];
				
				var dataBTC = [];
				var dataUSD = [];
				response.map(item => {

					dataBTC.push({
						"x": Number(item.top_btc_time) * 1000,
						"y": item.top_btc_btc
					});

					dataUSD.push({
						"x": Number(item.top_btc_time) * 1000,
						"y": item.top_btc_usd
					})


				})

					this.setState({
						chartOptions: {
							series: [
								{
									data: dataBTC,
								},
								{
									data: dataUSD,
								},
								
							]
						}
					});

				
				
			})

			.catch((error) => {
				App.loading(false);
				error_handle(error)
				return false;
			})
	}

	updateChartWidth() {
		if (this.updateWidthTimeout) clearTimeout(this.updateWidthTimeout);
		
		this.updateWidthTimeout = setTimeout(() => {
			console.log("Update Chart width");
			this.setState({
				chartOptions: {
					chart: {
						width: this.chartContainer.clientWidth < 25 ? this.chartContainer.clientWidth : this.chartContainer.clientWidth - 25
					}
				}
			})
		}, 500);
	}



	render() {

		return (
			<>
				<div className="modal fade" id={"bladeModal" + this.id}>
					<div className="modal-dialog modal-lg modal-dialog-centered" style={{ maxWidth: '95%' }}>
						<div className="modal-content">

							<div className="modal-header">
								<b>{this.state.address}</b>
								<button type="button" className="close" data-dismiss="modal">&times;</button>
							</div>

							<div ref={c => this.chartContainer = c} className="modal-body" style={{ textAlign: 'initial' }}>

								<HighchartsReact
									highcharts={Highcharts}
									options={this.state.chartOptions}
									constructorType={'stockChart'}
									ref={c => this.chart = c}

								/>

								
							</div>

							<div className="modal-footer">
								<button type="button" className="btn btn-danger" data-dismiss="modal">Close</button>
							</div>

						</div>
					</div>
				</div>

			</>
		)
	}




}
export default TopBTCModal
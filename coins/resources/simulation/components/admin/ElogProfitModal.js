import React, { Component } from 'react'
import Highcharts from 'highcharts/highstock'
import HighchartsReact from 'highcharts-react-official'

class ElogProfitModal extends Component {

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
						connectNulls: false,
						name: 'Max Profit',
						id: 'max_profit',
						color: 'green',
						lineWidth: 1,
						data: [],
					},
					{
						connectNulls: false,
						name: 'Min Profit',
						id: 'min_profit',
						color: 'red',
						lineWidth: 1,
						data: [],

					},
					{
						connectNulls: false,
						name: 'Profit',
						id: 'profit',
						color: 'blue',
						lineWidth: 1,
						data: [],

					},
					{
						connectNulls: false,
						name: 'Base Profit',
						id: 'baseprofit',
						color: 'orange',
						lineWidth: 1,
						data: [],

					},
					{
						type: 'flags',
						id: 'Finish',
						shape: 'squarepin',  // Defines the shape of the flags.
						name: 'Finish',

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
		this.updateChartWidth()

	}


	getData(campaign) {
		App.loading(true);
		return axios.request({
			url: `/admin/lab_event_logs/getProfit`,
			method: 'POST',
			data: {
				campaign: campaign
			}
		})

			.then(response => {
				App.loading(false);
				response = response['data'];
				if (response['result']) {

					var maxProfitData = [];
					var minProfitData = [];
					var profitData = [];
					var finishFlag = [];
					var baseProfitData = [];

					for(let i in response['data']['profit']){
						maxProfitData.push([response['data']['profit'][i][LAB_ELOG_TIME], response['data']['profit'][i][LAB_ELOG_MAXPROFIT]])
						minProfitData.push([response['data']['profit'][i][LAB_ELOG_TIME], response['data']['profit'][i][LAB_ELOG_MINPROFIT]])
						profitData.push([response['data']['profit'][i][LAB_ELOG_TIME], response['data']['profit'][i][LAB_ELOG_PROFIT]])
						baseProfitData.push([response['data']['profit'][i][LAB_ELOG_TIME], response['data']['profit'][i][LAB_ELOG_BASEPROFIT]])
					}

					for(let i in response['data']['finish']){
						finishFlag.push({
							x: response['data']['finish'][i][LAB_ELOG_TIME], 
							y: response['data']['finish'][i][LAB_ELOG_MAXPROFIT],
							text: 'Max:' + response['data']['finish'][i][LAB_ELOG_MAXPROFIT] + ' Min: '+response['data']['finish'][i][LAB_ELOG_MINPROFIT],
						})
					}

					this.setState({
						chartOptions: {
							series: [
								{
									data: maxProfitData,
								},
								{
									data: minProfitData,
								},
								{
									data: profitData,
								},
								{
									data: baseProfitData,
								},
								{
									title: 'Finished',
									data: finishFlag
								}
							]
						}
					}, ()=>this.updateChartWidth());

				}
				else {
					error_handle(response);
				}
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
export default ElogProfitModal
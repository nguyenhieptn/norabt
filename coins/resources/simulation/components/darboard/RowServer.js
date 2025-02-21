import React, { Component } from 'react'
import { Chart } from 'primereact/chart';
import Input from '../input/Input'
import Style from '../common/Style'
import { Link } from 'react-router-dom';



class RowServer extends Component {

	constructor(props) {
		super(props);

		this.state = {
			inteval: STATSCN_QUERIES_DAY
		}
	}



	render() {

		var agents = get(this.props.data['agents'], []);

		var agentsIndex = [];
		for (let i in agents) {
			agentsIndex[agents[i][AGENT_ID]] = agents[i];
		}

		var stats = get(this.props.data['stats'], []);
		var server = get(this.props.data['servers'], []);

		for (let i in server) {
			server[i]['queries'] = {};
			for (let j in stats) {
				if (stats[j][STATSCN_SRV_HOST] == server[i][CFG_SERVER_IP]
					&& stats[j][STATSCN_SRV_PORT] == server[i][CFG_SERVER_PORT]
					&& stats[j][STATSCN_HOSTGROUP] == server[i][CFG_SERVER_GID]
				) {
					var agentId = stats[j][STATSCN_AGENT];
					var agentIP = isset(agentsIndex[agentId]) ? agentsIndex[agentId][AGENT_IP] : 'Undefined';
					if (!isset(server[i]['queries'][agentIP])) {
						server[i]['queries'][agentIP] = Number(stats[j][this.state.inteval])
					} else {
						server[i]['queries'][agentIP] += Number(stats[j][this.state.inteval])
					}

					if (!isset(server[i]['queries']['Total'])) {
						server[i]['queries']['Total'] = Number(stats[j][this.state.inteval])
					} else {
						server[i]['queries']['Total'] += Number(stats[j][this.state.inteval])
					}

					server[i][CFG_SERVER_STATUS] = stats[j][STATSCN_STATUS];
				}
			}
		}


		return (
			<div className='row' style={{ margin: '15px', position:'relative' }}>

				<div style={{ position: 'absolute', right:0, top:-15 }}>
					<select className='input' value={this.state.inteval} onChange={(e) => this.setState({ inteval: e.target.value })}>
						<option value={STATSCN_QUERIES_REAL}>{lang('Real time')}</option>
						<option value={STATSCN_QUERIES_HOUR}>{lang('Hour')}</option>
						<option value={STATSCN_QUERIES_DAY}>{lang('Today')}</option>
						<option value={STATSCN_QUERIES}>{lang('Total')}</option>
					</select>
				</div>

				{server.map((item, key) => {
					return <ServerItem key={key} data={item} inteval={this.state.inteval}></ServerItem>
				})}


			</div>
		);
	}


}

export default RowServer;


class ServerItem extends Component {

	render() {
		var data = get(this.props.data, {})
		var queries = get(data['queries'], {});


		const options = {
			responsive: true,
			maintainAspectRatio: false,
			legend: false,
			scales: {
				yAxes: [{
					type: 'linear',
					display: true,
					ticks: {
						min: 0,
					},
				}],

				xAxes: [{
					categoryPercentage: 0.3,
					barPercentage: 1.0
				}],

			},
			animation: {
				onComplete: function (chartInstance) {
					console.log('test');
					var ctx = chartInstance.chart.ctx;
					ctx.textAlign = 'center';
					ctx.textBaseline = 'bottom';
					this.data.datasets.forEach(function (dataset, i) {
						var meta = chartInstance.chart.controller.getDatasetMeta(i);
						meta.data.forEach(function (bar, index) {
							var data = dataset.data[index];
							ctx.fillText(data, bar._model.x, bar._model.y - 5);
						});
					});
				}
			}

		}

		var labels = Object.keys(queries);
		var datasets = [{
			data: Object.values(queries),
			backgroundColor: '#42A5F5',
		}];
		var charData = { labels, datasets };

		return <div style={{display:'flex', width: '50%', padding:5}}><div className='box_shadow box_padding' style={{width:'100%', background: 'white', fontSize: 14 }}>
			<h4><i className='fa fa-database'></i>&nbsp;<strong>{data[CFG_SERVER_IP]}:{data[CFG_SERVER_PORT]}</strong></h4>
			<div className='box_flex'>

				<div style={{ padding: '5px 15px', display:'flex' }}>
					<strong>Status: </strong>
					{data[CFG_SERVER_STATUS] == 'ONLINE'
						? <span className='box_flex box_line' style={{ fontWeight: 'bold', color: '#00d700' }}>{data[CFG_SERVER_STATUS]}</span>
						: <span className='box_flex box_line' style={{ fontWeight: 'bold', color: 'red' }}>{data[CFG_SERVER_STATUS]}</span>
					}</div>

				<div style={{ padding: '5px 15px', display:'flex' }}>
					<strong>Group: </strong>
					<span className='box_flex box_line' style={{ fontWeight: 'bold', color: '#00d700' }}>{data[CFG_SERVER_GID]}</span>
				</div>

			</div>

			<Chart height="200" width="100%" type="bar" data={charData} options={options} />

		</div>
		</div>



			

	}
}





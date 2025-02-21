import React, { Component } from 'react'
import Style from '../common/Style'



class RowTable extends Component {

	constructor(props) {
		super(props);

		this.state = {
			freeLabs: [],
			pendingLabs: [],
		}
	}


	loadFreeLabs() {
		App.loading(true, 'Loading...')
		return axios.request({
			url: '/admin/labs/getFreeLabs',
			method: 'post',
		})

			.then(response => {
				App.loading(false, 'Loading...');
				response = response['data'];
				if (response['result']) {
					var data = response['data'];
					this.setState({ freeLabs: data });
				}
				return Promise.reject(response);
			})

			.catch(function (error) {
				console.log(error);
				App.loading(false, 'Loading...');
				error_handle(error)
			})
	}
	loadPendingLabs() {
		App.loading(true, 'Loading...')
		return axios.request({
			url: '/admin/labs/getPendingLabs',
			method: 'post',
		})

			.then(response => {
				App.loading(false, 'Loading...');
				response = response['data'];
				if (response['result']) {
					var data = response['data'];
					this.setState({ pendingLabs: data });
				}
				return Promise.reject(response);
			})

			.catch(function (error) {
				console.log(error);
				App.loading(false, 'Loading...');
				error_handle(error)
			})
	}



	render() {

		return (
			<>
				<Style id='row_table_css'>{`
				.row_table_img{
					width: 40px;
					height: 40px;
					border-radius: 50%;
					border: solid thin darkgray;
				}
				.p-panel-content table{
					font-size: 14px;
				}
				.rowtable .p-component{
					border: 1px solid #c8c8c8;
					width: 100%;
					border-radius: 5px;
				}
				.rowtable .p-panel .p-panel-content{
					border: none;
				}
				.rowtable .p-panel .p-panel-titlebar{
					border:none;
				}
			`}</Style>
				<div className='row rowtable'>

					<div className='col-md-6 d-flex'>
						<div className="p-panel p-component">
							<div className="p-panel-titlebar">
								<span className="p-panel-title">
									<span>
										<i className="fa fa-globe">
										</i>
									&nbsp;
									<span>Top Free Labs</span>
									</span>
								</span>
							</div>
							<div className="p-toggleable-content">
								<div className="p-panel-content">
									<table className="table table-striped table-borderless">
										<thead>
											<tr>
												<th></th><th></th><th></th>
												<th style={{ whiteSpace: 'nowrap', textAlign: 'center' }}><span>Total Download</span></th>
											</tr>
										</thead>
										<tbody>
											{this.state.freeLabs.map((item, key) => {
												return <tr key={key}>
													<th>{key + 1}</th>
													<td><img className='row_table_img' src={file_public(item[LAB_IMG])}></img></td>
													<td>{item[LAB_NAME]}</td>
													<th style={{ textAlign: 'center' }}>{item[LAB_COUNT_DOWNLOADED]}</th>
												</tr>
											})}
										</tbody>
									</table>
								</div>
							</div>
						</div>
					</div>

					<div className='col-md-6 d-flex'>

						<div className="p-panel p-component">
							<div className="p-panel-titlebar">
								<span className="p-panel-title">
									<span>
										<i className="fa fa-globe">
										</i>
									&nbsp;
									<span>Pending Labs</span>
									</span>
								</span>
							</div>
							<div className="p-toggleable-content">
								<div className="p-panel-content">
									<table className="table table-striped table-borderless">
										<thead>
											<tr>
												<th></th><th></th><th></th>
												<th style={{ whiteSpace: 'nowrap', textAlign: 'center' }}><span>Pending Time</span></th>
											</tr>
										</thead>
										<tbody>
											{this.state.pendingLabs.map((item, key) => {
												return <tr key={key}>
													<th>{key + 1}</th>
													<td><img className='row_table_img' src={file_public(item[LAB_IMG])}></img></td>
													<td>{item[LAB_NAME]}</td>
													<th style={{ textAlign: 'center' }}>{moment(item[LAB_PENDING_TIME], 'X').format('lll')}</th>
												</tr>
											})}
										</tbody>
									</table>
								</div>
							</div>
						</div>

					</div>


				</div>
			</>
		);
	}

	componentDidMount() {
		this.loadFreeLabs();
		this.loadPendingLabs();
	}
}

export default RowTable;



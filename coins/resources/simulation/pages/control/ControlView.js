

import React, { Component } from 'react'
import ShowDbModal from '../../components/admin/ShowDbModal';
import FormInput from '../../components/input/FormInput';
import Input from '../../components/input/Input';


class Control extends Component {

	constructor(props) {
		super(props);

		this.state = {
			content: ''
		}

		this.struct = {
			'remote_server':{
				[INPUT_NAME]: lang('LAB Server'),
				[INPUT_TYPE]: 'select',
				[INPUT_OPTION]: {
					LONG_VAN_3_CPU32_RAM126: 'LONG_VAN_3_CPU32_RAM126',
					local: 'Local',
				},
			},
			'control_lab_db': {
				[INPUT_NAME]: lang('LAB Database'),
				[INPUT_TYPE]: 'select',
				[INPUT_OPTION]: {
					coin_lab_1_year: 'Database 365 days',
					coin_crawler: 'Database 250ms',
					coin_future: 'Database 1m future',
					coin_spot: 'Database 1m spot',
					ftx_backtest_data: 'FTX backtest data(lv3)',
					backtest_data_1m: 'Backtest Data 1m future(lv3)',
					backtest_data_1m_spot: 'Backtest Data 1m spot(lv3)',
				},
				[INPUT_DES]: <div className='button btn btn-primary  btn-sm' onClick={() => { this.showdb.setData(this.form.getValue());this.showdb.modal() }} style={{ fontSize: 12 }}>Show db</div>
			},
		}
	}

	render() {
		return (<>
			<div className='box_shadow box_padding'>
				<h4>Database Setting</h4>
				<br />
				<div>
					<FormInput ref={e => this.form = e} struct={this.struct}></FormInput>
					
				</div>
				<br />
				<div className='box_flex'>
					<button style={{margin:'auto 0px auto auto'}} onClick={() => {
						this.updateData(this.form.getValue())
					}} className="button btn btn-primary">{lang('Save')}</button>
				</div>

				<ShowDbModal ref={e => this.showdb = e}></ShowDbModal>
			
			</div>
		</>
		);
	}

	componentDidMount() {
		this.loadData()
	}

	

	loadData() {
		App.loading(true, 'Loading...');
		return axios.request({
			url: '/control/control/read',
			method: 'post',
			data: {
				keys: ['control_lab_db','remote_server']
			}
		})

			.then(response => {
				App.loading(false, 'Adding...');
				response = response['data'];
				if (response['result']) {
					this.form.setValue(response['data'])
					if(isset(response['data']['control_logo'])){
						if (this.editor) this.editor.editor.setData(response['data']['control_logo']);
						this.setState({content: response['data']['control_logo']})
					}
				} else {
					return Promise.reject(response);
				}
			})

			.catch((error)=> {
				console.log(error);
				App.loading(false, 'Adding...');
				error_handle(error)
			})
	}

	updateData(data) {
		App.loading(true, 'Loading...');
		return axios.request({
			url: '/control/control/update',
			method: 'post',
			data: data,
		})

			.then(response => {
				App.loading(false, 'Adding...');
				response = response['data'];
				if (response['result']) {
					Swal(true, 'Success', 'success');
				} else {
					error_handle(response);
				}
			})

			.catch((error)=> {
				console.log(error);
				App.loading(false, 'Adding...');
				error_handle(error)
			})
	}



}

export default Control
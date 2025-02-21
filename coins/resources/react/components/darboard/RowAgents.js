import React, { Component } from 'react'
import {Chart} from 'primereact/chart';
import Input from '../input/Input'
import Style from '../common/Style'
import { Link } from 'react-router-dom';


class RowAgent extends Component { 
	
	constructor(props) {
		super(props);
		
		this.state = {
			
		}
	}
	

	
	render () {

		var agents = get(this.props.data['agents'], []);
		var monitor = get(this.props.data['monitor'], []);

		for(let i in agents){
			agents[i]['servers'] = [];
			for(let j in monitor){
				if(monitor[j][MONCN_AGENT] == agents[i][AGENT_ID]){
					agents[i]['servers'].push(monitor[j])
				}
			}
		}

	
		return (
			<div className='row' style={{margin:'15px'}}>

				{agents.map((item,key) => {
					return <AgentItem key={key} data={item}></AgentItem>
				})}
				

			</div>
		);
	}

	
}

export default RowAgent; 


class AgentItem extends Component {

    render() {
		var data = get(this.props.data, {})
		var servers = get(data['servers'], []);
    	return <div style={{width:'50%', padding:5, display:'flex'}}>
			<div className='box_shadow box_padding' style={{width:'100%', background:'white', fontSize:14}}>
			<h4><i className='fa fa-cubes'></i>&nbsp;<strong>{data[AGENT_IP]}</strong></h4>
			<div className='box_flex'>
				
				<div className='col-md-6'>
					
					<div style={{padding:5}}>
						<strong>Status: </strong>
						{data[AGENT_STATUS] == 1
						?<div className='box_flex box_line' style={{ fontWeight: 'bold', color: '#00d700' }}><i className="fa fa-circle"></i>&nbsp;Connected</div>
						:<div className='box_flex box_line' style={{ fontWeight: 'bold', color: 'red' }}><i className="fa fa-circle"></i>&nbsp;Disconnected</div>
					}</div>
					
					<div style={{padding:5}}>
						<strong>Active: </strong>
						{data[AGENT_ACTIVE] == 1
						?<div className='box_flex box_line' style={{ fontWeight: 'bold', color: '#00d700' }}><i className="fa fa-circle"></i>&nbsp;Actived</div>
						:<div className='box_flex box_line' style={{ fontWeight: 'bold', color: 'red' }}><i className="fa fa-circle"></i>&nbsp;Disabled</div>
					}</div>

					<div style={{padding:5}}>
						<strong>Synchronized: </strong>
						{data[AGENT_ACTIVE] == 1
						?<div className='box_flex box_line' style={{ fontWeight: 'bold', color: '#00d700' }}><i className="fa fa-circle"></i>&nbsp;Synchronized</div>
						:<div className='box_flex box_line' style={{ fontWeight: 'bold', color: 'red' }}><i className="fa fa-circle"></i>&nbsp;Sync Failed</div>
					}</div>
				</div>

				<div className='col-md-6'>
					<strong>Mysql Servers</strong>
					{servers.map((item, key) => {
						return <div key={key} className='box_flex' style={{color: (item[MONCN_CONNECT_ERROR]==null ? '#00d700' : 'red'), padding:5}}><i className="fa fa-circle"></i>&nbsp;{item[MONCN_HOSTNAME]}:{item[MONCN_PORT]}</div>
					})}
				</div>
			</div>
		</div>
		</div>
    		
    		
    		
    	;
    	
    }
}




	  
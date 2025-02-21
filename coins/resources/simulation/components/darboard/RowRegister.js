import React, { Component } from 'react'
import {Chart} from 'primereact/chart';
import Style from '../common/Style'


class RowRegister extends Component { 
	
	constructor(props) {
	    super(props);
	    
	   this.state = {
		   data: [],
		   timeUnit: 'day',
	   }
	    
	    
	} 

	loadData(){
		var timeUnit = this.state.timeUnit;

		this.schedule = {};
		if(timeUnit == 'day'){
			var unit = 86400;
			var startTime = Number(moment().startOf(timeUnit).format('X'));
			for (let i = 0; i < 15; i++){
				var start = startTime - i*unit
				this.schedule[i] = [start, start + unit]
			}
		}
		if(timeUnit == 'week'){
			var unit = 604800;
			var startTime = Number(moment().startOf(timeUnit).format('X'));
			for (let i = 0; i < 15; i++){
				var start = startTime - i*unit
				this.schedule[i] = [start, start + unit]
			}
		}
		if(timeUnit == 'month'){
			var unit = 2592000;
			var startTime = Number(moment().startOf(timeUnit).format('X'));
			for (let i = 0; i < 15; i++){
				var start = startTime - i*unit
				this.schedule[i] = [start, start + unit]
			}
		}


		return axios.request ({
		    url: '/admin/dashboard_login/registed',
			method: 'post',
			data: {
				[AUTHEN_TIME]: startTime-15*unit
			}
			})
			
	      .then(response => {
	    	  App.loading(false, 'Loading...');
	    	  response = response['data'];
	    	  if(response['result']){
				  var data = response['data'];
				  this.setState({data});
              }else{
				return Promise.reject(response);
			  }
              
	      })
	      
	      .catch(function (error) {
	    	  console.log(error);
	    	  App.loading(false, 'Loading...');
	    	  error_handle(error)
	      })




	}
	
	processData(){
		
		var schedule = this.schedule? this.schedule: {};
		var datas = this.state.data;
		var dataSch = {};
		var index = 0;
		
		for ( let i in datas){
			var data = datas[i];
			data[AUTHEN_TIME] = Number(data[AUTHEN_TIME]);
			if(schedule[index] && data[AUTHEN_TIME] >= schedule[index][0] && data[AUTHEN_TIME] < schedule[index][1]){
				if(!dataSch[index]){
					dataSch[index] = 1;
				}else{
					dataSch[index] ++;
				}
			} else if(schedule[index+1] && data[AUTHEN_TIME] >= schedule[index+1][0] && data[AUTHEN_TIME] < schedule[index+1][1]){
				index ++;
				if(!dataSch[index]){
					dataSch[index] = 1;
				}else{
					dataSch[index] ++;
				}
			} else {
				for (let j in this.schedule){
					if(data[AUTHEN_TIME] >= schedule[j][0] && data[AUTHEN_TIME] < schedule[j][1]){
						index = j;
						if(!dataSch[index]){
							dataSch[index] = 1;
						}else{
							dataSch[index] ++;
						}
						break;
					}
				}
			}
			
		}

		var labels = Object.values(schedule).map(item => moment(item[0], 'X').format('D/M/Y')).reverse();
		var datasets = [{
				data: labels.map((item, key) => { return dataSch[key] ? dataSch[key] : 0 }).reverse(),
				backgroundColor: '#42A5F5',
			}
		]

		
		var data = {labels, datasets};
		
		return data;
		
	}
	
	
	 render () {
		 
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
		                	categoryPercentage: 0.5,
		                	barPercentage: 1.0
		                }],
		                
					},
					animation: {
						onComplete: function(chartInstance) {
							console.log('test');
							var ctx = chartInstance.chart.ctx;
							ctx.textAlign = 'center';
							ctx.textBaseline = 'bottom';
							this.data.datasets.forEach(function(dataset, i) {
							var meta = chartInstance.chart.controller.getDatasetMeta(i);
							meta.data.forEach(function(bar, index) {
								var data = dataset.data[index];
								ctx.fillText(data, bar._model.x, bar._model.y - 5);
							});
							});
						}
					}
		        }
		 
		  var data = this.processData();
		  return(
			<div>
				<div className='box_flex'>
					<strong>Registers</strong>
					<div style={{margin:'auto 0px auto auto'}}>
						<select style={{padding:5}} value={this.state.timeUnit} onChange={(e)=>{this.setState({timeUnit: e.target.value}, ()=>this.loadData())}}>
							<option value='day'>Day</option>
							<option value='week'>Week</option>
							<option value='month'>Month</option>
						</select>
					</div>
				</div>
		  		<Chart height="400" width="100%" type="bar" data={data} options={options} />
			</div>);
	 }

	 componentDidMount(){
		 this.loadData();
	 }
}



export default RowRegister; 





	  
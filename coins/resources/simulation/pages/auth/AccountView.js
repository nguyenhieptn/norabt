import React, { Component } from 'react'
import Group from '../../components/auth/Group'
class Account extends Component { 
	
	constructor(props) {
	    super(props);
	    this.state={
	    		rootGroups: {},
	    		user: {}
	    };
	    this.dragComp = null;
	  }
	
	setDragComp(comp){
		this.dragComp = comp;
		console.log(comp);
		
	} 
	
	getDragComp(){
		return this.dragComp;
	} 
	
	createRootGroups(){
		var rootGroups = this.state.rootGroups;
		
		let output = [];
		if(count(rootGroups) == 0) return output;
		
		for(let i = 0; i < count(rootGroups); i++ ){
			output.push(<Group key={rootGroups[i][global.GROUP_ID]} frame={this} group={rootGroups[i]} member={this.state.user} expand={true} root={true}></Group>); 
		}
		return output;
	}
	
	componentDidMount () {
	    axios.post('/auth/account/getInitialGroup')
	      .then(response => {
	    	  response = response['data'];
	    	  if(response['result']){
	    		  this.setState({ 
	    			  rootGroups : response['data']['groups'], 
	    			  user : response['data']['user'] });
	    	  }else{
	    		  Swal(response['message'], response['data'], 'error');
	    	  }
	      })
	      .catch((error)=> {
	    	  Swal('Error', error, 'error');
	      })
	  }
	 
	  render () {
		  
		  return(
				  <div>
					  {this.createRootGroups()}
					  
				  </div>
				  );
	  }
}

export default Account;
	  
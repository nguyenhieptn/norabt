import React, { Component } from 'react'
import Menu from '../menu/Menu'
import scss from '@root/assets/css/constants.module'

class Layout extends Component {
	
	constructor(props) {
	    super(props);
	    
	    this.state = {
			menu: this.loadDefault(),
			page: '',
	    }
	    
		console.log(scss);
	}
	
	loadDefault(){
		if( App.isMobile() ) {
	    	 return status = 'closed';
	    }else {
	    	return '';
	    }
	}

	closeMenu(){
		this.setState({menu: 'closed'});
	}

	openMenu(){
		this.setState({menu: ''});
	}

	getMenuState(){
		return this.state.menu;
	}
	
	render () { 
		
		return(
				
		  <>
		  
		  	<style>{`
				.modal {
					left: ${this.state.menu == '' ? scss.menu_left : 0};
		  			max-width: ${screen.width * 1.25}
				}
			`}</style>
			
	  
		  	  <Menu layout = {this}></Menu>
		  
		      <div className = {"main "+this.state.menu}>
				  	{this.props.children}
			  </div>
			  
		  </>	
		  );
	}
}
export default Layout
	  
import React, { Component } from 'react'
import FormEditor from './FormEditor' 

class FuncEditRow extends Component {
	
	
	
	constructor(props, context) {
	    super(props, context);
	    this.table = this.context;
	   
	}
	
	initial(){
		this.rowData = this.props.rowData;
	}
	
	render () {
		  this.initial();
		  return(
				  <div>
				  
					 <div className="button" title={lang('Edit Row')} onClick={(e) => {
						 if(this.props.onClick){
							this.props.onClick(e);
							return;
						}else{
							this.table.children['EditModal'].loadData(this.rowData);
						 	this.table.children['EditModal'].modal();
						}
						 
					 }}>
						{this.props.children 
							?this.props.children
							:<i className="fa fa-edit"></i>
						}
					 	
					 </div>
					  
				 </div>
		)  
	}
}

FuncEditRow.contextType = TableContext;
export default FuncEditRow
	  
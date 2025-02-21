import React, { Component } from 'react'
import FormEditor from './FormEditor' 

class FuncDelRow extends Component {
	
	constructor(props, context) {
	    super(props, context);
	    this.table = this.context;
	   
	}
	
	initial(){
		this.rowData = this.props.rowData;
	}
	
	onClickHandle(){
		if(this.props.onClick){
			this.props.onClick(this.rowData);
			return;
		}
		
		const {key, value} = this.table.createKey(this.rowData);
		this.table.delRow(value).then( res=>{
			if(res){
				if(this.table.loadOrigin){
					this.table.loadOrigin();
				}else{
					this.table.filter();
				}
			}
		});
	}
	
	
	
	render () {
		  this.initial();
		  return(
				 <div className="button" title={lang("Delete Row")} onClick={() => {this.onClickHandle()}}>
				 	<i className="fa fa-trash"></i>
				 </div>
		)  
	}
}

FuncDelRow.contextType = TableContext;
export default FuncDelRow
	  
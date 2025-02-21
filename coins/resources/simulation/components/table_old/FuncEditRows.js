import React, { Component } from 'react'
import FormEditor from './FormEditor' 

class FuncEditRows extends Component {
	
	constructor(props, context) {
	    super(props, context);
	    this.table = this.context;
	    this.table.children['FuncEditRows'] = this;
	    this.id = this.table[STRUCT_TABLE][DATA_TABLE_ID] + Math.floor(Math.random() * 10000);
	    
	    if(!this.props.upload){
	    	this.upload = this.table.upload;
	    }else{
	    	this.upload = this.props.upload;
	    }
	   
	}
	
	initial(){
		this.struct = {};
		this.permitCol = this.table[STRUCT_TABLE][DATA_PERMIT_COL];
		for(let i in this.permitCol){
			if(!this.table[STRUCT_EDIT][i]) continue;
			this.struct[i] = this.table[STRUCT_EDIT][i];
			if(this.permitCol[i] == 'Read'){
				this.struct[i][EDIT_WRITABLE] = false;
			}else{
				this.struct[i][EDIT_WRITABLE] = true;
			}
		}
	}
	
	onClickHandle(){
	
		this.upload(this.form).then(response =>{
			
			 if(response){
				 
				var rowData = this.form.getValue();
					
				if(this.table[STRUCT_TABLE][DATA_EDITOR]){
					rowData = {...rowData, ...this.table[STRUCT_TABLE][DATA_EDITOR]}
				}
				this.editRow(rowData)
	    	  }
		});
	}
	
	async editRow(newData){
		
		var dataSelect = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];
		for(let i in dataSelect){
			const {key, value} = this.table.createKey(dataSelect[i]);
			
			var result = await this.table.editRow(value, newData);
			if(!result) break;
		}
			
		$("#edit_row_modal"+this.id).modal('hide');

		this.table[STRUCT_TABLE][DATA_SELECT_ROWS] = {};
		
		if(this.table.loadOrigin){
			this.table.loadOrigin();
		}else{
			this.table.filter();
		}
		
	}
	
	
	reload(){
		this.forceUpdate();
	}
	
	render () {
		  this.initial();
		  var text = get(this.props.text, 'Sửa');
		  return(
				  <div className="table_function">
				  
					 <div className="button" title="Sửa dòng đã chọn" onClick={() => {
						 $("#edit_row_modal"+this.id).modal();
						 this.form.setState({select:{}});
						 
					 }} style={{display: 'flex'}}>
					 	<i className="fa fa-edit"></i>&nbsp;{text}
					 </div>
					  
					<div className="modal fade" id={"edit_row_modal"+this.id} onClick={()=>{addClass($('body')[0], 'modal-open')}}> 
						<div className="modal-dialog modal-lg modal-dialog-centered">
							<div className="modal-content">
		
								<div className="modal-header">
									<h4 className="modal-title">{"Sửa hàng đã chọn"}</h4>
									<button type="button" className="close" data-dismiss="modal">&times;</button>
								</div>
								
								<div className="modal-body">
									<FormEditor ref={form => this.form = form} struct = {this.struct} select={true}></FormEditor> 
								</div>
								
								<div  className="modal-footer"> 
								  	<button type="button" className="btn btn-primary" onClick = {() => {this.onClickHandle()}}>Save</button>
							        <button type="button" className="btn btn-danger" data-dismiss="modal">Close</button>
						        </div>
							</div>
						</div>
					</div>
				</div>
		)  
	}
}

FuncEditRows.contextType = TableContext;
export default FuncEditRows
	  

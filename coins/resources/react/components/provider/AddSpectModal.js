import React, { Component } from 'react'

class AddSpectModal extends Component {
	
	constructor(props ) {
	    super(props);
	   
        this.id = makeId();
        this.state = {
            name : ''
        }
	   
	}
	
	
	modal(cmd='show'){
		if(cmd=='hide'){
			$("#modal"+this.id).modal('hide');
		}else{
			$("#modal"+this.id).modal();
		}
    }
    
    onClickHandle(){
        if(this.props.onClick) this.props.onClick(this.state.name);
        this.modal('hide')
    }
	
	render () {
		 
		  return(
					<div className="modal fade" id={"modal"+this.id} onClick={()=>{addClass($('body')[0], 'modal-open')}}> 
						<div className="modal-dialog modal-lg modal-dialog-centered">
							<div className="modal-content">
		
								<div className="modal-header">
									<h4 className="modal-title">{lang("Add Row")}</h4>
									<button type="button" className="close" data-dismiss="modal">&times;</button>
								</div>
								
								<div className="modal-body">
                                    <input className='input_item_input' style={{width: '100%'}} type='text' value={this.state.name} onChange={(e)=> this.setState({name: e.target.value})}></input>
								</div>
								
								<div  className="modal-footer"> 
								  	<button type="button" className="btn btn-primary" onClick = {() => {this.onClickHandle()}}>{lang('Add')}</button>
							        <button type="button" className="btn btn-danger" data-dismiss="modal">{lang('Close')}</button>
						        </div>
							</div>
						</div>
					</div>
		)  
	}
}

export default AddSpectModal
	  
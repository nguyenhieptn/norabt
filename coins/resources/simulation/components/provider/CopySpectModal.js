import React, { Component } from 'react'

class CopySpectModal extends Component {
	
	constructor(props ) {
	    super(props);
	   
        this.id = makeId();
        this.state = {
			products: {},
			selected: ''
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
	

	loadProducts(){
		return axios.request({
            url: '/provider/specifications/getSampleProduct',
            method: 'post',
        })

            .then(response => {
                App.loading(false, 'Adding...');
                response = response['data'];
                if(response['result']){
                    this.setState({products: response['data']});
                    return true;
                }
                return Promise.reject(response);
            })

            .catch((error)=> {
                console.log(error);
                App.loading(false, 'Adding...');
                error_handle(error)
                return Promise.reject();
            })
	}

	onClickHandle(){
		return axios.request({
            url: '/provider/specifications/read',
			method: 'post',
			data : {
				[PRODUCT_ID]: this.state.selected
			}
        })

            .then(response => {
                App.loading(false, 'Adding...');
                response = response['data'];
                if(response['result']){
                    if(this.props.onCopy) this.props.onCopy(response['data']);
                    return true;
                }
                return Promise.reject(response);
            })

            .catch((error)=> {
                console.log(error);
                App.loading(false, 'Adding...');
                error_handle(error)
                return Promise.reject();
            })
	}

	componentDidMount(){
		this.loadProducts();
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
                                    <select className='input_item_input' style={{width: '100%'}} value={this.state.selected} onChange={(e)=> this.setState({selected: e.target.value})}>
		  								{Object.keys(this.state.products).map( key => <option key={key} value={key}>{this.state.products[key]}</option>)}
									</select>
								</div>
								
								<div  className="modal-footer"> 
								  	<button type="button" className="btn btn-primary" onClick = {() => {this.onClickHandle()}}>{lang('Copy')}</button>
							        <button type="button" className="btn btn-danger" data-dismiss="modal">{lang('Close')}</button>
						        </div>
							</div>
						</div>
					</div>
		)  
	}
}

export default CopySpectModal
	  
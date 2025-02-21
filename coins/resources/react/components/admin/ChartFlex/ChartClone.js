import React, { Component } from 'react'
class ChartClone extends Component {

	constructor(props) {
		super(props);
		this.id = makeId()
		this.state = {
			config: ''
		}

			
	}


	onClickHandle() {
		if(this.props.onApply){
			this.props.onApply(JSON.parse(this.state.config))
		}
		
	}

	setConfig(config){
		config = JSON.stringify(config, null, 2)
		this.setState({config: config})
	}

	
	modal(cmd = 'show') {
		if (cmd == 'hide') {
			$("#edit_row_modal" + this.id).modal('hide');
		} else {
			$("#edit_row_modal" + this.id).modal();
		}
	}

	setDefault(){
		if(this.props.onSetDefault){
			this.props.onSetDefault(JSON.parse(this.state.config))
		}
	}
	

	render() {

		
		
		return (
			<div className="modal fade" id={"edit_row_modal" + this.id} onClick={() => { addClass($('body')[0], 'modal-open') }}>
				<div className="modal-dialog modal-lg modal-dialog-centered" style={{maxWidth:'90%'}}>
					<div className="modal-content">

						<div className="modal-header">
							<h4 className="modal-title">{this.state.title}</h4>
							<button type="button" className="close" data-dismiss="modal">&times;</button>
						</div>

						<div className="modal-body" style={{ textAlign: 'initial' }}>

							<textarea style={{width:'100%', minHeight:500}} className='input' value={this.state.config} onChange={(e) => this.setState({config: e.target.value})}></textarea>

						</div>

						<div className="modal-footer">
							
							<button type="button" className="btn btn-primary" onClick={() => { this.setDefault(this.state.config) }}>{lang('Set as Default')}</button>
							<button type="button" className="btn btn-info" onClick={() => { copyToClipboard(this.state.config) }}>{lang('Copy')}</button>
							<button type="button" className="btn btn-warning" onClick={() => { this.onClickHandle() }}>{lang('Apply')}</button>
							<button type="button" className="btn btn-danger" data-dismiss="modal">{lang('Close')}</button>
						</div>

					</div>
				</div>
			</div>
		)
	}
}
export default ChartClone

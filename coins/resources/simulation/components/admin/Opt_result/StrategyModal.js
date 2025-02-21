import React, { Component } from 'react'



import Table from '../../table/TableStatic'
import MainTable from '../../table/MainTable'
import Pagination from '../../table/Pagination'
import FuncBar from '../../table/FuncBar'

import FuncEditRow from '../../table/FuncEditRow'
import FuncAdd from '../../table/FuncAdd'
import FuncHideCol from '../../table/FuncHideCol'
import FuncDel from '../../table/FuncDel'
import FuncClear from '../../table/FuncClear'
import FuncRefresh from '../../table/FuncRefresh'
import FuncExport from '../../table/FuncExport'

import Lab_campaigns from '../../../model/admin/Lab_campaigns'

import Input from '../../input/Input'

class StrategyModal extends Component {

	constructor(props) {
		super(props);
		this.id = makeId();

		this.state = {
			data : '',
			 title : ''
		}


	}	



	setValue(data , title='Strategy'){
		var data = JSON.parse(data);
		data = JSON.stringify(data, null, 2);
		this.input.setValue(data);

		this.setState({
			title : title
		});
	}


	modal(cmd = 'show') {
		if (cmd == 'hide') {
			$("#bladeModal" + this.id).modal('hide');
		} else {
			$("#bladeModal" + this.id).modal();
		}
	}


	render() {

		return (
			<>
				<div className="modal fade" id={"bladeModal" + this.id}>
					<div className="modal-dialog modal-lg modal-dialog-centered" style={{ maxWidth: '98%' }}>
						<div className="modal-content">

							<div className="modal-header">
								<h4 className="modal-title">{this.state.title}</h4>
								<button type="button" className="close" data-dismiss="modal">&times;</button>
							</div>

							<div className="modal-body" style={{ textAlign: 'initial' }}>

								<div>
									<Input className='input' ref={c => this.input =c} struct={{
										[INPUT_TYPE]: 'ace',
										[INPUT_NULL]: true,
										// [INPUT_DEFAULT]: this.state.data,
										// [INPUT_ONCHANGE]: (e, obj) => { this.state.NameValue = obj.getValue() }
									}}></Input>
								</div>


							</div>

							<div className="modal-footer">
								<button type="button" className="btn btn-danger" data-dismiss="modal">Close</button>
							</div>

						</div>
					</div>
				</div>

			</>
		)
	}




}
export default StrategyModal
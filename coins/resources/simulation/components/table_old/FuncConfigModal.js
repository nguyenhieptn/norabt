import React, { Component } from 'react'
import FormInput from '../input/FormInput';

class FuncConfigModal extends Component {

	constructor(props, context) {
		
		super(props, context);

		this.id = makeId();
		this.table = this.context;

		this.table.children[this.id] = this;

	}



	modal(cmd = 'show') {
		if (cmd == 'hide') {
			$("#modal" + this.id).modal('hide');
		} else {
			$("#modal" + this.id).modal();
		}
	}

	loadData(data) {
		this.rowData = data;
		var params = data[this.props.column];
		params = JSON.parse(params);
		if (params)
			this.form.setValue(params);
	}

	render() {
		return (
			<div className="modal fade" id={"modal" + this.id}>
				<div className="modal-dialog modal-lg modal-dialog-centered">
					<div className="modal-content">

						<div className="modal-header">
							<h4 className="modal-title">{ }</h4>
							<button type="button" className="close" data-dismiss="modal">&times;</button>
						</div>

						<div className="modal-body" style={{ textAlign: 'initial' }}>
							<FormInput ref={e => this.form = e} struct={this.props.struct}></FormInput>
						</div>

						<div className="modal-footer">
							<button type="button" className="btn btn-danger" data-dismiss="modal">{lang('Close')}</button>
							<button type="button" className="btn btn-primary" onClick={() => {
								if (this.props.onSave) {
									var data = this.form.getValue();
									if (!data) return;
									return this.props.onSave(data)
								} else {
									this.onSave();
								}
							}} >{lang('Save')}</button>
						</div>

					</div>
				</div>
				<style>{`
                                .table.table-bordernone td, .table.table-bordernone th{
                                    border-top: none;
                                }
                            `}</style>
			</div>
		)
	}


	onSave() {
		var data = this.form.getValue();
		if (!data) return;

		const { key, value } = this.table.createKey(this.rowData);

		var data_key = value;
		var data_edit = { [this.props.column]: JSON.stringify(data) };

		this.table.editRow(data_key, data_edit).then(res => {
			if (res) {
				if (this.table.loadOrigin) {
					this.table.loadOrigin();
				} else {
					this.table.filter();
				}
				this.modal('hide');
			}
		})
	}

}

FuncConfigModal.contextType = TableContext;

export default FuncConfigModal


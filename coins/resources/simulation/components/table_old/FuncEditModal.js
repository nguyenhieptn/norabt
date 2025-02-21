import React, { Component } from 'react'
import FormEditor from './FormEditor'

class FuncEditModal extends Component {

	constructor(props, context) {
		super(props, context);
		if(this.props.table){
			this.table = this.props.table;
		}else{
			this.table = this.context;
		}
		this.table.children['EditModal'] = this;
		this.id = makeId();
		this.rowData = {};

		if (!this.props.upload) {
			this.upload = this.table.upload;
		} else {
			this.upload = this.props.upload;
		}

		
	}

	initial() {
		this.struct = {};
		this.permitCol = this.table[STRUCT_TABLE][DATA_PERMIT_COL];

		for (let i in this.table[STRUCT_EDIT]) {
			if (!this.permitCol[i]) continue;
			this.struct[i] = this.table[STRUCT_EDIT][i];
			if (this.permitCol[i] == 'Read') {
				this.struct[i][EDIT_WRITABLE] = false;
			} else {
				this.struct[i][EDIT_WRITABLE] = true;
			}
		}
	}

	onClickHandle() {
		var rowData = this.form.getValue();

		if (rowData == null) return;

		for (let i in rowData) {

			if (this.permitCol[i] == 'Read') {
				delete (rowData[i]);
			}
		}

		
		const {key, value} = this.table.createKey(this.rowData);
		
		var data_key = value;
		var data_edit = rowData;

		this.table.editRow(data_key, data_edit).then(res => {
			if(res){
				if(this.table.loadOrigin){
					this.table.loadOrigin();
				}else{
					this.table.filter();
				}
				this.modal('hide');
			}
		})
	}

	


	modal(cmd = 'show') {
		if (cmd == 'hide') {
			$("#edit_row_modal" + this.id).modal('hide');
		} else {
			$("#edit_row_modal" + this.id).modal();
			this.reload();
		}
	}

	loadData(rowData) {
		this.rowData = rowData;
		this.form.setValue(this.rowData);
		this.reload()
	}

	reload() {
		this.forceUpdate();
	}

	render() {
		this.initial();
		return (
			<div className="modal fade" id={"edit_row_modal" + this.id} onClick={() => { addClass($('body')[0], 'modal-open') }}>
				<div className="modal-dialog modal-lg modal-dialog-centered">
					<div className="modal-content">

						<div className="modal-header">
							<h4 className="modal-title">{lang("Edit")}</h4>
							<button type="button" className="close" data-dismiss="modal">&times;</button>
						</div>

						<div className="modal-body" style={{ textAlign: 'initial' }}>
							<FormEditor ref={form => this.form = form} struct={this.struct}></FormEditor>
						</div>

						<div className="modal-footer">
							<button type="button" className="btn btn-primary" onClick={() => { this.onClickHandle() }}>{lang('Save')}</button>
							<button type="button" className="btn btn-danger" data-dismiss="modal">{lang('Close')}</button>
						</div>

					</div>
				</div>
			</div>
		)
	}
}
FuncEditModal.contextType = TableContext;
export default FuncEditModal

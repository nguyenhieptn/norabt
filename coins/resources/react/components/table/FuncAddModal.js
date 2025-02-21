import { result } from 'lodash';
import React, { Component } from 'react'
import FormEditor from './FormEditor'

class FuncAddModal extends Component {

	constructor(props, context) {
		super(props, context);
		if (this.props.table) {
			this.table = this.props.table;
		} else {
			this.table = this.context;
		}

		this.table.children['AddModal'] = this;
		this.id = this.table[STRUCT_TABLE][DATA_TABLE_ID] + Math.floor(Math.random() * 10000);

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

		this.table.addRow(rowData).then(res => {
			if(res){
				this.modal('hide');
				if(this.table.loadOrigin){
					this.table.loadOrigin();
				}else{
					this.table.filter();
				}
			}
		});

	}

	modal(cmd = 'show') {
		if (cmd == 'hide') {
			$("#add_row_modal" + this.id).modal('hide');
		} else {
			$("#add_row_modal" + this.id).modal();
			this.reload()
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
		var text = get(this.props.text, lang('Add'));
		return (
			<div className="modal fade" id={"add_row_modal" + this.id} onClick={() => { addClass($('body')[0], 'modal-open') }}>
				<div className="modal-dialog modal-lg modal-dialog-centered">
					<div className="modal-content">

						<div className="modal-header">
							<h4 className="modal-title">{get(this.props.title, lang("Add"))}</h4>
							<button type="button" className="close" data-dismiss="modal">&times;</button>
						</div>

						<div className="modal-body">
							<FormEditor ref={form => this.form = form} struct={this.struct}></FormEditor>
						</div>

						<div className="modal-footer">
							<button type="button" className="btn btn-primary" onClick={() => { this.onClickHandle() }}>{get(this.props.button, lang("Add"))}</button>
							<button type="button" className="btn btn-danger" data-dismiss="modal">{lang('Close')}</button>
						</div>
					</div>
				</div>
			</div>
		)
	}
}

FuncAddModal.contextType = TableContext;
export default FuncAddModal

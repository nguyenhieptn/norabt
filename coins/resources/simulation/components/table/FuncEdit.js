import React, { Component } from 'react'
import FormEditor from './FormEditor'

class FuncEdit extends Component {

	constructor(props, context) {
		super(props, context);
		this.table = this.context;
		this.table.children['FuncEdit'] = this;
		this.id = makeId();

	}

	initial() {
		this.struct = {};
		this.permitCol = this.table[STRUCT_TABLE][DATA_PERMIT_COL];
		for (let i in this.permitCol) {
			if (!this.table[STRUCT_EDIT][i]) continue;
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

		if (this.table[STRUCT_TABLE][DATA_EDITOR]) {
			rowData = { ...rowData, ...this.table[STRUCT_TABLE][DATA_EDITOR] }
		}
		this.editRow(rowData)

	}

	editRow(newData) {

		var dataSelect = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];
		var editKey = [];
		for (let i in dataSelect) {
			const { key, value } = this.table.createKey(dataSelect[i]);
			editKey.push(value);
		}

		if (editKey.length == 0) {
			Swal('Error', 'Please select at lest 1 row');
			return;
		}

		this.table.editRows(editKey, newData).then(res => {
			if (res) {
				$("#edit_row_modal" + this.id).modal('hide');
				this.table[STRUCT_TABLE][DATA_SELECT_ROWS] = {}
				if (this.table.loadOrigin) {
					this.table.loadOrigin();
				} else {
					this.table.filter();
				}
			}
		});


	}




	reload() {
		this.forceUpdate();
	}

	render() {
		this.initial();
		var text = get(this.props.text, 'Edit');
		return (
			<div className="table_function">

				<div className="button" title="Edit selected rows" onClick={() => {
					$("#edit_row_modal" + this.id).modal();
					this.form.setState({ select: {} });

				}} style={{ display: 'flex' }}>
					<i className="fa fa-edit"></i>&nbsp;{text}
				</div>

				<div className="modal fade" id={"edit_row_modal" + this.id} onClick={() => { addClass($('body')[0], 'modal-open') }}>
					<div className="modal-dialog modal-lg modal-dialog-centered">
						<div className="modal-content">

							<div className="modal-header">
								<h4 className="modal-title">{"Edit selected rows"}</h4>
								<button type="button" className="close" data-dismiss="modal">&times;</button>
							</div>

							<div className="modal-body">
								<FormEditor ref={form => this.form = form} struct={this.struct} select={true}></FormEditor>
							</div>

							<div className="modal-footer">
								{isset(this.props.extraFunction)? this.props.extraFunction: ''}
								<button type="button" className="btn btn-primary" onClick={() => { this.onClickHandle() }}>Save</button>
								<button type="button" className="btn btn-danger" data-dismiss="modal">Close</button>
							</div>
						</div>
					</div>
				</div>
			</div>
		)
	}
}

FuncEdit.contextType = TableContext;
export default FuncEdit


import React, { Component } from 'react'
import FormEditor from './FormEditor'

class FuncClone extends Component {

	constructor(props, context) {
		super(props, context);
		this.table = this.context;


		this.table.children['FuncClone'] = this;
		// this.id = this.table[STRUCT_TABLE][DATA_TABLE_ID] + Math.floor(Math.random() * 10000);

		// if(!this.props.upload){
		// 	this.upload = this.table.upload;
		// }else{
		// 	this.upload = this.props.upload;
		// }

		// if(!this.props.onSuccess){
		// 	this.onSuccess = ()=>this.table.filter();
		// }else{
		// 	this.onSuccess = this.props.onSuccess;
		// }

	}

	componentWillUnmount() {
		this.table.children['FuncClone'] = false;
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

		this.rowData = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];

	}




	render() {
		this.initial();
		var text = get(this.props.text, lang('Clone'));
		return (
			<div className="table_function">

				<div className="button" title="Clone Row"
					onClick={(e) => {
						if (this.props.onClick) {
							this.props.onClick(e);
							return;
						} else {

							var leng = Object.keys(this.rowData).length;


							if (leng !== 1) {
								showLog('Please select one row');
								return;
							}


							this.table.children['CloneModal'].loadData(Object.values(this.rowData)[0]);
							this.table.children['CloneModal'].modal();
						}

					}}
					style={{ display: 'flex' }}>
					<i className="fa fa-clone"></i>&nbsp;{text}
				</div>

			</div>
		)
	}
}

FuncClone.contextType = TableContext;
export default FuncClone

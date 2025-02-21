import React, { Component } from 'react'
import FormEditor from './FormEditor'

class FuncDel extends Component {

	constructor(props, context) {
		super(props, context);
		this.table = this.context;
		this.id = makeId();

	}

	initial() {
		this.struct = {};
		this.permitCol = this.table[STRUCT_TABLE][DATA_PERMIT_COL];
		for (let i in this.permitCol) {
			if (!this.table[STRUCT_EDIT][i]) continue;
			this.struct[i] = this.table[STRUCT_EDIT][i];
		}
	}

	onClickHandle() {

		makeQuestion('Do you want to delete all selected rows').then(async res => {
			if (res) {
				var dataSelect = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];
				for(let i in dataSelect){
					const {key, value} = this.table.createKey(dataSelect[i]);
					var result = await this.table.delRow(value);
					if (!result) break;
				}
				this.table[STRUCT_TABLE][DATA_SELECT_ROWS] = {};
				if(this.table.loadOrigin){
					this.table.loadOrigin();
				}else{
					this.table.filter();
				}
			}
			
		})

	}

	

	render() {
		this.initial();
		return (
			<div className="table_function">

				<div className="button" title={lang("Delete Row selected")} onClick={() => { this.onClickHandle() }} style={{ display: 'flex' }}>
					<i className="fa fa-trash"></i>&nbsp;{lang('Delete')}
				</div>

			</div>
		)
	}
}

FuncDel.contextType = TableContext;
export default FuncDel

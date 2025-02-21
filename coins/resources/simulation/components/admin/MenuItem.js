import React, { Component } from 'react'
import DragSort from '../common/DragSort'
class MenuItem extends Component {

	constructor(props, context) {
		super(props, context);
		this.table = this.context;
		this.state = {
			expand: true
		}
	}

	render() {

		var children = this.props.data.filter(item => item[MENU_PARENT] == this.props.rowData[MENU_ID]);
		return (<div>

			<DragSort className="MenuItem_item box_flex box_shadow" style={{ flexWrap: 'wrap', margin: '5px 0px' }}
				src_id={this.props.rowData[MENU_ID]}
				src_weight={this.props.rowData[MENU_WEIGHT]}
				onDrag={() => this.table.drag = this}
				changeOrder={(src_id, dest_id) => {
					this.table.sort(src_id, dest_id).then(response => {
						if (!response) return;
						if (!response['result']) {
							error_handle(response);
							return;
						}
						this.props.parent.getChildren();
					})
				}}
			>

				<div className='button' onClick={() => {
					this.setState({
						expand: !this.state.expand
					})
				}}>

					<strong style={{ marginLeft: 10 }}>{this.props.rowData[MENU_TITLE]}</strong>

				</div>

				<div style={{ display: 'flex', margin: 'auto 5px auto auto' }}>

					<div className="button" title="Edit Row" onClick={() => {
						this.table.children['EditModal'].loadData(this.props.rowData);
						this.table.children['EditModal'].modal();
						this.table.children['EditModal'].onSuccess = () => {
							this.props.parent.getChildren();
						}
					}}>
						<i className="fa fa-edit"></i>
					</div>

					<div className="button" title="Delete Row" onClick={() => {
						this.table.delRow({ [MENU_ID]: this.props.rowData[MENU_ID] })
					}}>
						<i className="fa fa-trash"></i>
					</div>

					<div className="button" title="Add Row" onClick={() => {
						this.table.children['AddModal'].modal();
						this.table.children['AddModal'].onClickHandle = () => {
							var form = this.table.children['AddModal'].form;
							var rowData = form.getValue();
							rowData[MENU_PARENT] = this.props.rowData[MENU_ID];
							this.table.addRow(rowData).then(response => {
								if (response['result']) {
									this.props.parent.getChildren();
									this.table.children['AddModal'].modal('hide');
								} else {
									Swal(response['message'], response['data'], 'error');
								}
							})
						}
					}}>
						<i className="fa fa-plus-square"></i>
					</div>

				</div>


			</DragSort>

			<div style={{ display: (this.state.expand ? 'block' : 'none'), paddingLeft: 15 }}>

				{children.map((item, key) => {
					return <MenuItem data={this.props.data} rowData={item} key={item[MENU_ID]} parent={this.props.parent} />
				})}

			</div>

		</div>
		)
	}
}

MenuItem.contextType = TableContext;
export default MenuItem

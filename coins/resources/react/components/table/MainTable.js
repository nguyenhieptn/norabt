import React, { Component } from 'react'
import InputCheck from '../input/InputCheck'
import FuncEditModal from './FuncEditModal'
import FuncAddModal from './FuncAddModal'
import FuncCloneModal from './FuncCloneModal'
import FilterRow from './FilterRow'

class MainTable extends Component {


	constructor(props, context) {
		super(props, context)
		this.table = this.context;
		this.table.children['MainTable'] = this;

		this.state = {
			[DATA_SORT]: this.table[STRUCT_TABLE][DATA_SORT],
		}
		this.selectRow = {};
		this.headRow = {};
		this.id = this.table[STRUCT_TABLE][DATA_TABLE_ID];

	}

	initial() {
		this.columns = this.table[STRUCT_COLUMNS];
		this.cells = this.table[STRUCT_CELLS];
		this.hiddenCol = this.table[STRUCT_TABLE][DATA_HIDDEN_COL];
		this.permitCol = this.table[STRUCT_TABLE][DATA_PERMIT_COL];
		this.tableData = this.table[STRUCT_TABLE][DATA_TABLE];


		if (this.table[STRUCT_TABLE][TABLE_DECORATOR_DATA]) {
			this.tableData = this.table[STRUCT_TABLE][TABLE_DECORATOR_DATA](this.tableData);
		}



		this.func_select();
		this.func_seting();
		this.func_index();

	}

	//============================================
	func_index() {
		if (!this.table[STRUCT_TABLE][FLAG_ROW_INDEX]) return;

		var indexCol = {
			index: {
				[COL_NAME]: 'No.',
				[COL_SORT]: false,
				[COL_ISFUNC]: true,
				[COL_STYLE]: { textAlign: 'center' },
				...this.columns.index
			}
		}

		this.columns = { ...indexCol, ...this.columns }

		this.permitCol['index'] = true;

		for (let rowID in this.tableData) {
			var index = ((Number(this.table[STRUCT_TABLE][PAGE_ACTIVE]) - 1) * Number(this.table[STRUCT_TABLE][PAGE_QUANTITY]) + Number(rowID) + 1);
			this.tableData[rowID]['index'] = index;
		}
	}


	func_seting() {
		if (!this.table[STRUCT_TABLE][FLAG_SETTING_ROWS]) return;

		var setingColumn = {

			setting: {
				[COL_NAME]: lang('Setup'),
				[COL_SORT]: false,
				[COL_ISFUNC]: true,
				[COL_STYLE]: { textAlign: 'center' },
				...this.columns.setting
			}
		}

		this.permitCol['setting'] = true;
		this.columns = { ...setingColumn, ...this.columns }

		if (this.table[STRUCT_ROWS][ROW_FUNCS]) {
			for (let rowID in this.tableData) {
				this.tableData[rowID]['setting'] = this.table[STRUCT_ROWS][ROW_FUNCS](this.tableData[rowID])
			}
		}
	}

	//=============================================

	onSelect(checked, rowID) {
		var rowData = this.tableData[rowID];

		var { key, value } = this.table.createKey(rowData);

		if (checked) {
			this.table[STRUCT_TABLE][DATA_SELECT_ROWS][key] = rowData;
		} else {
			delete this.table[STRUCT_TABLE][DATA_SELECT_ROWS][key];
		}

		if (this.table.props.onSelect) this.table.props.onSelect(rowData);

	}

	onMasterSelect(event) {

		for (let i in this.selectRow) {
			if (isset(this.selectRow[i])) {
				this.selectRow[i].setValue(event.target.checked);
				this.onSelect(event.target.checked, this.selectRow[i].value);
			} else {
				delete (this.selectRow[i]);
			}

		}

	}

	loadSelect() {
		if (!this.table[STRUCT_TABLE][FLAG_SELECT_ROWS]) return;
		for (let rowID in this.tableData) {
			const { key, value } = this.table.createKey(this.tableData[rowID]);
			if (this.selectRow[key]) {
				this.selectRow[key].setValue(isset(this.table[STRUCT_TABLE][DATA_SELECT_ROWS][key]));
			}
		}
	}

	func_select() {
		if (!this.table[STRUCT_TABLE][FLAG_SELECT_ROWS]) return;

		var selectColumn = {
			select: {
				[COL_SORT]: false,
				[COL_ISFUNC]: true,
				[COL_STYLE]: { textAlign: 'center' },
				...this.columns.select,
				[COL_NAME]: <input type="checkbox" onChange={(event) => this.onMasterSelect(event)} />,
			}
		}

		this.permitCol['select'] = true;
		this.columns = { ...selectColumn, ...this.columns }

		for (let rowID in this.tableData) {
			const { key, value } = this.table.createKey(this.tableData[rowID]);
			this.tableData[rowID]['select'] = <InputCheck
				value={rowID}
				ref={input => this.selectRow[key] = input}
				defaultChecked={isset(this.table[STRUCT_TABLE][DATA_SELECT_ROWS][key])}
				type="checkbox"
				onChange={(checked) => this.onSelect(checked, rowID)}>
			</InputCheck>;
		}

	}
	//=============================================


	sortHandle(i) {
		var currentSort = this.table[STRUCT_TABLE][DATA_SORT][i];

		if (!this.table[STRUCT_TABLE][FLAG_MULTI_SORT]) {
			this.table[STRUCT_TABLE][DATA_SORT] = {};
		}

		if (currentSort == null) this.table[STRUCT_TABLE][DATA_SORT][i] = 'desc';
		else if (currentSort == 'desc') this.table[STRUCT_TABLE][DATA_SORT][i] = 'asc';
		else if (currentSort == 'asc') this.table[STRUCT_TABLE][DATA_SORT][i] = 'desc';

		this.table.filter();
	}


	drawHeader() {
		if (isset(this.table[STRUCT_TABLE][FLAG_HEAD_ROW]) && !this.table[STRUCT_TABLE][FLAG_HEAD_ROW])
			return (<tr></tr>);
		var tablehead = [];

		for (let i in this.columns) {
			if (!this.permitCol[i]) continue;
			if (get(this.hiddenCol[i], false)) {
				continue;
			}

			var colStyle = get(this.columns[i][COL_STYLE], {});
			var des = this.columns[i][COL_NAME];
			if (this.columns[i][COL_DES]) des = this.columns[i][COL_DES]

			if (this.columns[i][COL_SORT]) {
				var sortClass = 'none';
				if (this.table[STRUCT_TABLE][DATA_SORT][i] != null) {
					sortClass = this.table[STRUCT_TABLE][DATA_SORT][i];
				}

				let sum;
				
				if (this.columns[i][COL_SUM] ) {
					
					sum = 0;
					
					if(typeof(this.columns[i][COL_SUM]) === "function"){
						sum = this.columns[i][COL_SUM](this.tableData);
					}else{
						var colName = i;
						if (this.tableData) {
							this.tableData.map(row => {
								sum += Number(row[colName]);
							})

							sum= Math.round(sum*1000)/1000;
							sum = formatNumber(sum)

						}
					}

				} 
				tablehead.push(
					<th  title={des} ref={th => this.headRow[i] = th} style={colStyle} key={i}>
						<div  className="column_sort" vector={sortClass} onClick={() => this.sortHandle(i)}>
							{this.columns[i][COL_NAME]}
						</div>
						{
							isset(sum) && <div style={{color : 'red' , fontSize : '12px' }}>{[sum]}</div>
						}
					</th>
				);

			} else {

				let sum;

				if (this.columns[i][COL_SUM]) {
					
					sum = 0;
					
					if(typeof(this.columns[i][COL_SUM]) === "function"){
						sum = this.columns[i][COL_SUM](this.tableData);
					}else{
						var colName = i;
						if (this.tableData) {
							this.tableData.map(row => {
								sum += row[colName];
							})
							sum= Math.round(sum*1000)/1000;
							sum = formatNumber(sum)

						}
					}


				} 

				tablehead.push(
					<th title={des} ref={th => this.headRow[i] = th} style={colStyle} key={i}>
						<div >
							{this.columns[i][COL_NAME]}
						</div>
						{
							isset(sum) && <div style={{color : 'red' , fontSize : '12px' }}>{[sum]}</div>
						}
					</th>
				);

			}
		}

		return <tr>{tablehead}</tr>;
	}


	drawBody() {

		var tableHtml = [];

		for (let rowID in this.tableData) {

			var rowStyle = {}
			if (this.table[STRUCT_ROWS][ROW_STYLE] != null) {
				rowStyle = this.table[STRUCT_ROWS][ROW_STYLE](rowID, this.tableData);
			}

			var rowHtml = [];
			var rowData = this.tableData[rowID];

			if (this.table[STRUCT_ROWS][ROW_DECORATOR]) {
				rowData = this.table[STRUCT_ROWS][ROW_DECORATOR](rowID, this.tableData);
			}

			for (let colID in this.columns) {

				if (!this.permitCol[colID]) continue;

				if (get(this.hiddenCol[colID], false)) {
					continue;
				}

				var tdData = rowData[colID];
				var cellStyle = {};
				if (isset(this.cells[CELL_STYLE])) {
					cellStyle = this.cells[CELL_STYLE](colID, rowID, this.tableData);
				}

				var colStyle = get(this.columns[colID][COL_STYLE], {});

				if (isset(this.columns[colID][COL_DECORATOR_IN])) {

					if (this.columns[colID][COL_DECORATOR_IN].prototype.constructor.length == 1) {
						tdData = this.columns[colID][COL_DECORATOR_IN](tdData);
					} else {
						tdData = this.columns[colID][COL_DECORATOR_IN](colID, rowID, this.tableData);
					}

				}

				if (isset(this.columns[colID][COL_OPTION])) {
					if (isset(this.columns[colID][COL_OPTION][tdData])) {
						tdData = this.columns[colID][COL_OPTION][tdData];
					}
				}

				if (tdData == null || tdData == "Invalid date") { tdData = '' }

				rowHtml.push(<td key={colID} style={{ ...cellStyle, ...colStyle }}>{tdData}</td>);
			}

			tableHtml.push(<tr onClick={e => {
				const row = e.currentTarget;
				if ($(row).hasClass('focused')) return;

				const id = 'id' + makeId();
				const removeFocus = (e) => {
					var checkrow = e.target.closest('.' + id);
					if (checkrow == null) {
						$(row).removeClass('focused');
						$(row).removeClass(id)
						document.removeEventListener('click', removeFocus)
					}
				}

				$(row).addClass('focused');
				$(row).addClass(id);
				document.addEventListener('click', removeFocus);



			}} key={rowID} style={rowStyle}>{rowHtml}</tr>);

		}

		return tableHtml;

	}

	drawFooter() {
		var visibleColumns = [];
		for (let colID in this.columns) {

			if (!this.permitCol[colID]) continue;

			if (get(this.hiddenCol[colID], false)) {
				continue;
			}

			visibleColumns.push(colID);
		}
		var footerRow = this.table[STRUCT_ROWS][ROW_FOOTER](get(this.tableData, []), visibleColumns);
		return footerRow;
	}

	drawBanner() {
		var visibleColumns = [];
		for (let colID in this.columns) {

			if (!this.permitCol[colID]) continue;

			if (get(this.hiddenCol[colID], false)) {
				continue;
			}

			visibleColumns.push(colID);
		}
		var bannerRow = this.table[STRUCT_ROWS][ROW_BANNER](get(this.tableData, []), visibleColumns);
		return bannerRow;
	}

	reload() {
		this.forceUpdate();
		this.loadSelect();
	}

	render() {
		this.initial();

		return (
			<div>
				<div style={{ overflow: 'auto', minHeight: get(this.props.minHeight, 400) }}>
					<div style={{ width: 'max-content', minWidth: '100%' }}>
						<table id={this.id} className={'main_table ' + this.props.className} style={this.props.style}>
							<thead style={{ opacity: this.opacity }}>
								{this.table[STRUCT_ROWS][ROW_BANNER] && this.drawBanner()}
								{this.drawHeader()}
								{this.table[STRUCT_TABLE][FLAG_FILTER] && <FilterRow></FilterRow>}
							</thead>
							<tbody>{this.drawBody()}</tbody>
							{this.table[STRUCT_ROWS][ROW_FOOTER] && <tfoot>{this.drawFooter()}</tfoot>}
						</table>

						{(!this.tableData || Object.keys(this.tableData).length == 0) ? <div className="alert alert-warning" role="alert">{lang('No data')}</div> : ''}
					</div>

				</div>

				<FuncEditModal />
				<FuncAddModal />
				<FuncCloneModal/>

			</div>
		);
	}
}

MainTable.contextType = TableContext;

export default MainTable

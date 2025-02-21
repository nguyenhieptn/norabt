import './constants';
import React, { Component } from 'react';
import Script from '../common/Script'
import Load from '../common/Load'
import(/* webpackMode: "eager" */ './responsive/table.scss')

class TableStatic extends Component { 

	constructor(props) {
		super(props);

		this[STRUCT_FILTERS] = {};
		this[STRUCT_COLUMNS] = {};
		this[STRUCT_CELLS] = {};
		this[STRUCT_ROWS] = {};
		this[STRUCT_TABLE] = [];
		this[STRUCT_EDIT] = {};

		this[STRUCT_TABLE] = {
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this[STRUCT_EDIT],
			[DATA_SELECT_ROWS]: {},
			[DATA_FILTERS]: {},
			[DATA_SPECIAL]: {},
			[DATA_KEY]: ['table_key'],
			[FLAG_FILTER_LOGIC]: 'and',
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_ROW_INDEX]: true,
			[PAGE_ACTIVE]: 1,
			[PAGE_TOTAL]: 0,
			[PAGE_QUANTITY]: 25,
			[FLAG_FILTER]: true,
		};


		//Allow custom update function

		if(!this.props.filter){
	    	this.filter = this.filter.bind(this);
	    }else{
	    	this.filter = this.props.filter;
	    }
	    
	    if(!this.props.delRow){
	    	this.delRow = this.delRow.bind(this);
	    }else{
	    	this.delRow = this.props.delRow;
	    }
	    
	    if(!this.props.addRow){
	    	this.addRow = this.addRow.bind(this);
	    }else{
	    	this.addRow = this.props.addRow;
	    }
	    
	    if(!this.props.editRow){
	    	this.editRows = this.editRows.bind(this);
	    }else{
	    	this.editRows = this.props.editRows;
	    }

		if(!this.props.delRows){
	    	this.delRows = this.delRows.bind(this);
	    }else{
	    	this.delRows = this.props.delRows;
	    }
	    
	    if(!this.props.addRows){
	    	this.addRows = this.addRows.bind(this);
	    }else{
	    	this.addRows = this.props.addRows;
	    }
	    
	    if(!this.props.editRows){
	    	this.editRows = this.editRows.bind(this);
	    }else{
	    	this.editRows = this.props.editRows;
	    }

		if (!this.props.loadOrigin) {
			this.loadOrigin = this.loadOrigin.bind(this);
		} else {
			this.loadOrigin = this.props.loadOrigin;
		}

		this.table = get(this.props.table, {});

		// inital hidden cols status
		this.defaultHidenCol = { ...this.table[STRUCT_TABLE][DATA_HIDDEN_COL] };
		this.loadHidenCol();
		this.initial();
		this.children = {};
		this.mapping = {};
		
		if(this.props.model){
	    	this.model = this.props.model;
	    }else{
	    	this.model = this.table[STRUCT_TABLE].model;
	    }

		this.origin = [];


	}


	setOrigin(tableData) {
		this.origin = tableData.slice(0);
		this.indexOrigin();
		this.filter();
	}

	getOrigin(all = false) {
		var result = [];
		for (let i in this.origin) {
			result[i] = { ...this.origin[i] };
			if (!all) delete (result[i]['table_key']);
		}
		return result;
	}

	indexOrigin() {
		for (let i in this.origin) {
			this.origin[i]['table_key'] = i;
		}
	}


	//==========common function=========================

	createKey(rowData) {
		var key = '';
		var value = {};
		for (let i in this[STRUCT_TABLE][DATA_KEY]) {
			key += rowData[this[STRUCT_TABLE][DATA_KEY][i]];
			if (!isset(rowData[this[STRUCT_TABLE][DATA_KEY][i]])) return false;
			value[this[STRUCT_TABLE][DATA_KEY][i]] = rowData[this[STRUCT_TABLE][DATA_KEY][i]];
		}
		return { key, value };
	}


	//==================================================

	loadHidenCol() {
		this.hiddenCol = JSON.parse(
			localStorage.getItem(this.table[STRUCT_TABLE][DATA_TABLE_ID] + DATA_HIDDEN_COL));
		if (this.hiddenCol != null) {
			this.table[STRUCT_TABLE][DATA_HIDDEN_COL] = this.hiddenCol;
		} else {
			this[STRUCT_TABLE][DATA_HIDDEN_COL] = { ...this.defaultHidenCol };
		}

	}

	initial() {

		for (let i in this.table) {
			this[i] = { ...this[i], ...this.table[i] };
		}

	}

	setFilter(filter) {
		this[STRUCT_TABLE][DATA_FILTERS] = filter;
		this[STRUCT_TABLE][FLAG_FILTER_CHANGE] = true;
		this.filter();
	}
	//========================================
	filter() {

		var filterKey = {};
		var filterData = [];
		
		for (let i in this[STRUCT_TABLE][DATA_FILTERS]){
			var value = this[STRUCT_TABLE][DATA_FILTERS][i]
			var itemKey = {};
			for(let j in value['data']){
				if(value['data'][j] != ''){ 
					itemKey[j] = value['data'][j];
				}
			}
			if(Object.keys(itemKey).length > 0){
				filterKey[i] = {
						'logic' : value['logic'],
						'data' : itemKey
				};
			}
		}


		if (Object.keys(filterKey).length == 0) {
			filterData = this.getOrigin(true);
		} else {

			filterData = this.getOrigin(true).filter((item) => {
				var resultTotal = [];
				for (let i in filterKey) {



					if (filterKey[i]['logic'] == 'and') {
						var result = true;
						for (let j in filterKey[i]['data']) {
							if (!this.checkData(item[i], j, filterKey[i]['data'][j])) {
								result = false;
								break;
							}
						}

					} else {
						var result = false;
						for (let j in filterKey[i]['data']) {
							if (this.checkData(item[i], j, filterKey[i]['data'][j])) {
								result = true;
								break;
							}
						}
					}

					if (this[STRUCT_TABLE][FLAG_FILTER_LOGIC] == 'and') {
						if (!result) return false;
					} else {
						if (result) return true;
					}

				}

				if (this[STRUCT_TABLE][FLAG_FILTER_LOGIC] == 'and') {
					return true;
				} else {
					return false;
				}


			});

		}

		if (Object.keys(this[STRUCT_TABLE][DATA_SORT]).length > 0) {
			filterData = filterData.sort((a, b) => {
				var result = 0;
				var sortIndex = 0;
				for (let i in this[STRUCT_TABLE][DATA_SORT]) {
					if (a[i] == b[i]) {
						continue;
					} else {
						if (Number(a[i]) && Number(b[i])) {
							result = Number(a[i]) - Number(b[i]);
						} else {
							if (a[i] > b[i]) {
								result = 1;
							} else {
								result = -1;
							}
						}
						sortIndex = i;
						break;
					}
				}
				if (this[STRUCT_TABLE][DATA_SORT][sortIndex] == 'asc') {
					return result;
				} else {
					return -result;
				}

			})
		}


		this[STRUCT_TABLE][PAGE_TOTAL] = filterData.length;
		var startIndex = (this[STRUCT_TABLE][PAGE_ACTIVE] - 1) * this[STRUCT_TABLE][PAGE_QUANTITY];
		this[STRUCT_TABLE][DATA_TABLE] = filterData.splice(startIndex, this[STRUCT_TABLE][PAGE_QUANTITY]);
		if (this.successFilter) this.successFilter({ 'result': true });
		this.reload();
	}


	checkData(data, logic, value) {
		if (logic == '=') return data == value;
		if (logic == '>') return data > value;
		if (logic == '>=') return data >= value;
		if (logic == '<') return data < value;
		if (logic == '<=') return data <= value;
		if (logic == 'contain') return data.toLocaleLowerCase().includes(value.toLocaleLowerCase());
	}

	clearFilter() {
		this[STRUCT_TABLE][DATA_FILTERS] = {};
		this[STRUCT_TABLE][FLAG_FILTER_CHANGE] = true;
		this.filter();
	}

	//===========================================================

	addRow(rowData, loading = true) {

		var rowDatas=[rowData];
		this.setOrigin(Object.values(rowDatas).concat(this.origin));
		return Promise.resolve({ 'result': true });

	}

	addRows(rowDatas, loading = true) {

		var rowDatas=rowDatas;
		this.setOrigin(Object.values(rowDatas).concat(this.origin));
		return Promise.resolve({ 'result': true });

	}

	editRow(editKey, editData, loading = true) {

		var id = this[STRUCT_TABLE][DATA_KEY][0];
		var editDatas = {
			[DATA_KEY] : [editKey],
			[DATA_EDITOR]: editData,
		}
		
		var matchRow = [];
		for (let i in this.origin) {
			if (this.checkRow(this.origin[i], editDatas[DATA_KEY])) {
				matchRow.push(i);
			}
		}

		for (let i in matchRow) {
			for (let j in editDatas[DATA_EDITOR]) {
				this.origin[matchRow[i]][j] = editDatas[DATA_EDITOR][j];
			}
		}
		
		
		return Promise.resolve({ result: true });

	}

	editRows(editKeys, editData, loading = true) {

		var id = this[STRUCT_TABLE][DATA_KEY][0];
		var editDatas = {
			[DATA_KEY] : editKeys,
			[DATA_EDITOR]: editData,
		}
		
		var matchRow = [];
		for (let i in this.origin) {
			if (this.checkRow(this.origin[i], editDatas[DATA_KEY])) {
				matchRow.push(i);
			}
		}

		for (let i in matchRow) {
			for (let j in editDatas[DATA_EDITOR]) {
				this.origin[matchRow[i]][j] = editDatas[DATA_EDITOR][j];
			}
		}
		
		
		return Promise.resolve({ result: true });

	}

	checkRow(row, conditions) {
		var resultTotal = false;
		for (let i in conditions) {
			var resultItem = true;
			for (let j in conditions[i]) {
				if (row[j] != conditions[i][j]) {
					resultItem = false;
					break;
				}
			}

			if (resultItem) {
				resultTotal = true;
				break;
			}
		}
		return resultTotal;
	}

	
	delRow(delKey, alert = false) {
		var delKeys = [delKey];
		if (alert) {
			return this.deleteAlert().then(result => {
				if (result) {
					return this.deleteQuery(delKeys, true, special)
				} else {
					return Promise.reject();
				}
			})
		}
		else {
			return this.deleteQuery(delKeys, false, special)
		}
	}

	delRows(delkeys, alert = false) {
		
		if (delKeys.length == 0) {
			showLog('Select rows you want to delete', 'error');
			return Promise.reject();
		}

		if (alert) {
			return this.deleteAlert().then(result => {
				if (result) {
					return this.deleteQuery(delKeys, true, special)
				} else {
					return Promise.reject();
				}
			})
		}
		else {
			return this.deleteQuery(delKeys, false, special)
		}
	}

	deleteAlert() {
		return Swal({
			title: 'Are you sure?',
			text: "You won't be able to revert this!",
			type: 'warning',
			showCancelButton: true,
			confirmButtonColor: '#3085d6',
			cancelButtonColor: '#d33',
			confirmButtonText: 'Yes, delete it!'
		}).then((result) => {
			return result.value;
		})
	}

	deleteQuery(delKeys, loading = true) {
		this.setOrigin(this.origin.filter((item) => {
			if (!this.checkRow(item, delKeys)) {
				return true;
			}
			return false;
		}));

		this[STRUCT_TABLE][DATA_SELECT_ROWS] = {};
		if (this.successDel) this.successDel({ 'result': true });

		return Promise.resolve({ result: true });
	}

	//================================

	readRow(dataKeys, loading = true) {
		var result = this.origin.filter((item) => {
			if (!this.checkRow(item, delKeys)) {
				return true;
			}
			return false;
		});

		return Promise.resolve({ result: true, message: 'Success', data: result });
	}

	reload() {
		for (let i in this.children) {
			if (this.children[i]) {
				if (this.children[i].reload) {
					this.children[i].reload();
				} else {
					this.children[i].forceUpdate();
				}
			}
		}
	}

	map(loading=true){
		this.model.map(loading).then((res)=>{
			if(res){
				if(res['result']){
					this.setMapping(res['data']);
				}
			}	
		})
	}

	setMapping(response) {

		for (let i in response) {
			this.mapping[i] = response[i];

			if (isset(this[STRUCT_COLUMNS][i])) {
				this[STRUCT_COLUMNS][i][COL_OPTION] = response[i];
			}

			if (isset(this[STRUCT_EDIT][i])) {
				if (this[STRUCT_EDIT][i][EDIT_TYPE] == 'select') {
					this[STRUCT_EDIT][i][EDIT_OPTION] = { '': '', ...response[i] };
				} else {
					this[STRUCT_EDIT][i][EDIT_OPTION] = response[i];
				}
			}

			if (isset(this[STRUCT_FILTERS][i])) {
				if (this[STRUCT_FILTERS][i][FILTER_TYPE] == 'select' || this[STRUCT_FILTERS][i][FILTER_TYPE] == 'check') {
					this[STRUCT_FILTERS][i][FILTER_OPTION] = { '': lang('All'), ...response[i] };
				} else {
					this[STRUCT_FILTERS][i][FILTER_OPTION] = response[i];
				}
			}
		}

		this.reload();
	}

	loadOrigin(dataKeys, loading = true) {
		if (loading) App.loading(true, 'Loading...');
		this.model.readRow(dataKeys).then((res)=>{
			if(res){
				if(res['result']){
					response = resizeBy['data'];
					this.setOrigin(response['data']);
					this.filter();
				}
			}	
		})
		
	}

	componentDidMount() {

		if (this.props.autoload) {
			this.map();
			this.filter();
			this.loadOrigin();
		}

	}

	render() {

		return (
			<>

				<TableContext.Provider value={this}>
					<div className="table" style={this.props.style}>
						{this.props.children}
					</div>
				</TableContext.Provider>

			</>
		);
	}
}


if (!global.TableContext) global.TableContext = React.createContext();
export default TableStatic

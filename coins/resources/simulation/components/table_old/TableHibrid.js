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

		if (!this.props.upload) {
			this.upload = this.uploadData.bind(this);
		} else {
			this.upload = this.props.upload;
		}

		if (!this.props.filter) {
			this.filter = this.filter.bind(this);
		} else {
			this.filter = this.props.filter;
		}

		if (!this.props.delRow) {
			this.delRow = this.delRow.bind(this);
		} else {
			this.delRow = this.props.delRow;
		}

		if (!this.props.addRow) {
			this.addRow = this.addRow.bind(this);
		} else {
			this.addRow = this.props.addRow;
		}

		if (!this.props.editRow) {
			this.editRow = this.editRow.bind(this);
		} else {
			this.editRow = this.props.editRow;
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

	
	addRow(rowData, loading=true){
		
		return this.model.add(rowData, loading, this[STRUCT_TABLE][DATA_SPECIAL]).then((res)=>{
			if(res){
				if(res['result']){
					this[STRUCT_TABLE][FLAG_FILTER_CHANGE] = true;
					return res;
				}else{
					error_handle(res);
				}
				
			}
			
		})
	}
	
	editRow(editKey, editData, loading=true){
		return this.model.edit(editKey, editData, loading, this[STRUCT_TABLE][DATA_SPECIAL]).then((res)=>{
			if(res){
				if(res['result']){
					this[STRUCT_TABLE][FLAG_FILTER_CHANGE] = true;
					return res;
				}else{
					error_handle(res);
				}
			}	
		})
	}
	
	delRow(delKey, alert = true){
		
		return this.model.delete(delKey, alert).then((res)=>{
			if(res){
				if(res['result']){
					this[STRUCT_TABLE][FLAG_FILTER_CHANGE] = true;
					return res;
				}else{
					error_handle(res);
				}
			}	
		})
		
	}

	addRows(rowDatas, loading=true){
		return this.model.adds(rowDatas, loading, this[STRUCT_TABLE][DATA_SPECIAL]).then((res)=>{
			if(res){
				if(res['result']){
					this[STRUCT_TABLE][FLAG_FILTER_CHANGE] = true;
					return res;
				}else{
					error_handle(res);
				}
			}
			
		})
	}
	
	editRows(editKeys, editData, loading=true){
		return this.model.edits(editKeys, editData, loading, this[STRUCT_TABLE][DATA_SPECIAL]).then((res)=>{
			if(res){
				if(res['result']){
					this[STRUCT_TABLE][FLAG_FILTER_CHANGE] = true;
					return res;
				}else{
					error_handle(res);
				}
			}	
		})
	}
	
	delRows(delKeys, alert = true){
		
		return this.model.deletes(delKeys, alert, this[STRUCT_TABLE][DATA_SPECIAL]).then((res)=>{
			if(res){
				if(res['result']){
					this[STRUCT_TABLE][FLAG_FILTER_CHANGE] = true;
					return res;
				}else{
					error_handle(res);
				}
			}	
		})
		
	}
	
	readRow(dataKeys, loading=true){
		return this.model.read(dataKeys, loading).then((res)=>{
			return res;
		})
	}

	sort(src_id, dest_id, loading=true, special={}){
		return this.model.sort(src_id, dest_id, loading).then((res)=>{
			return res;
		})
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

	map() {

		if (this[STRUCT_TABLE][LINK_MAPPING]) {
			return axios.request({
				url: this[STRUCT_TABLE][LINK_MAPPING],
				method: 'post',
				data: {
					...this[STRUCT_TABLE][DATA_SPECIAL],
				}
			})
				.then(response => {
					response = response['data'];
					if (response['result']) {
						this.setMapping(response['data']);
					}

					return response;
				})
				.catch((error)=> {
					console.log(error);
				})
		}
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

	loadOrigin(dataKeys, loading = true, special = {}) {
		if (loading) App.loading(true, 'Loading...');
		return axios.request({
			url: this[STRUCT_TABLE][LINK_READ],
			method: 'get',
			data: {
				data: dataKeys,
				...this[STRUCT_TABLE][DATA_SPECIAL],
				...special
			}
		})

			.then(response => {
				App.loading(false, 'Loading...');
				response = response['data'];
				this.setOrigin(response);
				this.filter();
				if (this.props.onLoad) this.props.onLoad(response);
				return response;
			})

			.catch((error)=> {
				console.log(error);
				App.loading(true, 'Loading...');
				error_handle(error)
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

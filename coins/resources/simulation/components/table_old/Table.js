import './constants';
import React, { Component } from 'react';
import Script from '../common/Script'
import Load from '../common/Load'
import (/* webpackMode: "eager" */ './responsive/table.scss')

class Table extends Component {
	
	constructor(props) {
	    super(props);

		this.test = [];
	    
	    this[STRUCT_FILTERS] = {}; 
	    this[STRUCT_COLUMNS] = {}; 
	    this[STRUCT_CELLS] = {}; 
	    this[STRUCT_ROWS] = {}; 
	    this[STRUCT_TABLE] = []; 
	    this[STRUCT_EDIT] = {}; 
	    
	    this[STRUCT_TABLE]= {
            [DATA_HIDDEN_COL] : {},
            [DATA_PERMIT_COL] : this[STRUCT_EDIT],
            [DATA_SELECT_ROWS]: {},
            [DATA_FILTERS]: {},
            [DATA_SPECIAL]: {},
            [FLAG_FILTER_LOGIC] : 'and',
            [FLAG_FILTER_CHANGE] : true,
            [FLAG_MULTI_SORT] : false,
            [FLAG_RESIZABLE] : true,
            [FLAG_SELECT_ROWS] : true,
            [FLAG_SETTING_ROWS] : true,
            [FLAG_EXPAND_ROWS] : false,
            [FLAG_ROW_INDEX] : true,
            [PAGE_ACTIVE] : 1,
            [PAGE_TOTAL] : 0,
            [PAGE_QUANTITY] : 25,
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

		
	                                                                                                                                                                                                                                                                                     
	    this.table = get(this.props.table, {});
	    
	    // inital hidden cols status
	    this.defaultHidenCol = {...this.table[STRUCT_TABLE][DATA_HIDDEN_COL]};
	    this.loadHidenCol();
	    this.initial();
	    this.children = {};
	    this.mapping = {};

	    if(this.props.model){
	    	this.model = this.props.model;
	    }else{
	    	this.model = this.table[STRUCT_TABLE].model;
	    }

	}
	
	//==========common function=========================
	
	createKey(rowData){
		var key = '';
		var value = {};
		for(let i in this[STRUCT_TABLE][DATA_KEY]){
			key += rowData[this[STRUCT_TABLE][DATA_KEY][i]];
			if(!isset(rowData[this[STRUCT_TABLE][DATA_KEY][i]])) return false;
			value[this[STRUCT_TABLE][DATA_KEY][i]] = rowData[this[STRUCT_TABLE][DATA_KEY][i]];
		}
		return {key, value};
	}
	
	
	//==================================================
	
	loadHidenCol(){
		this.hiddenCol = JSON.parse(
		    		localStorage.getItem(this.table[STRUCT_TABLE][DATA_TABLE_ID]+DATA_HIDDEN_COL));
	    if(this.hiddenCol != null) {
	    	this.table[STRUCT_TABLE][DATA_HIDDEN_COL] = this.hiddenCol;
	    }else{
	    	this[STRUCT_TABLE][DATA_HIDDEN_COL] = {...this.defaultHidenCol};
	    }
	    
	}
	
	initial(){
		
		for(let i in this.table){
			this[i] = {...this[i], ...this.table[i]};
		}
		
	}
	
	setOrigin(){
		
	}
	
	setFilter(filter){
		this[STRUCT_TABLE][DATA_FILTERS] = filter;
		this[STRUCT_TABLE][FLAG_FILTER_CHANGE] = true;
		this.filter();
	}
	//========================================
	filter(loading=true){
		
		var filters = {};
		
		for (let i in this[STRUCT_TABLE][DATA_FILTERS]){
			var value = this[STRUCT_TABLE][DATA_FILTERS][i]
			var itemKey = {};
			for(let j in value['data']){
				if(value['data'][j] != ''){ 
					itemKey[j] = value['data'][j];
				}
			}
			if(Object.keys(itemKey).length > 0){
				filters[i] = {
						'logic' : value['logic'],
						'data' : itemKey
				};
			}
		}

		
		var filterData ={};
		
		filterData[PAGE_ACTIVE] = this[STRUCT_TABLE][PAGE_ACTIVE];
	    filterData[PAGE_QUANTITY] = this[STRUCT_TABLE][PAGE_QUANTITY];
	    filterData[PAGE_TOTAL] = this[STRUCT_TABLE][PAGE_TOTAL];
	    filterData[FLAG_FILTER_CHANGE] = this[STRUCT_TABLE][FLAG_FILTER_CHANGE];
	    filterData[FLAG_FILTER_LOGIC] = this[STRUCT_TABLE][FLAG_FILTER_LOGIC];
	    filterData[DATA_SORT] = this[STRUCT_TABLE][DATA_SORT];
	    filterData[DATA_FILTERS] = filters;
	    
	    this.model.filter(filterData, loading, this[STRUCT_TABLE][DATA_SPECIAL]).then((response)=>{
			if(response){
				if(response['result']){
					var data = response['data'];
					this[STRUCT_TABLE][DATA_TABLE] = data[DATA_TABLE];
					this[STRUCT_TABLE][PAGE_TOTAL] = data[PAGE_TOTAL];
					this[STRUCT_TABLE][PAGE_ACTIVE] = data[PAGE_ACTIVE];
					this[STRUCT_TABLE][FLAG_FILTER_CHANGE] = false;
					this.reload();
					
				}else{
					error_handle(response);
				}
			}
		})
		
	}
	
	clearFilter(){
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
		return this.model.read(dataKeys, loading, this[STRUCT_TABLE][DATA_SPECIAL]).then((res)=>{
			return res;
		})
	}

	sort(src_id, dest_id, loading=true){
		return this.model.sort(src_id, dest_id, loading, this[STRUCT_TABLE][DATA_SPECIAL]).then((res)=>{
			return res;
		})
	}
	
	reload(){

		for(let i in this.children){
			
			if(this.children[i]){
				if(this.children[i].reload){
					this.children[i].reload();
				}else{
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
	
	
	setMapping(response){
	   
  	  for (let i in response){
  		  	this.mapping[i] = response[i];
  		  	
  			if(isset(this[STRUCT_COLUMNS][i])){
  				this[STRUCT_COLUMNS][i][COL_OPTION] = response[i];
  			}
  			
  			if(isset(this[STRUCT_EDIT][i])){
  				if(this[STRUCT_EDIT][i][EDIT_TYPE] == 'select'){
  					this[STRUCT_EDIT][i][EDIT_OPTION] = {'':'', ...response[i]};
  				}else{
  					this[STRUCT_EDIT][i][EDIT_OPTION] = response[i];
  				}
  				
  			}
  			
  			if(isset(this[STRUCT_FILTERS][i])){
  				if(this[STRUCT_FILTERS][i][FILTER_TYPE] == 'select' || this[STRUCT_FILTERS][i][FILTER_TYPE] == 'check'){
  					this[STRUCT_FILTERS][i][FILTER_OPTION] = {'':lang('All'), ...response[i]};
  				}else{
  					this[STRUCT_FILTERS][i][FILTER_OPTION] = response[i];
  				}
  			}
  	  }
  	  
  	  this.reload();
	}
	
	componentDidMount(){
		
		if(this.props.autoload){
			this.map();
			this.filter();
		}
		
	}
	
	render () {
		
		return(
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


if(!global.TableContext) global.TableContext = React.createContext();
export default Table 
	  
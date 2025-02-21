import React, { Component } from 'react'
import FilterItem from './FilterItem'

class FilterRow extends Component {
	
	
	constructor(props, context) {
	    super(props, context);
	    this.table = this.context;
	    this.table.children['FilterRow'] = this;
		this.filter_item = {};
		
		
	}
	
	initial(){
		this.struct = get(this.table[STRUCT_FILTERS], []);
		this.colStruct = get(this.table[STRUCT_COLUMNS]);
		this.permitCol = this.table[STRUCT_TABLE][DATA_PERMIT_COL];
		this.hideCol = this.table[STRUCT_TABLE][DATA_HIDDEN_COL];
	}
	
	drawFilterItem(){
		
		var filterItems = [];
		if(this.table[STRUCT_TABLE][FLAG_SELECT_ROWS]) filterItems.push(<td key='table_select'></td>);
		if(this.table[STRUCT_TABLE][FLAG_ROW_INDEX]) filterItems.push(<td key='table_stt'></td>);
		if(this.table[STRUCT_TABLE][FLAG_SETTING_ROWS]) filterItems.push(<td key='table_setting'></td>)
		for(let i in this.colStruct){
			if(!this.permitCol[i]) continue; 
			if(this.hideCol[i]) continue;
			if(!this.struct[i]){
				var comp = <td key={i}></td>
			}else{
				var comp = <td key={i} style={{overflow: 'unset'}}><FilterItem className="filter_item_row" text={false} ref={input=>this.filter_item[i] = input} colID={i} onChangeBlur={()=>this.onChangeBlurHandle()} struct = {this.struct[i]}/></td>
			}
			filterItems.push(comp)
		}
		
		return filterItems 
	}
	
	loadFilter(){
		for (let i in this.filter_item){
			if(isset(this.filter_item[i])){
				if(isset(this.table[STRUCT_TABLE][DATA_FILTERS][i])){
					this.filter_item[i].setValue(this.table[STRUCT_TABLE][DATA_FILTERS][i]);
				}else{
					this.filter_item[i].setValue(null);
				}
			}
			
		}
	}
	
	onChangeBlurHandle(){
		this.table.setFilter(this.getValue());
	}
	
	getValue(){
		var values = {};
		for (let i in this.filter_item){
			if(!this.filter_item[i]) continue;
			values[i] = this.filter_item[i].getValue();
		}
		return values;
	}

	
	reload(){
		this.forceUpdate();
		this.loadFilter();
	}
	
	render () {
		this.initial();
		if(Object.keys(this.struct).length == 0) return <></>;
		return(<tr>{this.drawFilterItem()}</tr>);
	}
}

FilterRow.contextType = TableContext;

export default FilterRow
	  
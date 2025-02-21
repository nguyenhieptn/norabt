import React, { Component } from 'react'
import Table from '../../components/table/Table'
import MainTable from '../../components/table/MainTable'
import Pagination from '../../components/table/Pagination'
import FuncBar from '../../components/table/FuncBar'

import FuncEditRow from '../../components/table/FuncEditRow'
import FuncAdd from '../../components/table/FuncAdd'
import FuncHideCol from '../../components/table/FuncHideCol'
import FuncDel from '../../components/table/FuncDel'
import FuncClear from '../../components/table/FuncClear'
import FuncRefresh from '../../components/table/FuncRefresh'
import FuncExport from '../../components/table/FuncExport'

import Events from '../../model/admin/Events'

class EventsView extends Component {
	
	constructor(props) {
	    super(props);
	    
	    this.events_struct = {};
	    this.events_struct[STRUCT_FILTERS] = {}
	    this.events_struct[STRUCT_COLUMNS] = {
	    		
	    		[EVENT_SYMBOL]:{
                            [COL_NAME]: lang(EVENT_SYMBOL),
                            [COL_SORT]: true,
                            
                        },
                        [EVENT_TIME]:{
                            [COL_NAME]: lang(EVENT_TIME),
                            [COL_SORT]: true,
                            [COL_DECORATOR_IN]: (data)=>{ if(data == '') return data; else return moment(data, 'X').format(DATE_FORMAT)},
		        	 [COL_STYLE]: {whiteSpace: 'nowrap'}
                        },
                        [EVENT_PRICE]:{
                            [COL_NAME]: lang(EVENT_PRICE),
                            [COL_SORT]: true,
                            
                        },
                        [EVENT_TYPE]:{
                            [COL_NAME]: lang(EVENT_TYPE),
                            [COL_SORT]: true,
                            
                        },
                        [EVENT_BASE]:{
                            [COL_NAME]: lang(EVENT_BASE),
                            [COL_SORT]: true,
                            
                        },
                        [EVENT_PARAMS]:{
                            [COL_NAME]: lang(EVENT_PARAMS),
                            [COL_SORT]: true,
                            
                        },
                        
			
			
	    }
	    this.events_struct[STRUCT_FILTERS] = {
	    		
	    		[EVENT_SYMBOL]:{
    			 	[FILTER_NAME]: lang(EVENT_SYMBOL),
    			 	[FILTER_TYPE]:'text',
    			},
    			[EVENT_TIME]:{
    			 	[FILTER_NAME]: lang(EVENT_TIME),
    			 	[FILTER_TYPE]:'date',
    			},
    			[EVENT_PRICE]:{
    			 	[FILTER_NAME]: lang(EVENT_PRICE),
    			 	[FILTER_TYPE]:'text',
    			},
    			[EVENT_TYPE]:{
    			 	[FILTER_NAME]: lang(EVENT_TYPE),
    			 	[FILTER_TYPE]:'select',
    			},
    			[EVENT_BASE]:{
    			 	[FILTER_NAME]: lang(EVENT_BASE),
    			 	[FILTER_TYPE]:'text',
    			},
    			[EVENT_PARAMS]:{
    			 	[FILTER_NAME]: lang(EVENT_PARAMS),
    			 	[FILTER_TYPE]:'text',
    			},
    			
			
	    }
	    
	    this.events_struct[STRUCT_EDIT] = {
	    		
	    		[EVENT_SYMBOL]:{
    			 	[EDIT_NAME]: lang(EVENT_SYMBOL),
    			 	[EDIT_TYPE]:'text',
                    
    			},
    			[EVENT_TIME]:{
    			 	[EDIT_NAME]: lang(EVENT_TIME),
    			 	[EDIT_TYPE]:'date',
                    
    			},
    			[EVENT_PRICE]:{
    			 	[EDIT_NAME]: lang(EVENT_PRICE),
    			 	[EDIT_TYPE]:'text',
                    
    			},
    			[EVENT_TYPE]:{
    			 	[EDIT_NAME]: lang(EVENT_TYPE),
    			 	[EDIT_TYPE]:'select',
                    
    			},
    			[EVENT_BASE]:{
    			 	[EDIT_NAME]: lang(EVENT_BASE),
    			 	[EDIT_TYPE]:'text',
                    
    			},
    			[EVENT_PARAMS]:{
    			 	[EDIT_NAME]: lang(EVENT_PARAMS),
    			 	[EDIT_TYPE]:'text',
                    
    			},
    			
				
		    }
	    
	    this.events_struct[STRUCT_ROWS]= {
	    		[ROW_FUNCS]: (rowData) => {
	    			return <div className='box_flex' style={{justifyContent:'center'}}>
						<FuncEditRow rowData={rowData}/>
					</div>
	    		}
	    };
	    this.events_struct[STRUCT_TABLE]= {
	            [DATA_TABLE_ID] : EVENTS_TABLE,
	            [DATA_SPECIAL]: {symbol: App.symbol},
	            [DATA_HIDDEN_COL] : {[EVENT_BASE]: true},
	            [DATA_PERMIT_COL] : this.permissionEventsView(),
	            [DATA_KEY] : [EVENT_ID],
	            [DATA_SORT] : {[EVENT_ID] : 'desc'},
				[FLAG_FILTER]: true,
	            [FLAG_FILTER_CHANGE] : true,
	            [FLAG_MULTI_SORT] : false,
	            [FLAG_RESIZABLE] : true,
	            [FLAG_SELECT_ROWS] : true,
	            [FLAG_SETTING_ROWS] : true,
	            [FLAG_EXPAND_ROWS] : false,
	            [FLAG_HEAD_ROW] : true,
	            
				model: new Events()
	            
	    };
	    
	    
	}
	
	permissionEventsView(){
		return Object.assign(
			...Object.keys(this.events_struct[STRUCT_COLUMNS]).map((k, i) => ({[k]: 'Read'})), 
			...Object.keys(this.events_struct[STRUCT_EDIT]).map((k, i) => ({[k]: 'Write'})), 
		)
	}
	
	render () {
		  return(
			  <div>
				  <Table ref={c => this.table = c} table = {this.events_struct} autoload={true}>
				  	<FuncBar 
					  	left = {<FuncHideCol/>}
					  	right = {<><FuncAdd/><FuncDel/><FuncClear/><FuncRefresh/><FuncExport/></>}></FuncBar>
				  	<MainTable className='table table-bordered table-striped table-resizable'></MainTable>
				  	<Pagination></Pagination>
				  	
				  </Table>

				  
			  </div>
		  ); 
	  }
}

export default EventsView
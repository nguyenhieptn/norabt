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

import Testnet_events from '../../model/admin/Testnet_events'

class Testnet_eventsView extends Component {
	
	constructor(props) {
	    super(props);
	    
	    this.testnet_events_struct = {};
	    this.testnet_events_struct[STRUCT_FILTERS] = {}
	    this.testnet_events_struct[STRUCT_COLUMNS] = {
	    		
	    		[TESTNET_EVENTS_SYMBOL]:{
                            [COL_NAME]: lang(TESTNET_EVENTS_SYMBOL),
                            [COL_SORT]: true,
                            
                        },
                        [TESTNET_EVENTS_TIME]:{
                            [COL_NAME]: lang(TESTNET_EVENTS_TIME),
                            [COL_SORT]: true,
                            
                        },
                        [TESTNET_EVENTS_ICON]:{
                            [COL_NAME]: lang(TESTNET_EVENTS_ICON),
                            [COL_SORT]: false,
                            
                        },
                        [TESTNET_EVENTS_PROFIT]:{
                            [COL_NAME]: lang(TESTNET_EVENTS_PROFIT),
                            [COL_SORT]: true,
                            
                        },
                        [TESTNET_EVENTS_CONTENT]:{
                            [COL_NAME]: lang(TESTNET_EVENTS_CONTENT),
                            [COL_SORT]: false,
                            
                        },
                        [TESTNET_EVENTS_STRATEGY]:{
                            [COL_NAME]: lang(TESTNET_EVENTS_STRATEGY),
                            [COL_SORT]: true,
                            
                        },
                        [TESTNET_EVENTS_CAMPAIGN]:{
                            [COL_NAME]: lang(TESTNET_EVENTS_CAMPAIGN),
                            [COL_SORT]: true,
                            
                        },
                        
			
			
	    }
	    this.testnet_events_struct[STRUCT_FILTERS] = {
	    		
	    		[TESTNET_EVENTS_SYMBOL]:{
    			 	[FILTER_NAME]: lang(TESTNET_EVENTS_SYMBOL),
    			 	[FILTER_TYPE]:'text',
    			},
    			[TESTNET_EVENTS_PROFIT]:{
    			 	[FILTER_NAME]: lang(TESTNET_EVENTS_PROFIT),
    			 	[FILTER_TYPE]:'text',
    			},
    			[TESTNET_EVENTS_STRATEGY]:{
    			 	[FILTER_NAME]: lang(TESTNET_EVENTS_STRATEGY),
    			 	[FILTER_TYPE]:'text',
    			},
    			[TESTNET_EVENTS_CAMPAIGN]:{
    			 	[FILTER_NAME]: lang(TESTNET_EVENTS_CAMPAIGN),
    			 	[FILTER_TYPE]:'text',
    			},
    			
			
	    }
	    
	    this.testnet_events_struct[STRUCT_EDIT] = {
	    		
	    		[TESTNET_EVENTS_SYMBOL]:{
    			 	[EDIT_NAME]: lang(TESTNET_EVENTS_SYMBOL),
    			 	[EDIT_TYPE]:'text',
                    
    			},
    			[TESTNET_EVENTS_TIME]:{
    			 	[EDIT_NAME]: lang(TESTNET_EVENTS_TIME),
    			 	[EDIT_TYPE]:'Number',
                    
    			},
    			[TESTNET_EVENTS_ICON]:{
    			 	[EDIT_NAME]: lang(TESTNET_EVENTS_ICON),
    			 	[EDIT_TYPE]:'textarea',
                    
    			},
    			[TESTNET_EVENTS_PROFIT]:{
    			 	[EDIT_NAME]: lang(TESTNET_EVENTS_PROFIT),
    			 	[EDIT_TYPE]:'text',
                    
    			},
    			[TESTNET_EVENTS_CONTENT]:{
    			 	[EDIT_NAME]: lang(TESTNET_EVENTS_CONTENT),
    			 	[EDIT_TYPE]:'textarea',
                    
    			},
    			[TESTNET_EVENTS_STRATEGY]:{
    			 	[EDIT_NAME]: lang(TESTNET_EVENTS_STRATEGY),
    			 	[EDIT_TYPE]:'Number',
                    
    			},
    			[TESTNET_EVENTS_CAMPAIGN]:{
    			 	[EDIT_NAME]: lang(TESTNET_EVENTS_CAMPAIGN),
    			 	[EDIT_TYPE]:'Number',
                    
    			},
    			
				
		    }
	    
	    this.testnet_events_struct[STRUCT_ROWS]= {
	    		[ROW_FUNCS]: (rowData) => {
	    			return <div className='box_flex' style={{justifyContent:'center'}}>
						<FuncEditRow rowData={rowData}/>
					</div>
	    		}
	    };
	    this.testnet_events_struct[STRUCT_TABLE]= {
	            [DATA_TABLE_ID] : TESTNET_EVENTS_TABLE,
	            [DATA_FILTERS] : {},
	            [DATA_HIDDEN_COL] : {},
	            [DATA_PERMIT_COL] : this.permissionTestnet_eventsView(),
	            [DATA_KEY] : [TESTNET_EVENTS_ID],
	            [DATA_SORT] : {[TESTNET_EVENTS_ID] : 'desc'},
				[FLAG_FILTER]: true,
	            [FLAG_FILTER_CHANGE] : true,
	            [FLAG_MULTI_SORT] : false,
	            [FLAG_RESIZABLE] : true,
	            [FLAG_SELECT_ROWS] : true,
	            [FLAG_SETTING_ROWS] : true,
	            [FLAG_EXPAND_ROWS] : false,
	            [FLAG_HEAD_ROW] : true,
	            
				model: new Testnet_events()
	            
	    };
	    
	    
	}
	
	permissionTestnet_eventsView(){
		return Object.assign(
			...Object.keys(this.testnet_events_struct[STRUCT_COLUMNS]).map((k, i) => ({[k]: 'Read'})), 
			...Object.keys(this.testnet_events_struct[STRUCT_EDIT]).map((k, i) => ({[k]: 'Write'})), 
		)
	}
	
	render () {
		  return(
			  <div>
				  <Table ref={c => this.table = c} table = {this.testnet_events_struct} autoload={true}>
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

export default Testnet_eventsView
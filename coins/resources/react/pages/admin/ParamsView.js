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

import Params from '../../model/admin/Params'

class ParamsView extends Component {
	
	constructor(props) {
	    super(props);
	    
	    this.params_struct = {};
	    this.params_struct[STRUCT_FILTERS] = {}
	    this.params_struct[STRUCT_COLUMNS] = {
	    		
	    		[PARAM_NAME]:{
                            [COL_NAME]: lang(PARAM_NAME),
                            [COL_SORT]: true,
                            
                        },
                        [PARAM_TIMELIFE]:{
                            [COL_NAME]: lang(PARAM_TIMELIFE),
                            [COL_SORT]: true,
                            
                        },
                        [PARAM_TAKEPROFIT]:{
                            [COL_NAME]: lang(PARAM_TAKEPROFIT),
                            [COL_SORT]: true,
                            
                        },
                        [PARAM_BASEPROFIT]:{
                            [COL_NAME]: lang(PARAM_BASEPROFIT),
                            [COL_SORT]: true,
                            
                        },
                        [PARAM_STEPPROFIT]:{
                            [COL_NAME]: lang(PARAM_STEPPROFIT),
                            [COL_SORT]: true,
                            
                        },
                        [PARAM_TOPLOSS]:{
                            [COL_NAME]: lang(PARAM_TOPLOSS),
                            [COL_SORT]: true,
                            
                        },
                        [PARAM_MARGIN]:{
                            [COL_NAME]: lang(PARAM_MARGIN),
                            [COL_SORT]: true,
                            
                        },
                        
			
			
	    }
	    this.params_struct[STRUCT_FILTERS] = {
	    		
	    		[PARAM_NAME]:{
    			 	[FILTER_NAME]: lang(PARAM_NAME),
    			 	[FILTER_TYPE]:'text',
    			},
    			[PARAM_TIMELIFE]:{
    			 	[FILTER_NAME]: lang(PARAM_TIMELIFE),
    			 	[FILTER_TYPE]:'text',
    			},
    			[PARAM_TAKEPROFIT]:{
    			 	[FILTER_NAME]: lang(PARAM_TAKEPROFIT),
    			 	[FILTER_TYPE]:'text',
    			},
				[PARAM_STEPPROFIT]:{
					[FILTER_NAME]: lang(PARAM_STEPPROFIT),
					[FILTER_TYPE]:'text',
			   },
				[PARAM_BASEPROFIT]:{
					[FILTER_NAME]: lang(PARAM_BASEPROFIT),
					[FILTER_TYPE]:'text',
			   },
    			[PARAM_TOPLOSS]:{
    			 	[FILTER_NAME]: lang(PARAM_TOPLOSS),
    			 	[FILTER_TYPE]:'text',
    			},
    			[PARAM_MARGIN]:{
    			 	[FILTER_NAME]: lang(PARAM_MARGIN),
    			 	[FILTER_TYPE]:'text',
    			},
    			
			
	    }
	    
	    this.params_struct[STRUCT_EDIT] = {
	    		
	    		[PARAM_NAME]:{
    			 	[EDIT_NAME]: lang(PARAM_NAME),
    			 	[EDIT_TYPE]:'text',
    			 	[EDIT_NULL]:false,
                    
    			},
    			[PARAM_TIMELIFE]:{
    			 	[EDIT_NAME]: lang(PARAM_TIMELIFE),
    			 	[EDIT_TYPE]:'Number',
                    
    			},
    			[PARAM_TAKEPROFIT]:{
    			 	[EDIT_NAME]: lang(PARAM_TAKEPROFIT),
    			 	[EDIT_TYPE]:'Number',
					[EDIT_NULL]:false,
                    
    			},
				[PARAM_STEPPROFIT]:{
					[EDIT_NAME]: lang(PARAM_STEPPROFIT),
					[EDIT_TYPE]:'Number',
					[EDIT_NULL]:false,
				   
			   },
				[PARAM_BASEPROFIT]:{
					[EDIT_NAME]: lang(PARAM_BASEPROFIT),
					[EDIT_TYPE]:'Number',
					[EDIT_NULL]:false,
			   },
    			[PARAM_TOPLOSS]:{
    			 	[EDIT_NAME]: lang(PARAM_TOPLOSS),
    			 	[EDIT_TYPE]:'Number',
					[EDIT_NULL]:false,
                    
    			},
    			[PARAM_MARGIN]:{
    			 	[EDIT_NAME]: lang(PARAM_MARGIN),
    			 	[EDIT_TYPE]:'Number',
                    
    			},
    			
				
		    }
	    
	    this.params_struct[STRUCT_ROWS]= {
	    		[ROW_FUNCS]: (rowData) => {
	    			return <div className='box_flex' style={{justifyContent:'center'}}>
						<FuncEditRow rowData={rowData}/>
					</div>
	    		}
	    };
	    this.params_struct[STRUCT_TABLE]= {
	            [DATA_TABLE_ID] : PARAMS_TABLE,
	            [DATA_FILTERS] : {},
	            [DATA_HIDDEN_COL] : {},
	            [DATA_PERMIT_COL] : this.permissionParamsView(),
	            [DATA_KEY] : [PARAM_ID],
	            [DATA_SORT] : {[PARAM_ID] : 'desc'},
				[FLAG_FILTER]: true,
	            [FLAG_FILTER_CHANGE] : true,
	            [FLAG_MULTI_SORT] : false,
	            [FLAG_RESIZABLE] : true,
	            [FLAG_SELECT_ROWS] : true,
	            [FLAG_SETTING_ROWS] : true,
	            [FLAG_EXPAND_ROWS] : false,
	            [FLAG_HEAD_ROW] : true,
	            
				model: new Params()
	            
	    };
	    
	    
	}
	
	permissionParamsView(){
		return Object.assign(
			...Object.keys(this.params_struct[STRUCT_COLUMNS]).map((k, i) => ({[k]: 'Read'})), 
			...Object.keys(this.params_struct[STRUCT_EDIT]).map((k, i) => ({[k]: 'Write'})), 
		)
	}
	
	render () {
		  return(
			  <div>
				  <Table ref={c => this.table = c} table = {this.params_struct} autoload={true}>
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

export default ParamsView
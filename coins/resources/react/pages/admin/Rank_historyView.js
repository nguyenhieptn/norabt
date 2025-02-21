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

import Rank_history from '../../model/admin/Rank_history'

class Rank_historyView extends Component {
	
	constructor(props) {
	    super(props);
	    
	    this.rank_history_struct = {};
	    this.rank_history_struct[STRUCT_FILTERS] = {}
	    this.rank_history_struct[STRUCT_COLUMNS] = {
	    		
	    		[RANK_HIS_YEAR]:{
                            [COL_NAME]: lang(RANK_HIS_YEAR),
                            [COL_SORT]: true,
                            
                        },
                        [RANK_HIS_TIME]:{
                            [COL_NAME]: lang(RANK_HIS_TIME),
                            [COL_SORT]: true,
                            
                        },
                        [RANK_HIS_SYMBOL]:{
                            [COL_NAME]: lang(RANK_HIS_SYMBOL),
                            [COL_SORT]: true,
                            
                        },
                        [RANK_HIS_VALUE]:{
                            [COL_NAME]: lang(RANK_HIS_VALUE),
                            [COL_SORT]: true,
                            
                        },
                        [RANK_HIS_MARKET_CAP]:{
                            [COL_NAME]: lang(RANK_HIS_MARKET_CAP),
                            [COL_SORT]: true,
                            
                        },
                        [RANK_HIS_PRICE]:{
                            [COL_NAME]: lang(RANK_HIS_PRICE),
                            [COL_SORT]: true,
                            
                        },
                        [RANK_HIS_VOLUME_24H]:{
                            [COL_NAME]: lang(RANK_HIS_VOLUME_24H),
                            [COL_SORT]: true,
                            
                        },
                        
			
			
	    }
	    this.rank_history_struct[STRUCT_FILTERS] = {
	    		
	    		[RANK_HIS_YEAR]:{
    			 	[FILTER_NAME]: lang(RANK_HIS_YEAR),
    			 	[FILTER_TYPE]:'text',
    			},
    			[RANK_HIS_SYMBOL]:{
    			 	[FILTER_NAME]: lang(RANK_HIS_SYMBOL),
    			 	[FILTER_TYPE]:'text',
    			},
    			[RANK_HIS_VALUE]:{
    			 	[FILTER_NAME]: lang(RANK_HIS_VALUE),
    			 	[FILTER_TYPE]:'text',
    			},
    			[RANK_HIS_MARKET_CAP]:{
    			 	[FILTER_NAME]: lang(RANK_HIS_MARKET_CAP),
    			 	[FILTER_TYPE]:'text',
    			},
    			[RANK_HIS_PRICE]:{
    			 	[FILTER_NAME]: lang(RANK_HIS_PRICE),
    			 	[FILTER_TYPE]:'text',
    			},
    			[RANK_HIS_VOLUME_24H]:{
    			 	[FILTER_NAME]: lang(RANK_HIS_VOLUME_24H),
    			 	[FILTER_TYPE]:'text',
    			},
    			
			
	    }
	    
	    this.rank_history_struct[STRUCT_EDIT] = {
	    		
	    		[RANK_HIS_YEAR]:{
    			 	[EDIT_NAME]: lang(RANK_HIS_YEAR),
    			 	[EDIT_TYPE]:'Number',
                    
    			},
    			[RANK_HIS_TIME]:{
    			 	[EDIT_NAME]: lang(RANK_HIS_TIME),
    			 	[EDIT_TYPE]:'Number',
                    
    			},
    			[RANK_HIS_SYMBOL]:{
    			 	[EDIT_NAME]: lang(RANK_HIS_SYMBOL),
    			 	[EDIT_TYPE]:'text',
                    
    			},
    			[RANK_HIS_VALUE]:{
    			 	[EDIT_NAME]: lang(RANK_HIS_VALUE),
    			 	[EDIT_TYPE]:'Number',
                    
    			},
    			[RANK_HIS_MARKET_CAP]:{
    			 	[EDIT_NAME]: lang(RANK_HIS_MARKET_CAP),
    			 	[EDIT_TYPE]:'text',
                    
    			},
    			[RANK_HIS_PRICE]:{
    			 	[EDIT_NAME]: lang(RANK_HIS_PRICE),
    			 	[EDIT_TYPE]:'text',
                    
    			},
    			[RANK_HIS_VOLUME_24H]:{
    			 	[EDIT_NAME]: lang(RANK_HIS_VOLUME_24H),
    			 	[EDIT_TYPE]:'text',
                    
    			},
    			
				
		    }
	    
	    this.rank_history_struct[STRUCT_ROWS]= {
	    		[ROW_FUNCS]: (rowData) => {
	    			return <div className='box_flex' style={{justifyContent:'center'}}>
						<FuncEditRow rowData={rowData}/>
					</div>
	    		}
	    };
	    this.rank_history_struct[STRUCT_TABLE]= {
	            [DATA_TABLE_ID] : RANK_HISTORY_TABLE,
	            [DATA_FILTERS] : {},
	            [DATA_HIDDEN_COL] : {},
	            [DATA_PERMIT_COL] : this.permissionRank_historyView(),
	            [DATA_KEY] : [RANK_HIS_ID],
	            [DATA_SORT] : {[RANK_HIS_ID] : 'desc'},
				[FLAG_FILTER]: true,
	            [FLAG_FILTER_CHANGE] : true,
	            [FLAG_MULTI_SORT] : false,
	            [FLAG_RESIZABLE] : true,
	            [FLAG_SELECT_ROWS] : true,
	            [FLAG_SETTING_ROWS] : true,
	            [FLAG_EXPAND_ROWS] : false,
	            [FLAG_HEAD_ROW] : true,
	            
				model: new Rank_history()
	            
	    };
	    
	    
	}
	
	permissionRank_historyView(){
		return Object.assign(
			...Object.keys(this.rank_history_struct[STRUCT_COLUMNS]).map((k, i) => ({[k]: 'Read'})), 
			...Object.keys(this.rank_history_struct[STRUCT_EDIT]).map((k, i) => ({[k]: 'Write'})), 
		)
	}
	
	render () {
		  return(
			  <div>
				  <Table ref={c => this.table = c} table = {this.rank_history_struct} autoload={true}>
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

export default Rank_historyView
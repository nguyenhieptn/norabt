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

import Fear from '../../model/admin/Fear'

class FearView extends Component {
	
	constructor(props) {
	    super(props);
	    
	    this.fear_struct = {};
	    this.fear_struct[STRUCT_FILTERS] = {}
	    this.fear_struct[STRUCT_COLUMNS] = {
	    		
	    		[FEAR_TIME]:{
                            [COL_NAME]: lang(FEAR_TIME),
                            [COL_SORT]: true,
                            [COL_DECORATOR_IN]: (data)=>{ if(data == '') return data; else return moment(data, 'X').format(DATE_FORMAT)},
		        	 [COL_STYLE]: {whiteSpace: 'nowrap'}
                        },
                        [FEAR_VALUE]:{
                            [COL_NAME]: lang(FEAR_VALUE),
                            [COL_SORT]: true,
                            
                        },
                        [FEAR_CLASS]:{
                            [COL_NAME]: lang(FEAR_CLASS),
                            [COL_SORT]: true,
                            
                        },
                        
			
			
	    }
	    this.fear_struct[STRUCT_FILTERS] = {
	    		
	    		[FEAR_VALUE]:{
    			 	[FILTER_NAME]: lang(FEAR_VALUE),
    			 	[FILTER_TYPE]:'text',
    			},
    			[FEAR_CLASS]:{
    			 	[FILTER_NAME]: lang(FEAR_CLASS),
    			 	[FILTER_TYPE]:'select',
    			},
    			
			
	    }
	    
	    this.fear_struct[STRUCT_EDIT] = {
	    		
	    		[FEAR_TIME]:{
    			 	[EDIT_NAME]: lang(FEAR_TIME),
    			 	[EDIT_TYPE]:'date',
                    
    			},
    			[FEAR_VALUE]:{
    			 	[EDIT_NAME]: lang(FEAR_VALUE),
    			 	[EDIT_TYPE]:'text',
                    
    			},
    			[FEAR_CLASS]:{
    			 	[EDIT_NAME]: lang(FEAR_CLASS),
    			 	[EDIT_TYPE]:'select',
                    
    			},
    			
				
		    }
	    
	    this.fear_struct[STRUCT_ROWS]= {
	    		[ROW_FUNCS]: (rowData) => {
	    			return <div className='box_flex' style={{justifyContent:'center'}}>
						<FuncEditRow rowData={rowData}/>
					</div>
	    		}
	    };
	    this.fear_struct[STRUCT_TABLE]= {
	            [DATA_TABLE_ID] : FEAR_TABLE,
	            [DATA_FILTERS] : {},
	            [DATA_HIDDEN_COL] : {},
	            [DATA_PERMIT_COL] : this.permissionFearView(),
	            [DATA_KEY] : [FEAR_ID],
	            [DATA_SORT] : {[FEAR_ID] : 'desc'},
				[FLAG_FILTER]: true,
	            [FLAG_FILTER_CHANGE] : true,
	            [FLAG_MULTI_SORT] : false,
	            [FLAG_RESIZABLE] : true,
	            [FLAG_SELECT_ROWS] : true,
	            [FLAG_SETTING_ROWS] : true,
	            [FLAG_EXPAND_ROWS] : false,
	            [FLAG_HEAD_ROW] : true,
	            
				model: new Fear()
	            
	    };
	    
	    
	}
	
	permissionFearView(){
		return Object.assign(
			...Object.keys(this.fear_struct[STRUCT_COLUMNS]).map((k, i) => ({[k]: 'Read'})), 
			...Object.keys(this.fear_struct[STRUCT_EDIT]).map((k, i) => ({[k]: 'Write'})), 
		)
	}
	
	render () {
		  return(
			  <div>
				  <Table ref={c => this.table = c} table = {this.fear_struct} autoload={true}>
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

export default FearView
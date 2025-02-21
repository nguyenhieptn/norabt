import React, { Component } from 'react';

import Table from '../../components/table/TableStatic'
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



import Ctrl from '../../model/control/Ctrl'
import FuncEditAlertVolatility from '../../components/admin/FuncEditAlertVolatility';
import FuncAddAlertVolatility from '../../components/admin/FuncAddAlertVolatility';



class Alert_volatilityView extends Component {
    constructor(props) {
		super(props);
		this.id = makeId();
		this.table_alert_struct = {};
		this.table_alert_struct[STRUCT_FILTERS] = {}
		this.table_alert_struct[STRUCT_COLUMNS] = {

			'name': {
				[COL_NAME]: 'Name',
				[COL_SORT]: true,

			},

            'active': {
				[COL_NAME]: 'Active',
				[COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => { 
                    if(data ==1) return <span style={{ color :' limegreen'}}>Active</span>;
                   return <span style={{ color :' red'}}>Disable</span>;
                 },
                 [COL_STYLE] : {textAlign : 'center'}

			},
			'icon': {
				[COL_NAME]: 'Icon',
				[COL_SORT]: true,
                [COL_STYLE] : {textAlign : 'center'},

			},

        

            'content': {
				[COL_NAME]: 'Content',
				[COL_SORT]: true,

			},

            'bot': {
				[COL_NAME]: 'Bot',
				[COL_SORT]: true,

			},

            'group': {
				[COL_NAME]: 'Group Id',
				[COL_SORT]: true,
                [COL_STYLE] : {textAlign : 'center'}

			},

			
			'note': {
				[COL_NAME]: 'Note',
				[COL_SORT]: true,

			},

        

		
		}
		this.table_alert_struct[STRUCT_FILTERS] = {

			'name': {
				[FILTER_NAME]: 'name',
				[FILTER_TYPE]: 'text',
			},
            // 'group': {
			// 	[FILTER_NAME]: 'group',
			// 	[FILTER_TYPE]: 'number',
			// },
			// [POSITION_UPDATE_TIME]: {
			// 	[FILTER_NAME]: lang(POSITION_UPDATE_TIME),
			// 	[FILTER_TYPE]: 'date',
			// 	[FILTER_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
			// 	[FILTER_DECORATOR_OUT]: (data) => { if (data == '') return data; else return moment(data, DATE_FORMAT).format('x') },
			// },
			active: {
				[FILTER_NAME]: 'active',
				[FILTER_TYPE]: 'select',
				[FILTER_OPTION]: {
					'': 'All',
					[1]: 'Active',
					[0]: 'Disable'
				}
			},


		}


		this.table_alert_struct[STRUCT_EDIT] = {


		}

		this.table_alert_struct[STRUCT_ROWS] = {
		    [ROW_FUNCS]: (rowData) => {
		        return <div className='box_flex' style={{ justifyContent: 'center' }}>
		            <FuncEditRow onClick={() => {
                        this.EditModel.setData(this.state.config , rowData)  ;
                        this.EditModel.modal();
                    }
                        
                    } />
					<div className="button" title={lang("Delete Row")} onClick={() => { this.onClickDeleteHandle(rowData) }}>
						<i className="fa fa-trash"></i>
					</div>
		        </div>
		    }
		};
		this.table_alert_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: '1ass12',
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionTableAlertView(),
			[DATA_KEY]: [],
			[DATA_SORT]: {},
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,



		};

		
	}

	permissionTableAlertView() {
		return Object.assign(
			...Object.keys(this.table_alert_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.table_alert_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}


    componentDidMount(){
         this.loadOrigin();
    }

	reloadOrigin(){
		this.loadOrigin();
	}

	onClickDeleteHandle(rowData){
		makeQuestion('Do you want to delete?').then(res => {
			if(res){
				var index1;
				this.state.config.map((item,index) =>{
					
					if(item.id == rowData.id) {index1 = index  }
				} 
				
				)
				this.state.config.splice(index1, 1);
				this.saveData();
				
			}	
		}
		)
		
	}

	saveData() {
        
        var ctrl = new Ctrl();
        ctrl.set({ 'track_avg_alter': JSON.stringify(this.state.config) }).then(res => {
            this.loadOrigin();
            this.reloadAlertService();
            // if (res['result']) this.modal('hide');
        });
    }


    reloadAlertService() {
        App.loading(true);
        return axios.request({
            url: '/admin/volatility/reloadAlert',
            method: 'POST',

        })
            .then(response => {
                App.loading(false, 'Loading...');
                response = response['data'];
                if (!response['result']) {
                    error_handle(response);

                }
            })

            .catch((error) => {
                console.log(error);
                App.loading(false, 'Loading...');
                error_handle(error)

            })
    }

	


	async loadOrigin() {
        var ctrl = new Ctrl();
        ctrl.get('track_avg_alter', null).then(cfg => {
       
            if (cfg != null) {
                cfg = JSON.parse(cfg);
                this.setState({ config: cfg })
                this.table.setOrigin(cfg);
            }
        });

	}
	funcClone() {
		return (
			<div className="table_function">

				<div className="button" title="Add Row"
					onClick={(e) => {
						var dataSelect = this.table[STRUCT_TABLE][DATA_SELECT_ROWS];
						
						var data = Object.values(dataSelect)[0];
						var leng =  Object.keys(dataSelect).length ; 


						if (leng !== 1) {
							showLog('Please select one optimization');
							return;
						}
				
						this.AddModel.setData(this.state.config , data);
						this.AddModel.modal();
						
					}}
					style={{ display: 'flex' }}>
					<i className="fa fa-clone"></i>&nbsp;Clone
				</div>

			</div>
		)
	}

	render() {


		return (
			<>
				<Table ref={c => this.table = c} table={this.table_alert_struct} autoload={false} loadOrigin={this.loadOrigin.bind(this)}>
					<FuncBar
						left={<>
							<div className='box_flex'>
								<FuncHideCol />
							</div>
						</>}
						right={<>
							<div onClick={() => {
								this.AddModel.setData(this.state.config);
								this.AddModel.modal();
							}} className="button" title="Add Row"  style={{display : 'flex'}}  ><i className="fa fa-plus-square"></i>&nbsp;Add</div>
						{this.funcClone()}<FuncClear></FuncClear><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-striped table-resizable' minHeight={0}></MainTable>
					<Pagination></Pagination>

				</Table>


			
			  <FuncEditAlertVolatility  reload={() => this.reloadOrigin()} ref={c => this.EditModel = c}></FuncEditAlertVolatility>
			  <FuncAddAlertVolatility reload={() => this.reloadOrigin()} ref={c => this.AddModel = c}></FuncAddAlertVolatility>

			</>
		)
	}

}

export default Alert_volatilityView;
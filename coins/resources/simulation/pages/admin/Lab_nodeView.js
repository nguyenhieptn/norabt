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

import Lab_node from '../../model/admin/Lab_node'
import ToolTip from '../../components/common/Tooltip'

class Lab_nodeView extends Component {

	constructor(props) {
		super(props);

		this.lab_node_struct = {};
		this.lab_node_struct[STRUCT_FILTERS] = {}
		this.lab_node_struct[STRUCT_COLUMNS] = {

			[LAB_NODE_NAME]: {
				[COL_NAME]: lang(LAB_NODE_NAME),
				[COL_SORT]: true,
				[COL_STYLE]: {overflow:'unset'},
				[COL_DECORATOR_IN]: data => {
					let tooltip = null;
					return <div style={{position:'relative'}}>
						<ToolTip ref={c => tooltip = c}></ToolTip>
						<b className='button' style={{fontSize:12}} onClick={() => {
							this.mainModel.getSystemInfo(data).then(res => {
								if(res['result']){
									res = res['data']
									let ms = `
										CPU: ${res['cpu']}%
										RAM: ${res['ram']}%
										DISK: ${res['disk']}%
									`
									tooltip.set(true, ms, false, 5000)
								}else{
									tooltip.set(true, res['message'], false, 5000)
								}
							})
						}}>{data}</b>
					</div>
				}

			},
			[LAB_NODE_CPU]: {
				[COL_NAME]: lang(LAB_NODE_CPU),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					// return (<span style={data <= 50 ? { color: 'limegreen' } : { color: 'red' }}>{`${data} %`}</span>)
					var process = data[rowId][colId];
					var total = data[rowId][LAB_NODE_CPU_CORE]  ;
					var background = 'limegreen';
					if(process > 50) background = 'orange'
					if(process > 80) background = 'red'

					return <div className='box_flex' style={{ minWidth: 200 }}>

						<div className="progress" style={{ flexGrow: 1, border:'solid thin ' + background }}>
							<div className="progress-bar progress-bar-striped active" role="progressbar" style={{ background : background, width: `${process}%` , color: 'black', textShadow: 'white 1px 0px, white -1px 0px, white 0px 1px, white 0px -1px'   }}>
								&nbsp;&nbsp;{`${process} % / ${total} Core`}
							</div>
						</div>

					</div>
				},


			},
			[LAB_NODE_RAM]: {
				[COL_NAME]: lang(LAB_NODE_RAM),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					// return (<span style={data <= 50 ? { color: 'limegreen' } : { color: 'red' }}>{`${data} %`}</span>)
					var process = data[rowId][colId];
					var total = Math.round((data[rowId][LAB_NODE_RAM_TOTAL] / 1073741824) * 10) / 10 ;
					var background = 'limegreen';
					if(process > 50) background = 'orange'
					if(process > 80) background = 'red'

					return <div className='box_flex' style={{ minWidth: 200 }}>

						<div className="progress" style={{ flexGrow: 1, border:'solid thin ' + background }}>
							<div className="progress-bar progress-bar-striped active" role="progressbar" style={{ background : background, width: `${process}%` , color: 'black', textShadow: 'white 1px 0px, white -1px 0px, white 0px 1px, white 0px -1px'   }}>
								&nbsp;&nbsp;{`${process} % / ${total} G`}
							</div>
						</div>

					</div>
				},


			},
			
			[LAB_NODE_DISK]: {
				[COL_NAME]: lang(LAB_NODE_DISK),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (colId, rowId, data) => {
					// return (<span style={data <= 50 ? { color: 'limegreen' } : { color: 'red' }}>{`${data} %`}</span>)
					var process = data[rowId][colId];
					var total = Math.round((data[rowId][LAB_NODE_DISK_TOTAL] / 1073741824) * 10) / 10 ;
					var background = 'limegreen';
					if(process > 50) background = 'orange'
					if(process > 80) background = 'red'

					return <div className='box_flex' style={{ minWidth: 200 }}>

						<div className="progress" style={{ flexGrow: 1, border:'solid thin ' + background }}>
							<div className="progress-bar progress-bar-striped active" role="progressbar" style={{ background : background, width: `${process}%` , color: 'black', textShadow: 'white 1px 0px, white -1px 0px, white 0px 1px, white 0px -1px'   }}>
								&nbsp;&nbsp;{`${process} % / ${total} G`}
							</div>
						</div>

					</div>
				},


			},
			[LAB_NODE_STATUS]: {
				[COL_NAME]: lang(LAB_NODE_STATUS),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => {
					return (<span style={data == 'CONNECTED' ? { color: 'limegreen' } : { color: 'red' }}>{`${data}`}</span>)
				},


			},
			[LAB_NODE_IP]: {
				[COL_NAME]: lang(LAB_NODE_IP),
				[COL_SORT]: true,

			},
			[LAB_NODE_PORT]: {
				[COL_NAME]: lang(LAB_NODE_PORT),
				[COL_SORT]: true,

			},
			[LAB_NODE_SID]: {
				[COL_NAME]: lang(LAB_NODE_SID),
				[COL_SORT]: true,

			},
		
			
			[LAB_NODE_VERSION]: {
				[COL_NAME]: lang(LAB_NODE_VERSION),
				[COL_SORT]: true,

			},
			
			[LAB_NODE_NOTE]: {
				[COL_NAME]: lang(LAB_NODE_NOTE),
				[COL_SORT]: false,

			},



		}
		this.lab_node_struct[STRUCT_FILTERS] = {

			[LAB_NODE_NAME]: {
				[FILTER_NAME]: lang(LAB_NODE_NAME),
				[FILTER_TYPE]: 'text',
			},
			[LAB_NODE_IP]: {
				[FILTER_NAME]: lang(LAB_NODE_IP),
				[FILTER_TYPE]: 'text',
			},
			[LAB_NODE_PORT]: {
				[FILTER_NAME]: lang(LAB_NODE_PORT),
				[FILTER_TYPE]: 'text',
			},
			[LAB_NODE_SID]: {
				[FILTER_NAME]: lang(LAB_NODE_SID),
				[FILTER_TYPE]: 'text',
			},
			[LAB_NODE_STATUS]: {
				[FILTER_NAME]: lang(LAB_NODE_STATUS),
				[FILTER_TYPE]: 'text',
			},
			


		}

		this.lab_node_struct[STRUCT_EDIT] = {

		
			[LAB_NODE_NOTE]: {
				[EDIT_NAME]: lang(LAB_NODE_NOTE),
				[EDIT_TYPE]: 'textarea',

			},


		}

		this.lab_node_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData} />
				</div>
			}
		};

		this.mainModel = new Lab_node();
		this.lab_node_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: LAB_NODE_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionLab_nodeView(),
			[DATA_KEY]: [LAB_NODE_ID],
			[DATA_SORT]: { [LAB_NODE_ID]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: this.mainModel

		};


	}

	permissionLab_nodeView() {
		return Object.assign(
			...Object.keys(this.lab_node_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.lab_node_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	componentDidMount(){
		this.getData = setInterval(() => { this.table.filter() }, 300000);
	}

	componentWillUnmount() {
        if (this.getData) {
            clearInterval(this.getData);
        }
    }

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.lab_node_struct} autoload={true}>
					<FuncBar
						left={<FuncHideCol />}
						right={<><FuncAdd /><FuncDel /><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-striped table-resizable'></MainTable>
					<Pagination></Pagination>

				</Table>


			</div>
		);
	}
}

export default Lab_nodeView
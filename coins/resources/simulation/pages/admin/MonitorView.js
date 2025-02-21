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

class MonitorView extends Component {

    constructor(props) {
        super(props);
        this.id = makeId();
        this.table_monitor_struct = {};
        this.table_monitor_struct[STRUCT_FILTERS] = {}
        this.table_monitor_struct[STRUCT_COLUMNS] = {

            'cpu': {
                [COL_NAME]: 'CPU',
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (colId, rowId, data) => {
					// return (<span style={data <= 50 ? { color: 'limegreen' } : { color: 'red' }}>{`${data} %`}</span>)
					var process = data[rowId][colId];
					var total = 100  ;
					var background = 'limegreen';
					if(process > 50) background = 'orange'
					if(process > 80) background = 'red'

					return <div className='box_flex' style={{ minWidth: 200 }}>

						<div className="progress" style={{ flexGrow: 1, border:'solid thin ' + background }}>
							<div className="progress-bar progress-bar-striped active" role="progressbar" style={{ background : background, width: `${process}%` , color: 'black', textShadow: 'white 1px 0px, white -1px 0px, white 0px 1px, white 0px -1px'   }}>
								&nbsp;&nbsp;{`${process} % / ${total} %`}
							</div>
						</div>

					</div>
				},

            },
            'ram': {
                [COL_NAME]: 'RAM',
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (colId, rowId, data) => {
					// return (<span style={data <= 50 ? { color: 'limegreen' } : { color: 'red' }}>{`${data} %`}</span>)
					var process = data[rowId][colId];
					var total = Math.round((data[rowId]['total_ram'] / 1000000) * 10) / 10 ;
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
            'disk': {
                [COL_NAME]: 'Disk',
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (colId, rowId, data) => {
					// return (<span style={data <= 50 ? { color: 'limegreen' } : { color: 'red' }}>{`${data} %`}</span>)
					var process = data[rowId][colId];
					var total = data[rowId]['total_disk']  ;
					var background = 'limegreen';
					if(process > 50) background = 'orange'
					if(process > 80) background = 'red'

					return <div className='box_flex' style={{ minWidth: 200 }}>

						<div className="progress" style={{ flexGrow: 1, border:'solid thin ' + background }}>
							<div className="progress-bar progress-bar-striped active" role="progressbar" style={{ background : background, width: `${process}%` , color: 'black', textShadow: 'white 1px 0px, white -1px 0px, white 0px 1px, white 0px -1px'   }}>
								&nbsp;&nbsp;{`${process} % / ${total} `}
							</div>
						</div>

					</div>
				},

            },
            'swap': {
                [COL_NAME]: 'Swap',
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (colId, rowId, data) => {
					// return (<span style={data <= 50 ? { color: 'limegreen' } : { color: 'red' }}>{`${data} %`}</span>)
					var process = data[rowId][colId];
					var total = Math.round((data[rowId]['total_swap'] / 1000000) * 10) / 10 ;
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


        }
        this.table_monitor_struct[STRUCT_FILTERS] = {

            // 'name': {
            // 	[FILTER_NAME]: 'name',
            // 	[FILTER_TYPE]: 'text',
            // },

        }


        this.table_monitor_struct[STRUCT_EDIT] = {


        }

        this.table_monitor_struct[STRUCT_ROWS] = {

        };
        this.table_monitor_struct[STRUCT_TABLE] = {
            [DATA_TABLE_ID]: '1ass122344',
            [DATA_FILTERS]: {},
            [DATA_HIDDEN_COL]: {},
            [DATA_PERMIT_COL]: this.permissionTableAlertView(),
            [DATA_KEY]: [],
            [DATA_SORT]: {},
            [FLAG_FILTER]: true,
            [FLAG_FILTER_CHANGE]: true,
            [FLAG_MULTI_SORT]: false,
            [FLAG_RESIZABLE]: true,
            [FLAG_SELECT_ROWS]: false,
            [FLAG_SETTING_ROWS]: false,
            [FLAG_EXPAND_ROWS]: false,
            [FLAG_HEAD_ROW]: true,
        };


    }

    permissionTableAlertView() {
        return Object.assign(
            ...Object.keys(this.table_monitor_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
            ...Object.keys(this.table_monitor_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
        )
    }
    async loadOrigin() {
        App.loading(true);
        return axios.request({
            url: '/control/control/getSystemInfo',
            method: 'GET',
        })

            .then(response => {
                App.loading(false);
                
                response = response['data']['data'];
                // console.log(response)
                let result = [response]
                this.table.setOrigin(result)
                // var totalRam = Math.round((response['total_ram'] / 1000000) * 10) / 10;
                // var totalSwap = Math.round((response['total_swap'] / 1000000) * 10) / 10;

                // this.setState({
                //     cpu: `${response['cpu']} `,
                //     ram: `${response['ram']} `,
                //     totalRam: `${totalRam}G`,
                //     swap: `${response['swap']} `,
                //     totalSwap: `${totalSwap}G`,
                //     disk: `${response['disk']}G`,
                //     totalDisk: response['total_disk'],
                // });
            })

            .catch((error) => {
                console.log(error);
                error_handle(error)
                return false;
            })

    }

    componentDidMount() {
        this.loadOrigin()
    }
    render() {
        return (
            <div>
                <Table ref={c => this.table = c} table={this.table_monitor_struct} autoload={false} loadOrigin={this.loadOrigin.bind(this)}>
                    <FuncBar
                        left={<>
                            <div className='box_flex'>
                                <FuncHideCol />
                            </div>
                        </>}
                        right={<>
                            <FuncClear></FuncClear><FuncRefresh /><FuncExport /></>}></FuncBar>
                    <MainTable className='table table-bordered table-striped table-resizable' minHeight={0}></MainTable>
                    <Pagination></Pagination>

                </Table>
            </div>
        );
    }
}

export default MonitorView;
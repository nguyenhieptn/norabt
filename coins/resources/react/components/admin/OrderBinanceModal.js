import React, { Component } from 'react'
import Accounts from '../../model/admin/Accounts';


import Input from '../input/Input';

import Table from '../table/TableStatic'
import MainTable from '../table/MainTable'
import Pagination from '../table/Pagination'
import FuncBar from '../table/FuncBar'

import FuncEditRow from '../table/FuncEditRow'
import FuncAdd from '../table/FuncAdd'
import FuncHideCol from '../table/FuncHideCol'
import FuncDel from '../table/FuncDel'
import FuncClear from '../table/FuncClear'
import FuncRefresh from '../table/FuncRefresh'
import FuncExport from '../table/FuncExport'

class OrderBinanceModal extends Component {

	constructor(props) {
		super(props);
		this.id = makeId();

	

		this.orders_binance_struct = {};
        this.orders_binance_struct[STRUCT_FILTERS] = {}
        this.orders_binance_struct[STRUCT_COLUMNS] = {

         

            [BINANCE_ORDER_BINANCE]: {
                [COL_NAME]: lang(ORDER_BINANCE),
                [COL_SORT]: true,

            },
      
            [BINANCE_ORDER_TIME]: {
                [COL_NAME]: lang(ORDER_TIME),
                [COL_SORT]: true,
                // [COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' },

                [COL_DECORATOR_IN]: (colId, rowId, data) => {

					var rowData = data[rowId];
					var data = rowData[colId];
					if (!data) return '';
					return <div style={{ cursor: 'pointer' }} onClick={() => {
                        this.props.onSelectTime 
                        ? this.props.onSelectTime(rowData[ORDER_SYMBOL], (Math.floor(rowData[ORDER_TIME] / 1000) - 300) * 1000, (Math.floor(rowData[ORDER_TIME] / 1000) + 3000) * 1000)
                        : window.open(App.link('/admin/dashboard/view?symbol=' + rowData[ORDER_SYMBOL]) + "&start=" + (Math.floor(rowData[ORDER_TIME] / 1000) - 300) * 1000 + "&stop=" + (Math.floor(rowData[ORDER_TIME] / 1000) + 3000) * 1000, '_blank');
                    }}><b>{moment(data, 'x').format(DATE_FORMAT)}</b></div>
				}

            },
            [BINANCE_ORDER_SYMBOL]: {
                [COL_NAME]: lang(ORDER_SYMBOL),
                [COL_SORT]: true,

            },

        
            [BINANCE_ORDER_SIDE]: {
                [COL_NAME]: lang(ORDER_SIDE),
                [COL_SORT]: true,

            },
            [BINANCE_ORDER_PRICE]: {
                [COL_NAME]: lang(ORDER_PRICE),
                [COL_SORT]: true,

            },
     
            [BINANCE_ORDER_QTY]: {
                [COL_NAME]: lang(ORDER_QTY),
                [COL_SORT]: true,

            },
            [BINANCE_ORDER_PNL]: {
                [COL_NAME]: lang(ORDER_PNL),
                [COL_SORT]: true,
                [COL_SUM]: true,

            },
            [BINANCE_ORDER_COMMIT]: {
                [COL_NAME]: lang(ORDER_COMMIT),
                [COL_SORT]: true,
                [COL_SUM]: true

            },
     



        }
        this.orders_binance_struct[STRUCT_FILTERS] = {


            [BINANCE_ORDER_BINANCE]: {
                [FILTER_NAME]: lang(ORDER_BINANCE),
                [FILTER_TYPE]: 'text',
            },
       
            [BINANCE_ORDER_TIME]: {
                [FILTER_NAME]: lang(ORDER_TIME),
                [FILTER_TYPE]: 'date',
               
            },
            [BINANCE_ORDER_SYMBOL]: {
                [FILTER_NAME]: lang(ORDER_SYMBOL),
                [FILTER_TYPE]: 'text',
            },

        
            [BINANCE_ORDER_SIDE]: {
                [FILTER_NAME]: lang(ORDER_SIDE),
                [FILTER_TYPE]: 'select',
            },
            [BINANCE_ORDER_PRICE]: {
                [FILTER_NAME]: lang(ORDER_PRICE),
                [FILTER_TYPE]: 'text',
            },
        
         
            [BINANCE_ORDER_QTY]: {
                [FILTER_NAME]: lang(ORDER_QTY),
                [FILTER_TYPE]: 'text',
            },
            [BINANCE_ORDER_PNL]: {
                [FILTER_NAME]: lang(ORDER_PNL),
                [FILTER_TYPE]: 'text',
            },
            [BINANCE_ORDER_COMMIT]: {
                [FILTER_NAME]: lang(ORDER_COMMIT),
                [FILTER_TYPE]: 'text',
            },


        }

        this.orders_binance_struct[STRUCT_EDIT] = {




        }

  
        this.orders_binance_struct[STRUCT_TABLE] = {
        	[DATA_TABLE_ID]: '122',
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionOrdersBinanceView(),
			[DATA_KEY]: ['id'],
			[DATA_SORT]: { [BINANCE_ORDER_ID]: 'desc'},
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

	permissionOrdersBinanceView() {
        return Object.assign(
            ...Object.keys(this.orders_binance_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
            ...Object.keys(this.orders_binance_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
        )
    }

	modal(cmd = 'show') {
		if (cmd == 'hide') {
			$("#bladeModal" + this.id).modal('hide');
		} else {
			$("#bladeModal" + this.id).modal();
		}
	}



	async loadOrigin(data) {
		this.table.setOrigin(data);
	}



	render() {


		return (
			<>
				<div className="modal fade" id={"bladeModal" + this.id}>
					<div className="modal-dialog modal-lg modal-dialog-centered" style={{ minWidth : '1500px'}}>
						<div className="modal-content">

							<div className="modal-header">
								<h4 className="modal-title">Add</h4>
								<button type="button" className="close" data-dismiss="modal">&times;</button>
							</div>

							<div className="modal-body" style={{ textAlign: 'initial' }}>

							<Table ref={c => this.table = c} table={this.orders_binance_struct} autoload={false} loadOrigin={this.loadOrigin.bind(this)}>
									<FuncBar
										left={<>
											<div className='box_flex'>
												<FuncHideCol />
											</div>
										</>}
										right={<><FuncClear></FuncClear><FuncRefresh /><FuncExport /></>}></FuncBar>
									<MainTable className='table table-bordered table-striped table-resizable' minHeight={0}></MainTable>
									<Pagination></Pagination>

								</Table>
								
							</div>

							<div className="modal-footer">

							



								<button type="button" className="btn btn-danger" data-dismiss="modal">Close</button>
							</div>

						</div>
					</div>
				</div>

			</>
		)
	}





}
export default OrderBinanceModal
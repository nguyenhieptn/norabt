import React, { Component } from 'react';


import Input from '../../components/input/Input';

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
import Lab_candle_1m from '../../model/admin/Lab_candle_1m';


class CrawlerYearCheckModal extends Component {
    constructor(props) {
        super(props);
        this.id = makeId();

        this.state = {
            symbols : []
        }

        this.lab_candle_1m_struct = {};
		this.lab_candle_1m_struct[STRUCT_FILTERS] = {}
		this.lab_candle_1m_struct[STRUCT_COLUMNS] = {

			[LAB_CANDLE_1M_TIME]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},
			[LAB_CANDLE_1M_SYMBOL]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_SYMBOL),
				[COL_SORT]: true,

			},
            [LAB_CANDLE_1M_INTERVAL]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_INTERVAL),
				[COL_SORT]: true,
                [COL_DECORATOR_IN]: (data)=>{
                    return <b style={{color:'red'}}>{timeInterval(data - 60000)}</b>
                }
			},
			[LAB_CANDLE_1M_OPEN_TIME]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_OPEN_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},
			[LAB_CANDLE_1M_CLOSE_TIME]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_CLOSE_TIME),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data, 'x').format(DATE_FORMAT) },
				[COL_STYLE]: { whiteSpace: 'nowrap' }
			},
			[LAB_CANDLE_1M_OPEN]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_OPEN),
				[COL_SORT]: true,

			},
			[LAB_CANDLE_1M_CLOSE]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_CLOSE),
				[COL_SORT]: true,

			},
			[LAB_CANDLE_1M_HIGH]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_HIGH),
				[COL_SORT]: true,

			},
			[LAB_CANDLE_1M_LOW]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_LOW),
				[COL_SORT]: true,

			},
			[LAB_CANDLE_1M_TRADES]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_TRADES),
				[COL_SORT]: true,

			},
			[LAB_CANDLE_1M_VOLUME]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_VOLUME),
				[COL_SORT]: true,

			},

			
            
			[LAB_CANDLE_1M_EMA5]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_EMA5),
				[COL_SORT]: true,

			},
			[LAB_CANDLE_1M_EMA9]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_EMA9),
				[COL_SORT]: true,

			},
			[LAB_CANDLE_1M_EMA12]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_EMA12),
				[COL_SORT]: true,

			},
			[LAB_CANDLE_1M_EMA13]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_EMA13),
				[COL_SORT]: true,

			},
			[LAB_CANDLE_1M_EMA26]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_EMA26),
				[COL_SORT]: true,

			},
			[LAB_CANDLE_1M_MACD]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_MACD),
				[COL_SORT]: true,

			},
			[LAB_CANDLE_1M_SIGNAL]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_SIGNAL),
				[COL_SORT]: true,

			},
			[LAB_CANDLE_1M_HISTOGRAM]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_HISTOGRAM),
				[COL_SORT]: true,

			},
			
			[LAB_CANDLE_1M_SIGNAL2]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_SIGNAL2),
				[COL_SORT]: true,

			},
			[LAB_CANDLE_1M_HISTOGRAM2]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_HISTOGRAM2),
				[COL_SORT]: true,

			},
			[LAB_CANDLE_1M_SIGNAL3]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_SIGNAL3),
				[COL_SORT]: true,

			},
			[LAB_CANDLE_1M_HISTOGRAM3]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_HISTOGRAM3),
				[COL_SORT]: true,

			},
			
			[LAB_CANDLE_1M_SIGNAL4]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_SIGNAL4),
				[COL_SORT]: true,

			},
			[LAB_CANDLE_1M_HISTOGRAM4]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_HISTOGRAM4),
				[COL_SORT]: true,

			},
			[LAB_CANDLE_1M_SIGNAL5]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_SIGNAL5),
				[COL_SORT]: true,

			},
			[LAB_CANDLE_1M_HISTOGRAM5]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_HISTOGRAM5),
				[COL_SORT]: true,

			},
			[LAB_CANDLE_1M_SIGNAL6]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_SIGNAL6),
				[COL_SORT]: true,

			},
			[LAB_CANDLE_1M_HISTOGRAM6]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_HISTOGRAM6),
				[COL_SORT]: true,

			},

			[LAB_CANDLE_1M_SIGNAL7]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_SIGNAL7),
				[COL_SORT]: true,

			},
			[LAB_CANDLE_1M_HISTOGRAM7]: {
				[COL_NAME]: lang(LAB_CANDLE_1M_HISTOGRAM7),
				[COL_SORT]: true,

			},

			[LAB_CANDLE_1M_AVGU14]:{
				[COL_NAME]: lang(LAB_CANDLE_1M_AVGU14),
				[COL_SORT]: true,
				
			},
			[LAB_CANDLE_1M_AVGD14]:{
				[COL_NAME]: lang(LAB_CANDLE_1M_AVGD14),
				[COL_SORT]: true,
				
			},
			[LAB_CANDLE_1M_RSI14]:{
				[COL_NAME]: lang(LAB_CANDLE_1M_RSI14),
				[COL_SORT]: true,
				
			},
			[LAB_CANDLE_1M_RSI_EMA9]:{
				[COL_NAME]: lang(LAB_CANDLE_1M_RSI_EMA9),
				[COL_SORT]: true,
				
			},
			[LAB_CANDLE_1M_RSI_EMA5]:{
				[COL_NAME]: lang(LAB_CANDLE_1M_RSI_EMA5),
				[COL_SORT]: true,
				
			},
			[LAB_CANDLE_1M_RSI_EMA4]:{
				[COL_NAME]: lang(LAB_CANDLE_1M_RSI_EMA4),
				[COL_SORT]: true,
				
			},
			[LAB_CANDLE_1M_RSI_WMA]:{
				[COL_NAME]: lang(LAB_CANDLE_1M_RSI_WMA),
				[COL_SORT]: true,
				
			},

			[LAB_CANDLE_1M_STARTPOINT]:{
				[COL_NAME]: lang(LAB_CANDLE_1M_STARTPOINT),
				[COL_SORT]: true,
				
			},



		}

		this.lab_candle_1m_struct[STRUCT_FILTERS] = {
            [LAB_CANDLE_1M_SYMBOL]: {
				[FILTER_NAME]: lang(LAB_CANDLE_1M_SYMBOL),
				[FILTER_TYPE]: 'text',
			},

		}

		this.lab_candle_1m_struct[STRUCT_EDIT] = {

		}

		this.lab_candle_1m_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex' style={{ justifyContent: 'center' }}>
					<FuncEditRow rowData={rowData} />
				</div>
			}
		};

		this.lab_candle_1m_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: LAB_CANDLE_1M_TABLE,
			[DATA_SPECIAL]: { symbol: App.symbol },
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {
                [LAB_CANDLE_1M_EMA5]: true,
                [LAB_CANDLE_1M_EMA9]: true,
                [LAB_CANDLE_1M_EMA12]: true,
                [LAB_CANDLE_1M_EMA13]: true,
                [LAB_CANDLE_1M_EMA26]: true,
                [LAB_CANDLE_1M_MACD]: true,
                [LAB_CANDLE_1M_SIGNAL]: true,
                [LAB_CANDLE_1M_HISTOGRAM]: true,
                [LAB_CANDLE_1M_SIGNAL2]: true,
                [LAB_CANDLE_1M_HISTOGRAM2]: true,
                [LAB_CANDLE_1M_SIGNAL3]: true,
                [LAB_CANDLE_1M_HISTOGRAM3]: true,
                [LAB_CANDLE_1M_SIGNAL4]: true,
                [LAB_CANDLE_1M_HISTOGRAM4]: true,
                [LAB_CANDLE_1M_SIGNAL5]: true,
                [LAB_CANDLE_1M_HISTOGRAM5]: true,
                [LAB_CANDLE_1M_SIGNAL6]: true,
                [LAB_CANDLE_1M_HISTOGRAM6]: true,
                [LAB_CANDLE_1M_SIGNAL7]: true,
                [LAB_CANDLE_1M_HISTOGRAM7]: true,
                [LAB_CANDLE_1M_AVGU14]: true,
                [LAB_CANDLE_1M_AVGD14]: true,
                [LAB_CANDLE_1M_RSI14]: true,
                [LAB_CANDLE_1M_RSI_EMA9]: true,
                [LAB_CANDLE_1M_RSI_EMA5]: true,
                [LAB_CANDLE_1M_RSI_EMA4]: true,
                [LAB_CANDLE_1M_RSI_WMA]: true,
                [LAB_CANDLE_1M_STARTPOINT]: true,
            },
			[DATA_PERMIT_COL]: this.permissionLab_candle_1mView(),
			[DATA_KEY]: [LAB_CANDLE_1M_ID],
			[DATA_SORT]: { [LAB_CANDLE_1M_CLOSE_TIME]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: false,
			[FLAG_SETTING_ROWS]: false,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Lab_candle_1m()

		};
    }

    permissionLab_candle_1mView() {
		return Object.assign(
			...Object.keys(this.lab_candle_1m_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.lab_candle_1m_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}


    modal(cmd = 'show') {
        if (cmd == 'hide') {
            $("#add_row_modal" + this.id).modal('hide');

        } else {
            this.table.setOrigin([]);
            $("#add_row_modal" + this.id).modal();
           
        }
    }

    componentWillUnmount() {
        
    }

    loadOriginTracking() {
        let exchange = this.inputExchange.getValue()
        if(exchange == null) return;
        let dbName = 'coin_'+exchange;
        var m1Model = new Lab_candle_1m()
        m1Model.getMissData(dbName, this.state.symbols).then(res => {
            if(res['result']){
                this.table.setOrigin(res['data']);
            }
        })
        
    }
    

    componentDidMount() {

    }

    render() {

        return (
            <div className="modal fade" id={"add_row_modal" + this.id} onClick={() => { addClass($('body')[0], 'modal-open') }}>
                <div className="modal-dialog modal-lg modal-dialog-centered" style={{ maxWidth: '95%' }}>
                    <div className="modal-content">

                        <div className="modal-header">
                            <h4 className="modal-title">{lang("Check data")}</h4>
                            <button type="button" className="close" data-dismiss="modal">&times;</button>
                        </div>

                        <div className="modal-body" >
                            
                            <div style={{ display: 'flex', marginLeft: '3px' }}>
                                
                                <div style={{ display: 'flex ', alignItems: 'center', marginRight: '20px' }}>
                                    <span style={{ marginRight: '10px' }}>Exchange : </span>
                                    <Input ref={c => this.inputExchange = c} className='input' struct={{
                                        [INPUT_TYPE]: 'select',
                                        [INPUT_NULL]: false,
                                        [INPUT_OPTION]: {
                                            'future': 'future',
                                            'spot': 'spot',
                                        },
                                        [INPUT_DEFAULT]: 'future'
                                    }}></Input>
                                </div>

                                <div className='button btn btn-primary' onClick={()=>{
                                    this.loadOriginTracking()
                                }}>Check</div>


                            </div>

                            <div>Symbols: <b>{this.state.symbols.join(', ')}</b></div>

                            <Table ref={c => this.table = c} table={this.lab_candle_1m_struct} autoload={false} loadOrigin={this.loadOriginTracking.bind(this)}>
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

                        <div className="modal-footer">
                            <button type="button" className="btn btn-danger" data-dismiss="modal">{lang('Close')}</button>
                        </div>
                    </div>
                </div>
            </div>
        );
    }
}

export default CrawlerYearCheckModal;
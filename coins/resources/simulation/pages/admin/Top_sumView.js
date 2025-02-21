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

import Top_summary from '../../model/admin/Top_Sum'
import AddressBTCModal from '../../components/admin/AddressBTCModal'

class Top_sumView extends Component {
    constructor(props) {
        super(props);

        this.top_summary_struct = {};
        this.top_summary_struct[STRUCT_FILTERS] = {}
        this.top_summary_struct[STRUCT_COLUMNS] = {

            [TOP_SUM_TIME]: {
                [COL_NAME]: lang(TOP_SUM_TIME),
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => { if (data == '') return data; else return moment(data - 86400000 *2, 'x').format(DATE_FORMAT) },

            },
            [TOP_SUM_BALANCE]: {
                [COL_NAME]: lang(TOP_SUM_BALANCE),
                [COL_SORT]: true,
                [COL_STYLE]: { textAlign: 'center' },
                [COL_DECORATOR_IN]: (data) => {

					return <span>{`${formatNumber(data)} BTC`}</span>;
				},
            },
            [TOP_SUM_IN]: {
                [COL_NAME]: lang(TOP_SUM_IN),
                [COL_SORT]: true,
                [COL_STYLE]: { textAlign: 'center' },
                [COL_DECORATOR_IN]: (data) => {

					return <span>{`${formatNumber(data)} BTC`}</span>;
				},

            },
            [TOP_SUM_OUT]: {
                [COL_NAME]: lang(TOP_SUM_OUT),
                [COL_SORT]: true,
                [COL_STYLE]: { textAlign: 'center' },
                [COL_DECORATOR_IN]: (data) => {

					return <span>{`${formatNumber(data)} BTC`}</span>;
				},

            },
           
            [TOP_SUM_NEW_IN]: {
                [COL_NAME]: lang(TOP_SUM_NEW_IN),
                [COL_SORT]: true,
                [COL_STYLE]: { textAlign: 'center' },
                [COL_DECORATOR_IN]: (data) => {
                    if(!data) return
					return <span>{`${formatNumber(data)} BTC`}</span>;
				},
            },
            [TOP_SUM_OUTED]: {
                [COL_NAME]: lang(TOP_SUM_OUTED),
                [COL_SORT]: true,
                [COL_STYLE]: { textAlign: 'center' },
                [COL_DECORATOR_IN]: (data) => {
                    if(!data) return
                    data = -data;
					return <span>{`${formatNumber(data)} BTC`}</span>;
				},
            },
            [TOP_SUM_ADDRESS_IN]: {
                [COL_NAME]: lang(TOP_SUM_ADDRESS_IN),
                [COL_SORT]: false,
                [COL_DECORATOR_IN]: (data) => {

					return <button type="button" className="btn btn-info" onClick={() => {

						this.AddressBTCModal.modal();
						this.AddressBTCModal.setValue(data , 'Address In');
					}}>Info</button>;
				},
				[COL_STYLE]: { textAlign: 'center' },


            },
            
            [TOP_SUM_ADDRESS_OUTED]: {
                [COL_NAME]: lang(TOP_SUM_ADDRESS_OUTED),
                [COL_SORT]: false,
                [COL_DECORATOR_IN]: (data) => {

					return <button type="button" className="btn btn-info" onClick={() => {

						this.AddressBTCModal.modal();
						this.AddressBTCModal.setValue(data , 'Address Out');
					}}>Info</button>;
				},
				[COL_STYLE]: { textAlign: 'center' },


            },
            [TOP_SUM_CHANGE_COUNT]: {
                [COL_NAME]: lang(TOP_SUM_CHANGE_COUNT),
                [COL_SORT]: true,
                [COL_STYLE]: { textAlign: 'center' },
                [COL_DECORATOR_IN]: (data) => {
                    if(!data) return
					return <span>{`${formatNumber(data)} `}</span>;
				},
            },



        }
        this.top_summary_struct[STRUCT_FILTERS] = {


            [TOP_SUM_IN]: {
                [FILTER_NAME]: lang(TOP_SUM_IN),
                 [FILTER_TYPE]: 'number',
                [FILTER_LOGIC]: ['>=', '<='],
            },
            [TOP_SUM_OUT]: {
                [FILTER_NAME]: lang(TOP_SUM_OUT),
                 [FILTER_TYPE]: 'number',
                [FILTER_LOGIC]: ['>=', '<='],
            },
            [TOP_SUM_BALANCE]: {
                [FILTER_NAME]: lang(TOP_SUM_BALANCE),
                 [FILTER_TYPE]: 'number',
                [FILTER_LOGIC]: ['>=', '<='],
            },
            [TOP_SUM_NEW_IN]: {
                [FILTER_NAME]: lang(TOP_SUM_NEW_IN),
                 [FILTER_TYPE]: 'number',
                [FILTER_LOGIC]: ['>=', '<='],
            },
            [TOP_SUM_OUTED]: {
                [FILTER_NAME]: lang(TOP_SUM_OUTED),
                 [FILTER_TYPE]: 'number',
                [FILTER_LOGIC]: ['>=', '<='],
            },
            [TOP_SUM_CHANGE_COUNT]: {
                [FILTER_NAME]: lang(TOP_SUM_CHANGE_COUNT),
                [FILTER_TYPE]: 'text',
            },


        }

        this.top_summary_struct[STRUCT_EDIT] = {

    


        }

        this.top_summary_struct[STRUCT_ROWS] = {
            [ROW_FUNCS]: (rowData) => {
                return <div className='box_flex' style={{ justifyContent: 'center' }}>
                    <FuncEditRow rowData={rowData} />
                </div>
            }
        };
        this.top_summary_struct[STRUCT_TABLE] = {
            [DATA_TABLE_ID]: TOP_SUMMARY_TABLE,
            [DATA_FILTERS]: {},
            [DATA_HIDDEN_COL]: {},
            [DATA_PERMIT_COL]: this.permissionTop_summaryView(),
            [DATA_KEY]: [TOP_SUM_ID],
            [DATA_SORT]: { [TOP_SUM_ID]: 'desc' },
            [FLAG_FILTER]: true,
            [FLAG_FILTER_CHANGE]: true,
            [FLAG_MULTI_SORT]: false,
            [FLAG_RESIZABLE]: true,
            [FLAG_SELECT_ROWS]: false,
            [FLAG_SETTING_ROWS]: false,
            [FLAG_EXPAND_ROWS]: false,
            [FLAG_HEAD_ROW]: true,

            model: new Top_summary()

        };


    }

    permissionTop_summaryView() {
        return Object.assign(
            ...Object.keys(this.top_summary_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
            ...Object.keys(this.top_summary_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
        )
    }

    render() {
        return (
            <div>
                <Table ref={c => this.table = c} table={this.top_summary_struct} autoload={true}>
                    <FuncBar
                        left={<FuncHideCol />}
                        right={<><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
                    <MainTable className='table table-bordered table-striped table-resizable'></MainTable>
                    <Pagination></Pagination>

                </Table>

                <AddressBTCModal  ref={c => this.AddressBTCModal = c}></AddressBTCModal>


            </div>
        );
    }
}

export default Top_sumView;
import React, { Component } from 'react'
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

import Candle_24h from '../../model/admin/Candle_24h'
import Finance from '../../model/admin/Finance'
import Input from '../../components/input/Input'
import VolumeAlertModal from '../../components/analytics/VolumeAlertModal'

class Finance24hView extends Component {

    constructor(props) {
        super(props);

        this.finance_24h_struct = {};
        this.finance_24h_struct[STRUCT_FILTERS] = {}
        this.finance_24h_struct[STRUCT_COLUMNS] = {

            [FINANCE_NAME]: {
                [COL_NAME]: 'Stock',
                [COL_SORT]: true,
            },
        
        }
        this.finance_24h_struct[STRUCT_FILTERS] = {

            [FINANCE_NAME]: {
                [FILTER_NAME]: lang(FINANCE_NAME),
                [FILTER_TYPE]: 'text',
            },
        }

        this.finance_24h_struct[STRUCT_EDIT] = {


        }

        this.finance_24h_struct[STRUCT_ROWS] = {
            // [ROW_FUNCS]: (rowData) => {
            //     return <div className='box_flex' style={{ justifyContent: 'center' }}>
            //         <FuncEditRow rowData={rowData} />
            //     </div>
            // }
        };
        this.finance_24h_struct[STRUCT_TABLE] = {
            [DATA_TABLE_ID]: FINANCE_TABLE,
            [DATA_FILTERS]: {},
            [DATA_HIDDEN_COL]: {},
            [DATA_PERMIT_COL]: this.permissionFinance_24hView(),
            [DATA_KEY]: [FINANCE_ID],
            [DATA_SORT]: { [moment.utc().startOf('day').format('x')]: 'desc' },
            [FLAG_FILTER]: true,
            [FLAG_FILTER_CHANGE]: true,
            [FLAG_MULTI_SORT]: false,
            [FLAG_RESIZABLE]: true,
            [FLAG_SELECT_ROWS]: true,
            [FLAG_SETTING_ROWS]: false,
            [FLAG_EXPAND_ROWS]: false,
            [FLAG_HEAD_ROW]: true,

            // model: new Candle_24h()
            model: new Finance()

        };


    }

    permissionFinance_24hView() {
        return Object.assign(
            ...Object.keys(this.finance_24h_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
            ...Object.keys(this.finance_24h_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
        )
    }

    componentDidMount() {
        this.loadOrigin();
    }


    async loadOrigin() {
        var startDate = Number(this.startDate.getValue());
        var endDate = Number(this.endDate.getValue());

      

        var model = new Finance();

        var dates = [startDate];

        var t = startDate;
        while (t < endDate) {
            t += 86400000;
            dates.push(t);
        }
 

        var structColumn = {

            [FINANCE_NAME]: {
                [COL_NAME]: 'Stock',
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => {

                    return <b>{data}</b>
                }

            },

         

        }

        for (let i = dates.length - 1; i >= 0; i--) {
            structColumn[dates[i]] = {
                [COL_NAME]: moment(dates[i], 'x').format('DD/MM/YYYY'),
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: data => {
                    if(!isset(data)) return 0;
                    if (data == 0) {
                        return `0 %`;
                    } else if (data > 0) {
                        return <span style={{ color: '#137333' }}>{`+ ${Math.round(data * 1000) / 1000} %`}</span>;
                    } else {
                        return <span style={{ color: 'red' }}>{`- ${Math.round(-data * 1000) / 1000} %`}</span>;
                    }
                }
            }

            this.table[STRUCT_TABLE][DATA_PERMIT_COL][dates[i]] = 'read';
        }

        this.table[STRUCT_COLUMNS] = structColumn;

        var tableData = {};
        
        for (let i in dates) {
            
            var startDate ;
      
            startDate = dates[i]  + 86400000 - 1;

          
            var dateData = await model.get([[  [FINANCE_CLOSE_TIME, '=', startDate] ]]);
            if (dateData['result']) {
                dateData = dateData['data'];

                for (let j in dateData) {
                    var data = dateData[j];
                    var sym = data[FINANCE_NAME];
                    if (!isset(tableData[sym])) tableData[sym] = { [FINANCE_NAME]: sym };
                    tableData[sym][dates[i]] = get(data[FINANCE_PERCENT], 0);
                }
            }
        }


        this.table.setOrigin(Object.values(tableData));


    }

    render() {
        return (
            <div>
                <Table ref={c => this.table = c} table={this.finance_24h_struct} autoload={false} loadOrigin={this.loadOrigin.bind(this)}>
                    <FuncBar
                        left={<>
                            <div className='box_flex'>
                                <FuncHideCol />

                                {/* <div className='button btn btn-sm btn-warning' onClick={() => {
                                    this.vlAlertModal.modal()
                                }}><i className="fa fa-bell-o"></i>&nbsp;Alert</div> */}

                                <Input className='input' placeholder='Start Time' ref={c => this.startDate = c} struct={{
                                    [INPUT_TYPE]: 'date',
                                    [INPUT_FORMAT]: 'DD/MM/YYYY',
                                    [INPUT_DEFAULT]: moment().subtract(1, 'weeks').format('DD/MM/YYYY'),
                                    [INPUT_DECORATOR_IN]: data => data,
                                    [INPUT_DECORATOR_OUT]: (data) => moment.utc(data, 'DD/MM/YYYY').format('x'),
                                    [INPUT_ONCHANGE_BLUR]: () => { this.loadOrigin() }
                                }}></Input>&nbsp;
                                <Input className='input' placeholder='Stop Time' ref={c => this.endDate = c} struct={{
                                    [INPUT_TYPE]: 'date',
                                    [INPUT_FORMAT]: 'DD/MM/YYYY',
                                    [INPUT_DEFAULT]: moment().format('DD/MM/YYYY'),
                                    [INPUT_DECORATOR_IN]: data => data,
                                    [INPUT_DECORATOR_OUT]: (data) => moment.utc(data, 'DD/MM/YYYY').format('x'),
                                    [INPUT_ONCHANGE_BLUR]: () => { this.loadOrigin() }
                                }}></Input>
                            </div>
                        </>}
                        name={'Stock tracking'}
                        right={<><FuncClear></FuncClear><FuncRefresh /><FuncExport /></>}></FuncBar>
                    <MainTable className='table table-bordered table-striped table-resizable' minHeight={0}></MainTable>
                    <Pagination></Pagination>

                </Table>


                <VolumeAlertModal ref={c => this.vlAlertModal = c}></VolumeAlertModal>


            </div>
        );
    }
}

export default Finance24hView
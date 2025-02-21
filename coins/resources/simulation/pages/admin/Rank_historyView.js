import React, { Component } from 'react';
import Input from '../../components/input/Input'

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


class Rank_historyView extends Component {

    constructor(props) {
        super(props);
        this.state = {
            check : false
        }
        this.id = makeId();
        this.table_coinmaket_history = {};
        this.table_coinmaket_history[STRUCT_FILTERS] = {}
        this.table_coinmaket_history[STRUCT_COLUMNS] = {

            'symbol': {
                [COL_NAME]: 'Symbol',
                [COL_SORT]: true,
                [COL_STYLE] : {textAlign : 'center'}

            },
            'service': {
                [COL_NAME]: 'Crawler service',
                [COL_DECORATOR_IN]: data => {
					return data ? <div style={{ color: '#00e209', fontWeight: 'bold', textAlign: 'center' }}>Running</div> : <div style={{ color: 'red', fontWeight: 'bold', textAlign: 'center' }}>Stopped</div>
				}

            },
            'coin_spot': {
                [COL_NAME]: 'Spot',
                [COL_DECORATOR_IN]: data => {
					return data ? <div style={{ color: '#00e209', fontWeight: 'bold', textAlign: 'center' }}>Data  available</div> : <div style={{ color: 'red', fontWeight: 'bold', textAlign: 'center' }}>No data yet</div>
				}

            },
            'coin_future': {
                [COL_NAME]: 'Future',
                [COL_DECORATOR_IN]: data => {
					return data ? <div style={{ color: '#00e209', fontWeight: 'bold', textAlign: 'center' }}>Data  available</div> : <div style={{ color: 'red', fontWeight: 'bold', textAlign: 'center' }}>No data yet</div>
				}

            },

        }
        this.table_coinmaket_history[STRUCT_FILTERS] = {

        }


        this.table_coinmaket_history[STRUCT_EDIT] = {


        }

        this.table_coinmaket_history[STRUCT_ROWS] = {

        };
        this.table_coinmaket_history[STRUCT_TABLE] = {
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
            ...Object.keys(this.table_coinmaket_history[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
            ...Object.keys(this.table_coinmaket_history[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
        )
    }


     loadOrigin(data) {
        this.table.setOrigin(data);

    }

    OnFilter() {

        var Year = this.inputYear.getValue();
        var Rank = this.inputRank.getValue();
        if (Rank !== '' ) {
            this.setState({
                check : false
            });
            App.loading(true);
            axios.request({
                url: `/admin/rank_history/getByRank?year=${Year}&rank=${Rank}`,
                method: 'GET',
            })
                .then(response => {
                    App.loading(false);
                    response = response['data']['data'];
                    // var data = [];
                    // Object.values(response).map(item => {
                    //     data.push({
                    //         symbol : item
                    //     })
                    // })

                    this.loadOrigin(response)
                   
                })
    
                .catch((error) => {
                    App.loading(false);
                    console.log(error);
                    error_handle(error)
                })
        }else{
            this.setState({
                check : true
            });
        }
    }
    render() {
        return (
            <>


                <div style={{ display: 'flex' }}>
                    <Input style={{ marginRight: '10px' }} ref={c => this.inputYear = c} className='input' struct={{
                        [INPUT_TYPE]: 'select',
                        [INPUT_NULL]: true,
                        [INPUT_OPTION]: {
                            '2013': '2013',
                            '2014': '2014',
                            '2015': '2015',
                            '2016': '2016',
                            '2017': '2017',
                            '2018': '2018',
                            '2019': '2019',
                            '2020': '2020',
                            '2021': '2021',
                            '2022': '2022',
                        },
                        [INPUT_DEFAULT] : '2013'
                    }}></Input>

                    <Input placeholder="Rank"  style={this.state.check ? { marginRight: '10px' , border : '1px solid red' } : {marginRight: '10px'}} ref={c => this.inputRank = c} className='input' struct={{
                        [INPUT_TYPE]: 'text',
                        [INPUT_NULL]: true,
                       
                    }}></Input>

                    <button type="button" className="btn btn-outline-primary btn-sm" onClick={() => this.OnFilter()}>Filter</button>
                </div>

                <Table ref={c => this.table = c} table={this.table_coinmaket_history} autoload={false} loadOrigin={this.loadOrigin.bind(this)}>
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
            </>

        );
    }
}

export default Rank_historyView;
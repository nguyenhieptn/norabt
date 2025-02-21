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
import Input from '../../components/input/Input'
import VolumeAlertModal from '../../components/analytics/VolumeAlertModal'
import Coinmarket from '../../model/admin/Coinmarket'
import Watchlist from '../../model/admin/Watchlist'
class Candle_24hView extends Component {

    constructor(props) {
        super(props);

        this.candle_24h_struct = {};
        this.candle_24h_struct[STRUCT_FILTERS] = {}
        this.candle_24h_struct[STRUCT_COLUMNS] = {

            [CANDLE_24H_SYMBOL]: {
                [COL_NAME]: lang(CANDLE_24H_SYMBOL),
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => {
                    var rankData = (data == '1000SHIBUSDT' ? 'SHIBUSDT' : data);
                    var img = this.watchlistIcon[data];
                    if (img == undefined) {
                        img = '/assets/img/Eicon.png'
                        // img = img = this.watchlistIcon['BTCUSDT']
                    }
                    return <b>
                        <img style={{ width: '20px', height: '20px', marginRight: '10px' }} src={img}></img>
                        {data}
                        <span style={{ color: 'blue', fontWeight: 'normal' }}> [{get(this.coinMarketData[rankData], '')}]</span>
                    </b>
                }

            },
            'rank': {
                [COL_NAME]: 'Rank',
                [COL_SORT]: true,

            },

        }
        this.candle_24h_struct[STRUCT_FILTERS] = {

            [CANDLE_24H_SYMBOL]: {
                [FILTER_NAME]: lang(CANDLE_24H_SYMBOL),
                [FILTER_TYPE]: 'text',
            },
        }

        this.candle_24h_struct[STRUCT_EDIT] = {


        }

        this.candle_24h_struct[STRUCT_ROWS] = {
            [ROW_FUNCS]: (rowData) => {
                return <div className='box_flex' style={{ justifyContent: 'center' }}>
                    <FuncEditRow rowData={rowData} />
                </div>
            }
        };
        this.candle_24h_struct[STRUCT_TABLE] = {
            [DATA_TABLE_ID]: CANDLE_24H_TABLE,
            [DATA_FILTERS]: {},
            [DATA_HIDDEN_COL]: {},
            [DATA_PERMIT_COL]: this.permissionCandle_24hView(),
            [DATA_KEY]: [CANDLE_24H_ID],
            [DATA_SORT]: { [moment.utc().startOf('day').format('x')]: 'desc' },
            [FLAG_FILTER]: true,
            [FLAG_FILTER_CHANGE]: true,
            [FLAG_MULTI_SORT]: false,
            [FLAG_RESIZABLE]: true,
            [FLAG_SELECT_ROWS]: true,
            [FLAG_SETTING_ROWS]: false,
            [FLAG_EXPAND_ROWS]: false,
            [FLAG_HEAD_ROW]: true,

            model: new Candle_24h()

        };

        this.coinMarketModel = new Coinmarket();
        this.watchlistIcon = {};


    }

    permissionCandle_24hView() {
        return Object.assign(
            ...Object.keys(this.candle_24h_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
            ...Object.keys(this.candle_24h_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
        )
    }
    getIcon() {
        var watchlist = new Watchlist();

        return watchlist.getIcon();

    }

    componentDidMount() {

        this.getIcon().then(res => {
            this.watchlistIcon = res;
            this.loadOrigin();
        });

    }




    async loadOrigin() {
        var startDate = Number(this.startDate.getValue());
        var endDate = Number(this.endDate.getValue());

        var model = new Candle_24h();

        var dates = [startDate];

        var t = startDate;
        while (t < endDate) {
            t += 86400000;
            dates.push(t);
        }
        this.coinMarketData = await this.coinMarketModel.getRank();


        var structColumn = {

            [CANDLE_24H_SYMBOL]: {
                [COL_NAME]: lang(CANDLE_24H_SYMBOL),
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: (data) => {
                    var rankData = (data == '1000SHIBUSDT' ? 'SHIBUSDT' : data);
                    var img = this.watchlistIcon[data];
                    if (img == undefined) {
                        img = '/assets/img/Eicon.png'
                        // img = img = this.watchlistIcon['BTCUSDT']
                    }
                    return <b>
                        <img style={{ width: '20px', height: '20px', marginRight: '10px' }} src={img}></img>
                        {data}
                        <span style={{ color: 'blue', fontWeight: 'normal' }}> [{get(this.coinMarketData[rankData], '')}]</span>
                    </b>
                }

            },
            'rank': {
                [COL_NAME]: 'Rank',
                [COL_SORT]: true,

            },


        }

        for (let i = dates.length - 1; i >= 0; i--) {
            structColumn[dates[i]] = {
                [COL_NAME]: moment(dates[i], 'x').format('DD/MM/YYYY'),
                [COL_SORT]: true,
                [COL_DECORATOR_IN]: data => formatNumber(Math.round(data))
            }

            this.table[STRUCT_TABLE][DATA_PERMIT_COL][dates[i]] = 'read';
        }

        this.table[STRUCT_COLUMNS] = structColumn;

        var tableData = {};

        for (let i in dates) {
            var dateData = await model.read({ [CANDLE_24H_DATE]: dates[i] });
            if (dateData['result']) {
                dateData = dateData['data'];

                for (let j in dateData) {
                    var data = dateData[j];
                    var sym = data[CANDLE_24H_SYMBOL];
                    if (!isset(tableData[sym])) tableData[sym] = { [CANDLE_24H_SYMBOL]: sym };
                    tableData[sym][dates[i]] = get(data[CANDLE_24H_VOLUME_USDT], 0);

                    if( sym == '1000SHIBUSDT'){
                        tableData['1000SHIBUSDT']['rank'] =  get(this.coinMarketData['SHIBUSDT'], '')
                    }else{
                        tableData[sym]['rank'] =  get(this.coinMarketData[sym], '')
                    } 
                
                   
                }
            }
        }


        // console.log(tableData)


        this.table.setOrigin(Object.values(tableData));


    }

    render() {
        return (
            <div>
                <Table ref={c => this.table = c} table={this.candle_24h_struct} autoload={false} loadOrigin={this.loadOrigin.bind(this)}>
                    <FuncBar
                        left={<>
                            <div className='box_flex'>
                                <FuncHideCol />

                                <div className='button btn btn-sm btn-warning' onClick={() => {
                                    this.vlAlertModal.modal()
                                }}><i className="fa fa-bell-o"></i>&nbsp;Alert</div>

                                <Input className='input' placeholder='Start Time' ref={c => this.startDate = c} struct={{
                                    [INPUT_TYPE]: 'date',
                                    [INPUT_FORMAT]: 'DD/MM/YYYY',
                                    [INPUT_DEFAULT]: moment().subtract(2, 'weeks').format('DD/MM/YYYY'),
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
                        name={'Volume tracking'}
                        right={<><FuncClear></FuncClear><FuncRefresh /><FuncExport /></>}></FuncBar>
                    <MainTable className='table table-bordered table-striped table-resizable' minHeight={0}></MainTable>
                    <Pagination></Pagination>

                </Table>


                <VolumeAlertModal ref={c => this.vlAlertModal = c}></VolumeAlertModal>


            </div>
        );
    }
}

export default Candle_24hView
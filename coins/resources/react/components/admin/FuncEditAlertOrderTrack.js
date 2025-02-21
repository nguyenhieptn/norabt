import React, { Component } from 'react';
import Watchlist from '../../model/admin/Watchlist';

import Ctrl from '../../model/control/Ctrl'

class FuncEditAlertOrderTrack extends Component {
    constructor(props) {
        super(props);
        this.id = makeId();
        this.state = {
            config: [

            ],
            column: [
                ORDER_TRACK_SYMBOL,
                ORDER_TRACK_PRICE,
                ORDER_TRACK_LOW,
                ORDER_TRACK_HIGH,
               
                ORDER_TRACK_CLOSE,
                ORDER_TRACK_CHANGE,
                ORDER_TRACK_1D_UP,
                ORDER_TRACK_1D_DOWN,
                ORDER_TRACK_UP,
                ORDER_TRACK_DOWN,
                ORDER_TRACK_1H_UP,
                ORDER_TRACK_1H_DOWN,
                ORDER_TRACK_15M_UP,
                ORDER_TRACK_15M_DOWN,
                ORDER_TRACK_3M_UP,
                ORDER_TRACK_3M_DOWN,
                ORDER_TRACK_RSI4H_0,
                ORDER_TRACK_RSI4H_1,
                ORDER_TRACK_RSI1H_0,
                ORDER_TRACK_RSI1H_1,
                ORDER_TRACK_RSI_EMA9,
                ORDER_TRACK_1D_RSI_WMA,
                ORDER_TRACK_1W_RSI_WMA,
            ],
            icon: ['', '↗️', '↘️', '✅', '⛔️', '⏹', '🚫', '🤝', '🕒', '⚠️'],
            symbols: {}
        }
    }

    setData(config , rowData){
        console.log(rowData);
       this.setState({
           config,
           rowData
       });
    }
    modal(cmd = 'show') {
        if (cmd == 'hide') {
            $("#add_row_modal" + this.id).modal('hide');
        } else {
            $("#add_row_modal" + this.id).modal();
        }
    }
    componentDidMount(){
        var wlModel = new Watchlist();
        wlModel.getWatchlist().then(res => {
            this.setState({symbols: res})
        })
    }

    saveData() {
        var ctrl = new Ctrl();
        ctrl.set({ 'alarm_configuration': JSON.stringify(this.state.config) }).then(res => {
            this.props.reload();
            this.reloadAlertService();
            if (res['result']) this.modal('hide');
        });
    }


    reloadAlertService() {
        App.loading(true);
        return axios.request({
            url: '/admin/order_track/reloadAlert',
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


    
    render() {
        var config = this.state.config;
        return (
            <div className="modal fade" id={"add_row_modal" + this.id} onClick={() => { addClass($('body')[0], 'modal-open') }}>
            <div className="modal-dialog modal-lg modal-dialog-centered" style={{ maxWidth: '95%' }}>
                <div className="modal-content">

                    <div className="modal-header">
                        <h4 className="modal-title">{get(this.props.title, lang("Alert Configuration"))}</h4>
                        <button type="button" className="close" data-dismiss="modal">&times;</button>
                    </div>

                    <div className="modal-body" style={{ padding: 15 }}>

                        {config.map((item, cfgIndex) => {
                            var conditions = item.condition;
                            return <div key={item.id} className='box_border' 
                                        style={item.id == this.state.rowData.id ? {marginBottom: 10, borderRadius: 5, background: 'antiquewhite' } : {display : 'none' , visibility : 'hidden' }}
                                    >

                                <div className='box_flex button' style={{ padding: 5, margin: 5 }} onClick={()=>{
                                    item.expand = (item.expand == 1 ? 0 : 1);
                                    this.setState({ config });
                                }}>

                                    <i className={item.expand == 1 ? "fa fa-caret-down": "fa fa-caret-right"} style={{marginRight:15}}></i>
                                    <div><b>{item.name}</b></div>

                                    {/* <i style={{margin: 'auto 0px auto auto'}} className='close button' onClick={() => {
                                        config.splice(cfgIndex, 1);
                                        this.setState({ config });
                                    }}>×</i> */}

                                </div>


                                <div style={{display:'block', borderTop:'solid thin darkgray'}}>

                                    <div className='box_flex' style={{ padding: 5, margin: 5 }}>
                                        <div style={{ flex: 1 }}>Name:</div>
                                        <input style={{ flex: 2 }} placeholder="Name" className='input' value={item.name} onChange={(e) => {
                                            item.name = e.target.value;
                                            this.setState({ config });
                                        }}></input>
                                    </div>

                                    <div className='box_flex' style={{ padding: 5, margin: 5 }}>
                                        <div style={{ flex: 1 }}>BOT ID:</div>
                                        <input style={{ flex: 2 }} placeholder="BOT ID" className='input' value={item.bot} onChange={(e) => {
                                            item.bot = e.target.value;
                                            this.setState({ config });
                                        }}></input>
                                    </div>

                                    <div className='box_flex' style={{ padding: 5, margin: 5 }}>
                                        <div style={{ flex: 1 }}>Group ID:</div>
                                        <input style={{ flex: 2 }} placeholder="Group ID" className='input' value={item.group} onChange={(e) => {
                                            item.group = e.target.value;
                                            this.setState({ config });
                                        }}></input>
                                    </div>

                                    <div className='box_flex' style={{ padding: 5, margin: 5 }}>
                                        <div style={{ flex: 1 }}>Icon:</div>
                                        <select style={{ flex: 2 }} className='input' value={item.icon} onChange={(e) => { item.icon = e.target.value; this.setState({ config }) }}>
                                            {this.state.icon.map(icon => {
                                                return <option key={icon} value={icon}>{icon}</option>
                                            })}
                                        </select>
                                    </div>

                                    <div className='box_flex' style={{ padding: 5, margin: 5 }}>
                                        <div style={{ flex: 1 }}>Active:</div>
                                        <select style={{ flex: 2 }} className='input' value={item.active} onChange={(e) => {
                                            item.active = e.target.value;
                                            this.setState({ config });
                                        }}>
                                            <option value={1}>Active</option>
                                            <option value={0}>Disable</option>
                                        </select>
                                    </div>

                                    <div className='box_flex' style={{ padding: 5, margin: 5 }}>
                                        <div style={{ flex: 1 }}>Content:</div>
                                        <textarea style={{ flex: 2 }} placeholder="Content" className='input' value={item.content} onChange={(e) => {
                                            item.content = e.target.value;
                                            this.setState({ config });
                                        }}></textarea>
                                    </div>

                                    <div className='box_flex' style={{ padding: 5, margin: 5 }}>
                                            <div style={{ flex: 1 }}>Note:</div>
                                            <textarea style={{ flex: 2 }} placeholder="Note" className='input' value={item.note} onChange={(e) => {
                                                item.note = e.target.value;
                                                this.setState({ config });
                                            }}></textarea>
                                        </div>

                                    <div className='box_flex' style={{ padding: 5, margin: 5 }}>
                                        <div style={{ flex: 1 }}>Conditions (AND):</div>
                                        <div style={{ flex: 1 }}><div className='button btn btn-sm btn-primary' onClick={() => {
                                            conditions.push({
                                                id: makeId(),
                                                column: '',
                                                logic: '',
                                                value: '',
                                            });
                                            this.setState({ config })
                                        }}>Add Condition</div></div>

                                    </div>

                                    {conditions.map((condition, conIndex) => {

                                        return <div key={condition.id} className='box_flex box_border' style={{ padding: 5, margin: 5, borderRadius: 5, background: 'white' }}>
                                            <div style={{ flex: 1, margin: 5 }}><div className='button btn btn-sm btn-danger' onClick={() => {
                                                conditions.splice(conIndex, 1);
                                                this.setState({ config });
                                            }}>Delete</div></div>

                                            <div style={{ flex: 5, margin: 5 }}>
                                                <select className='input' style={{ width: '100%' }} value={condition.column} onChange={e => {
                                                    condition.column = e.target.value;
                                                    this.setState({ config });
                                                }}>
                                                    <option value=''>{lang('Select Column')}</option>
                                                    <option value='fear'>{lang('Crypto Fear & Greed')}</option>
                                                    {this.state.column.map(col => {
                                                        return <option key={col} value={col}>{lang(col)}</option>
                                                    })}
                                                    <option value="candle_4h_rsi_wma">RSI WMA45 4h</option>
                                                    <option value="candle_4h_signal">SIGNAL 4h</option>
                                                    <option value="candle_1d_signal">SIGNAL 1D</option>
                                                </select>
                                            </div>

                                            <div style={{ flex: 5, margin: 5 }}>
                                                <select className='input' style={{ width: '100%' }} value={condition.symbol} onChange={e => {
                                                    condition.symbol = e.target.value;
                                                    this.setState({ config });
                                                }}>
                                                    <option value=''>{lang('Any Symbol')}</option>
                                                    {Object.keys(this.state.symbols).map(sym => {
                                                        return <option key={sym} value={sym}>{sym}</option>
                                                    })}
                                                </select>
                                            </div>

                                            <div style={{ flex: 5, margin: 5 }}>
                                                <select className='input' style={{ width: '100%' }} value={condition.logic} onChange={e => {
                                                    condition.logic = e.target.value;
                                                    this.setState({ config });
                                                }}>
                                                    <option value="">Select Logic</option>
                                                    {['>', '<', '=', '>=', '<='].map(col => {
                                                        return <option key={col}>{col}</option>
                                                    })}
                                                </select>
                                            </div>

                                            <div style={{ flex: 5, margin: 5 }}>
                                                <input className='input' style={{ width: '100%' }} placeholder="Thresold" type='text' value={condition.value} onChange={e => {
                                                    condition.value = e.target.value;
                                                    this.setState({ config });
                                                }}></input>
                                            </div>

                                        </div>
                                    })}

                                </div>

                            </div>
                        })}

                        {/* <div className='box_flex' style={{ marginBottom: 15, justifyContent: 'center' }}>
                            <div className='button btn btn-sm btn-primary' onClick={() => {
                                config.push({
                                    id: makeId(),
                                    name: '',
                                    bot: '',
                                    group: '',
                                    content: '',
                                    icon: '',
                                    active: 1,
                                    condition: [],
                                    expand: 1,
                                });
                                this.setState({ config });
                            }}>Add Alert</div>

                        </div> */}


                    </div>

                    <div className="modal-footer">
                        <button type="button" className="btn btn-warning" onClick={() => { this.saveData() }}>{lang('Save and Apply')}</button>
                        <button type="button" className="btn btn-danger" data-dismiss="modal">{lang('Close')}</button>
                    </div>
                </div>
            </div>
        </div>
        );
    }
}

export default FuncEditAlertOrderTrack;
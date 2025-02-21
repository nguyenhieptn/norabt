import React, { Component } from 'react';
import Watchlist from '../../model/admin/Watchlist';

import Ctrl from '../../model/control/Ctrl'
import InputDate from '../inputs/InputDate';

class FuncEditAlertOrder extends Component {
    constructor(props) {
        super(props);
        this.id = makeId();
        this.state = {
            config: {},
            index: '',
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


    edit(config, index){
        console.log(index);
        console.log(config);
        var editConfig = {
            id: config.id,
            name: config.name,
            enter_price: config.enter_price,
            frame: config.frame,
            bot: config.bot,
            group: config.group,
            content: config.content,
            icon: config.icon,
            active: config.active,
            condition: config.condition,
            phases: config.phases,
            next_alert: config.next_alert
        }
        this.setState({
            config:editConfig, index
        })
    }

    clone(config){
        this.setState({
            index: '',
            config: {
                id: makeId(),
                name: config.name,
                enter_price: config.enter_price,
                frame: config.frame,
                bot: config.bot,
                group: config.group,
                content: config.content,
                icon: config.icon,
                active: config.active,
                condition: config.condition,
                phases: config.phases,
                next_alert: config.next_alert
            }
        }) 
    }


    add(){
        this.setState({
            index: '',
            config: {
                id: makeId(),
                name: '',
                enter_price: '',
                frame: '',
                bot: '',
                group: '',
                content: '',
                icon: '',
                active: 1,
                condition: [],
                phases: [],
            }
        })
    }


    saveData(){
        if(this.props.onSave){
            this.props.onSave(this.state.config, this.state.index)
        }
    }


    reloadAlertService() {
        // App.loading(true);
        // return axios.request({
        //     url: '/admin/order_track/reloadAlert',
        //     method: 'POST',

        // })
        //     .then(response => {
        //         App.loading(false, 'Loading...');
        //         response = response['data'];
        //         if (!response['result']) {
        //             error_handle(response);

        //         }
        //     })

        //     .catch((error) => {
        //         console.log(error);
        //         App.loading(false, 'Loading...');
        //         error_handle(error)

        //     })
    }


    
    render() {
        var config = this.state.config;
        var conditions = get(config.condition, []);
        var phases = get(config.phases, []);
        
        return (
            <div className="modal fade" id={"add_row_modal" + this.id} onClick={() => { addClass($('body')[0], 'modal-open') }}>
            <div className="modal-dialog modal-lg modal-dialog-centered" style={{ maxWidth: '95%' }}>
                <div className="modal-content">

                    <div className="modal-header">
                        <h4 className="modal-title">{get(this.props.title, lang("Alert Configuration"))}</h4>
                        <button type="button" className="close" data-dismiss="modal">&times;</button>
                    </div>

                    <div className="modal-body" style={{ padding: 15 }}>

                      
                            
                            <div key={config.id} className='box_border'>

                                <div className='box_flex button' style={{ padding: 5, margin: 5 }} onClick={()=>{
                                    config.expand = (config.expand == 1 ? 0 : 1);
                                    this.setState({ config });
                                }}>

                                    <i className={config.expand == 1 ? "fa fa-caret-down": "fa fa-caret-right"} style={{marginRight:15}}></i>
                                    <div><b>{config.name}</b></div>

                                    {/* <i style={{margin: 'auto 0px auto auto'}} className='close button' onClick={() => {
                                        config.splice(cfgIndex, 1);
                                        this.setState({ config });
                                    }}>×</i> */}

                                </div>


                                <div style={{display:'block', borderTop:'solid thin darkgray'}}>

                                    <div className='box_flex' style={{ padding: 5, margin: 5 }}>
                                        <div style={{ flex: 1 }}>Name:</div>
                                        <input style={{ flex: 2 }} placeholder="Name" className='input' value={config.name} onChange={(e) => {
                                            config.name = e.target.value;
                                            this.setState({ config });
                                        }}></input>
                                    </div>

                                    <div className='box_flex' style={{ padding: 5, margin: 5 }}>
                                        <div style={{ flex: 1 }}>Frame:</div>
                                        <select style={{ flex: 2 }} className='input' value={config.frame} onChange={(e) => {
                                            config.frame = e.target.value;
                                            this.setState({ config });
                                        }}>
                                            <option value={''}>Frame</option>
                                            <option value={'4h'}>4H</option>
                                            <option value={'1d'}>1D</option>
                                        </select>
                                    </div>

                                    <div className='box_flex' style={{ padding: 5, margin: 5 }}>
                                        <div style={{ flex: 1 }}>Enter Price (%):<p style={{color:'limegreen'}}>Percent lower than LOW</p></div>
                                        <input style={{ flex: 2 }} placeholder="Enter Price" className='input' type="number" value={config.enter_price} onChange={(e) => {
                                            config.enter_price = e.target.value;
                                            this.setState({ config });
                                        }}></input>
                                    </div>

                                    <div className='box_flex' style={{ padding: 5, margin: 5 }}>
                                        <div style={{ flex: 1 }}>BOT ID:</div>
                                        <input style={{ flex: 2 }} placeholder="BOT ID" className='input' value={config.bot} onChange={(e) => {
                                            config.bot = e.target.value;
                                            this.setState({ config });
                                        }}></input>
                                    </div>

                                    <div className='box_flex' style={{ padding: 5, margin: 5 }}>
                                        <div style={{ flex: 1 }}>Group ID:</div>
                                        <input style={{ flex: 2 }} placeholder="Group ID" className='input' value={config.group} onChange={(e) => {
                                            config.group = e.target.value;
                                            this.setState({ config });
                                        }}></input>
                                    </div>

                                    <div className='box_flex' style={{ padding: 5, margin: 5 }}>
                                        <div style={{ flex: 1 }}>Icon:</div>
                                        <select style={{ flex: 2 }} className='input' value={config.icon} onChange={(e) => { config.icon = e.target.value; this.setState({ config }) }}>
                                            {this.state.icon.map(icon => {
                                                return <option key={icon} value={icon}>{icon}</option>
                                            })}
                                        </select>
                                    </div>

                                    <div className='box_flex' style={{ padding: 5, margin: 5 }}>
                                        <div style={{ flex: 1 }}>Active:</div>
                                        <select style={{ flex: 2 }} className='input' value={config.active} onChange={(e) => {
                                            config.active = e.target.value;
                                            this.setState({ config });
                                        }}>
                                            <option value={1}>Active</option>
                                            <option value={0}>Disable</option>
                                        </select>
                                    </div>

                                    <div className='box_flex' style={{ padding: 5, margin: 5 }}>
                                        <div style={{ flex: 1 }}>Content:</div>
                                        <textarea style={{ flex: 2 }} placeholder="Content" className='input' value={config.content} onChange={(e) => {
                                            config.content = e.target.value;
                                            this.setState({ config });
                                        }}></textarea>
                                    </div>

                                    <div className='box_flex' style={{ padding: 5, margin: 5 }}>
                                        <div style={{ flex: 1 }}>Note:</div>
                                        <textarea style={{ flex: 2 }} placeholder="Note" className='input' value={config.note} onChange={(e) => {
                                            config.note = e.target.value;
                                            this.setState({ config });
                                        }}></textarea>
                                    </div>


                                    <div className='box_flex' style={{ padding: 5, margin: 5 }}>
                                        <div style={{ flex: 1 }}>Next Alert:</div>
                                        <textarea style={{ flex: 2 }} placeholder="Next Alert" className='input' value={JSON.stringify(config.next_alert)} onChange={(e) => {
                                            try {
                                                config.next_alert = JSON.parse(e.target.value);
                                            } catch (error) {
                                                config.next_alert = null
                                            }
                                            
                                            this.setState({ config });
                                        }}></textarea>
                                    </div>

                                    {/* <div className='box_flex' style={{ padding: 5, margin: 5 }}>
                                        <div style={{ flex: 1 }}>Next Alert:</div>
                                        <InputDate className="input" format={DATE_FORMAT} value={config.next_alert} onChange={(obj)=>{
                                            config.next_alert = obj.getValue();
                                            this.setState({ config });
                                        }}></InputDate>
                                    </div> */}

                                    <div className='box_flex' style={{ padding: 5, margin: 5 }}>
                                        <div style={{ flex: 1 }}>Conditions (AND):</div>
                                        <div style={{ flex: 1 }}><div style={{width:200}} className='button btn btn-sm btn-primary' onClick={() => {
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
                                                    {['>', '<', '=', '>=', '<=', '!='].map(col => {
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



                                    <div className='box_flex' style={{ padding: 5, margin: 5 }}>
                                        <div style={{ flex: 1 }}>Phases:</div>
                                        <div style={{ flex: 1 }}><div style={{width:200}} className='button btn btn-sm btn-primary' onClick={() => {
                                            phases.push({
                                                id: makeId(),
                                                name: '',
                                                profit: '',
                                                enter_package: '',
                                                takeprofit: '',
                                                note: '',
                                            });
                                            this.setState({ config })
                                        }}>Add Phase</div></div>

                                    </div>

                                    {phases.map((phase, conIndex) => {

                                        return <div key={phase.id} className='box_flex box_border' style={{ padding: 5, margin: 5, borderRadius: 5, background: 'white' }}>
                                            <div style={{ flex: 1, margin: 5 }}><div className='button btn btn-sm btn-danger' onClick={() => {
                                                phases.splice(conIndex, 1);
                                                this.setState({ config });
                                            }}>Delete</div></div>

                                            <div style={{ flex: 5, margin: 5 }}>
                                                <input className='input' style={{ width: '100%' }} placeholder="Name" type='text' value={phase.name} onChange={e => {
                                                    phase.name = e.target.value;
                                                    this.setState({ config });
                                                }}></input>
                                            </div>
                                             
                                            <div style={{ flex: 5, margin: 5 }}>
                                                <input className='input' style={{ width: '100%' }} placeholder="Enter Package (%)" type='number' value={phase.enter_package} onChange={e => {
                                                    phase.enter_package = e.target.value;
                                                    this.setState({ config });
                                                }}></input>
                                            </div>

                                            <div style={{ flex: 5, margin: 5 }}>
                                                <input className='input' style={{ width: '100%' }} placeholder="Profit (%)" type='number' value={phase.profit} onChange={e => {
                                                    phase.profit = e.target.value;
                                                    this.setState({ config });
                                                }}></input>
                                            </div>

                                            <div style={{ flex: 5, margin: 5 }}>
                                                <input className='input' style={{ width: '100%' }} placeholder="Take Profit (%)" type='number' value={phase.takeprofit} onChange={e => {
                                                    phase.takeprofit = e.target.value;
                                                    this.setState({ config });
                                                }}></input>
                                            </div>

                                            <div style={{ flex: 5, margin: 5 }}>
                                                <input className='input' style={{ width: '100%' }} placeholder="Note" type='text' value={phase.note} onChange={e => {
                                                    phase.note = e.target.value;
                                                    this.setState({ config });
                                                }}></input>
                                            </div>

                                        </div>
                                    })}

                                </div>

                            </div>

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

export default FuncEditAlertOrder;
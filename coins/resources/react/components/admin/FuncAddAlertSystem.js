import React, { Component } from 'react';


import Ctrl from '../../model/control/Ctrl'
class FuncAddAlertSystem extends Component {
    constructor(props) {
        super(props);
        this.id = makeId();
        this.state = {
            config: [
                {
                    id: makeId(),
                    name: '',
                    bot: '',
                    group: '',
                    content: '',
                    note: '',
                    icon: '',
                    active: 1,
                    condition: [],
                    expand: 1,
                }

            ],

            object: {
                '': 'Select Object',
                'cpu': 'CPU',
                'ram': 'RAM',
                'swap': 'SWAP',
                'disk': 'DISK',

            },

            icon: ['', '↗️', '↘️', '✅', '⛔️', '⏹', '🚫', '🤝', '🕒', '⚠️'],
            symbols: {}
        }
    }

    setData(data, row) {
        var config = this.state.config;
        config[0].id = makeId();
        if (row) {
            config[0].name = row.name;
            config[0].bot = row.bot;
            config[0].group = row.group;
            config[0].content = row.content;
            config[0].note = row.note;
            config[0].icon = row.icon;
            config[0].active = row.active;
            config[0].condition = row.condition;
            config[0].expand = row.expand;
        }
        this.setState({ data });
    }
    modal(cmd = 'show') {
        if (cmd == 'hide') {
            $("#add_row_modal" + this.id).modal('hide');
        } else {
            $("#add_row_modal" + this.id).modal();

        }
    }


    saveData() {
        var data = this.state.data.concat(this.state.config);
        var ctrl = new Ctrl();
        ctrl.set({ 'system_alter': JSON.stringify(data) }).then(res => {
            this.props.reload();

            if (res['result']) this.modal('hide');
        });
    }






    render() {
        var config = this.state.config;

        return (
            <div className="modal fade" id={"add_row_modal" + this.id} onClick={() => { addClass($('body')[0], 'modal-open') }}>
                <div className="modal-dialog modal-lg modal-dialog-centered" style={{ maxWidth: '75%' }}>
                    <div className="modal-content">

                        <div className="modal-header">
                            <h4 className="modal-title">{get(this.props.title, lang("Alert Configuration"))}</h4>
                            <button type="button" className="close" data-dismiss="modal">&times;</button>
                        </div>

                        <div className="modal-body" style={{ padding: 15 }}>

                            {config.map((item, cfgIndex) => {
                                var conditions = item.condition;
                                return <div key={item.id} className='box_border'
                                    style={{ marginBottom: 10, borderRadius: 5 }}
                                >

                                    <div className='box_flex button' style={{ padding: 5, margin: 5 }} onClick={() => {
                                        item.expand = (item.expand == 1 ? 0 : 1);
                                        this.setState({ config });
                                    }}>

                                        <i className={item.expand == 1 ? "fa fa-caret-down" : "fa fa-caret-right"} style={{ marginRight: 15 }}></i>
                                        <div><b>{item.name}</b></div>

                                    </div>


                                    <div style={{ display: 'block', borderTop: 'solid thin darkgray' }}>

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
                                                    <select className='input' style={{ width: '100%' }} value={condition.object} onChange={e => {
                                                        condition.object = e.target.value;
                                                        this.setState({ config });
                                                    }}>
                                                        {Object.keys(this.state.object).map(col => {
                                                            return <option key={col} value={col}>{this.state.object[col]}</option>
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

export default FuncAddAlertSystem;
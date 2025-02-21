import React, { Component } from 'react';

import Lab_account from '../../model/admin/Lab_account'
import Lab_optimization from '../../model/admin/Lab_optimization'
import Input from '../../components/input/Input';
import DragSort from '../common/DragSort';
import Tooltip from '../common/Tooltip';

class FuncAddAOptimize extends Component {
    constructor(props) {
        super(props);
        this.id = makeId();
        this.state = {
            optionsAccount: {},
            AccountValue: '',
            ThreadValue: 20,
            DataLength: 15,
            NameValue: '',
            optionsServer:{} ,
            ServerValue : '',
            IdValue: null,
            variables: [],
            totalFrom: 0,
            needUpdate: 0,
            optionsUser:{} ,
            UserValue : '',
        }
    }

    async getData() {

        var model_labAccount = new Lab_account();

        var dataAccount = await model_labAccount.read({});
        dataAccount = dataAccount['data'];

        var optionsAccount = { '': "--Select Account--" };

        dataAccount.map(item => {
            optionsAccount[item[LAB_ACCOUNT_ID]] = item[LAB_ACCOUNT_NAME];
        })

        this.setState({
            optionsAccount,
            needUpdate: this.state.needUpdate + 1
        });
    }

    modal(cmd = 'show') {
        if (cmd == 'hide') {
            $("#add_row_modal" + this.id).modal('hide');
        } else {
            $("#add_row_modal" + this.id).modal();

        }
    }



    setValue(opti = null, clone = null) {
        var options = this.props.table().mapping.lab_opt_server;
        options[''] = "--Select Server--";

        if (opti == null) {
            this.setState({
                AccountValue: '',
                ThreadValue: 20,
                DataLength: 15,
                NameValue: '',
                ServerValue : '',
                optionsServer: options,
                IdValue: null,
                variables: [],
                totalFrom: 0,
                needUpdate: this.state.needUpdate + 1
            })
        } else {
            var lab_optimizationModel = new Lab_optimization();
            lab_optimizationModel.read({
                [LAB_OPT_ID]: opti
            }).then(res => {
                if (!res['result']) {
                    error_handle(res);
                    return
                }
                if (!isset(res['data'][0])) {
                    return
                }

                var optiObj = res['data'][0]

                var optionsUser = this.props.table().mapping[LAB_OPT_USER];
                optionsUser[''] = "--Select User--";

                this.setState({
                    AccountValue: optiObj[LAB_OPT_ACCOUNT],
                    ThreadValue: optiObj[LAB_OPT_THREAD],
                    DataLength: optiObj[LAB_OPT_DATA_LENG],
                    NameValue: clone ? optiObj[LAB_OPT_NAME] + '_Copy' : optiObj[LAB_OPT_NAME],
                    ServerValue :  optiObj[LAB_OPT_SERVER],
                    optionsServer: options,
                    IdValue: clone ? null : optiObj[LAB_OPT_ID],
                    variables: JSON.parse(optiObj[LAB_OPT_PARAMS]),
                    needUpdate: this.state.needUpdate + 1,
                    optionsUser,
                    UserValue : optiObj[LAB_OPT_USER]
                }, () => this.calTotalForm())

            })
        }
    }

    saveData() {
        var context = this.state;
        var data = {
            [LAB_OPT_ACCOUNT]: context.AccountValue,
            [LAB_OPT_THREAD]: context.ThreadValue,
            [LAB_OPT_DATA_LENG]: context.DataLength,
            [LAB_OPT_NAME]: context.NameValue,
            [LAB_OPT_SERVER] : context.ServerValue,
            [LAB_OPT_PARAMS]: JSON.stringify(context.variables),
        }


        if(App.user[AUTHEN_GROUP] == 0 && this.state.IdValue !== null ){
            data[LAB_OPT_USER] = context.UserValue
        }

        var lab_optimizationModel = new Lab_optimization();
        if (this.state.IdValue == null) {

            lab_optimizationModel.add(data).then(res => {
                if (res['result']) {
                    this.modal('hide')
                    if (this.props.onSave) this.props.onSave()
                } else {
                    error_handle(res)
                }
            });
        } else {
            lab_optimizationModel.edit({
                [LAB_OPT_ID]: this.state.IdValue
            }, data).then(res => {
                if (res['result']) {
                    this.modal('hide')
                    if (this.props.onSave) this.props.onSave()
                } else {
                    error_handle(res)
                }
            })
        }

    }

    onCache(item) {

        var name = item['name'];

        if (item['type'] == "SETS")
            var text = `"#${name}[]#"`;
        else
            var text = `"#${name}#"`;

        const el = document.createElement('input');
        el.value = text;
        el.style.position = 'absolute';
        el.style.left = '-9999px';
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);

    }

    renderResultData(contex) {

        var startValue = contex.startInput.getValue()
        var stopValue = contex.stopInput.getValue()
        var stepValue = contex.stepInput.getValue()



        if (stopValue != '' && stepValue != '' && startValue != '') {
            startValue = Number(startValue)
            stopValue = Number(stopValue)
            stepValue = Number(stepValue)
            if(startValue >= stopValue || stepValue <= 0) {
                contex.dataInput.tooltip.set(true, 'Start must be greater than Stop and Step greater than 0', false)

            }
            var data = [];
            for (let index = startValue; index <= stopValue; index += stepValue) {
                index = Math.round(index * 10000) / 10000
                data.push(index);
            }

            contex.dataInput.setValue(data.join(","))
            contex.dataInput.getInput().getInput().focus()

        }
    }

    calTotalForm() {

        var variables = this.state.variables;
        var totalFrom = 0;
        variables.map(item => {
            if (item.type == "EXPRESSIONS") return;
            if (typeof (item.data) != 'object') return;
            var leng = item.data.length
            if (totalFrom == 0) {
                totalFrom = leng
            } else {
                totalFrom *= leng
            }
        })
        this.setState({
            totalFrom,
        });
    }


    changeOrder(src_id, des_id) {
        src_id = Number(src_id)
        des_id = Number(des_id)
        var variables = this.state.variables
        if (src_id > des_id) {
            variables.splice(des_id, 0, variables[src_id])
            variables.splice(src_id + 1, 1)
        }
        if (des_id > src_id) {
            variables.splice(des_id + 1, 0, variables[src_id])
            variables.splice(src_id, 1)
        }
        this.setState({
            variables
        })
    }

    renderUser(){

        if(this.state.IdValue == null) return
        if(App.user[AUTHEN_GROUP] !== 0) return
        return(
            <div style={{ display: 'flex', alignItems: 'center' }}>
            <div className='editor_item'>
                <div className=''>
                    <div>
                        User <span style={{ color: 'red' }}>*</span>
                    </div>
                </div>
                <div>

                    <Input className='input' struct={{
                        [INPUT_TYPE]: 'select',
                        [INPUT_NULL]: true,
                        [INPUT_OPTION]: this.state.optionsUser,
                        [INPUT_DEFAULT]: this.state.UserValue,
                        [INPUT_ONCHANGE]: (e, obj) => { this.state.UserValue = obj.getValue() }
                    }}></Input>

                </div>
            </div>
        </div>
        )
    }


    componentDidMount() {
        this.getData()
    }

    render() {
        var variables = this.state.variables;
        return (
            <div className="modal fade" id={"add_row_modal" + this.id} onClick={() => { addClass($('body')[0], 'modal-open') }}>
                <div className="modal-dialog modal-lg modal-dialog-centered" style={{ maxWidth: '75%' }}>
                    <div className="modal-content">

                        <div className="modal-header">
                            <h4 className="modal-title">{lang("Add")}</h4>
                            <button type="button" className="close" data-dismiss="modal">&times;</button>
                        </div>

                        <div className="modal-body" >

                            <form key={this.state.needUpdate} id={this.state.needUpdate}>
                                <div style={{ display: 'flex', alignItems: 'center' }}>
                                    <div className='editor_item'>
                                        <div className=''>
                                            <div>
                                                Name <span style={{ color: 'red' }}>*</span>
                                            </div>
                                        </div>

                                        <div>
                                            <Input className='input' struct={{
                                                [INPUT_TYPE]: 'text',
                                                [INPUT_NULL]: true,
                                                [INPUT_DEFAULT]: this.state.NameValue,
                                                [INPUT_ONCHANGE]: (e, obj) => { this.state.NameValue = obj.getValue() }
                                            }}></Input>
                                        </div>
                                    </div>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center' }}>
                                    <div className='editor_item'>
                                        <div className=''>
                                            <div>
                                                Account <span style={{ color: 'red' }}>*</span>
                                            </div>
                                        </div>

                                        <div>

                                            <Input className='input' struct={{
                                                [INPUT_TYPE]: 'select_unsort',
                                                [INPUT_NULL]: true,
                                                [INPUT_OPTION]: this.state.optionsAccount,
                                                [INPUT_DEFAULT]: this.state.AccountValue,
                                                [INPUT_ONCHANGE]: (e, obj) => { this.state.AccountValue = obj.getValue() }
                                            }}></Input>

                                        </div>
                                    </div>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center' }}>
                                    <div className='editor_item'>
                                        <div className=''>
                                            <div>
                                                Thread <span style={{ color: 'red' }}>*</span>
                                            </div>
                                        </div>

                                        <div>

                                            <Input className='input' struct={{
                                                [INPUT_TYPE]: 'number',
                                                [INPUT_NULL]: false,
                                                [INPUT_DEFAULT]: this.state.ThreadValue,
                                                [INPUT_ONCHANGE]: (e, obj) => { this.state.ThreadValue = obj.getValue() }
                                            }}></Input>

                                        </div>
                                    </div>
                                </div>

                                <div style={{ display: 'flex', alignItems: 'center' }}>
                                    <div className='editor_item'>
                                        <div className=''>
                                            <div>
                                                Data Length <span style={{ color: 'red' }}>*</span>
                                            </div>
                                        </div>

                                        <div>

                                            <Input className='input' struct={{
                                                [INPUT_TYPE]: 'number',
                                                [INPUT_NULL]: false,
                                                [INPUT_DEFAULT]: this.state.DataLength,
                                                [INPUT_ONCHANGE]: (e, obj) => { this.state.DataLength = obj.getValue() }
                                            }}></Input>

                                        </div>
                                    </div>
                                </div>

                                <div style={{ display: 'flex', alignItems: 'center' }}>
                                    <div className='editor_item'>
                                        <div className=''>
                                            <div>
                                                Server <span style={{ color: 'red' }}>*</span>
                                            </div>
                                        </div>
                                        <div>

                                            <Input className='input' struct={{
                                                [INPUT_TYPE]: 'select',
                                                [INPUT_NULL]: true,
                                                [INPUT_OPTION]: this.state.optionsServer,
                                                [INPUT_DEFAULT]: this.state.ServerValue,
                                                [INPUT_ONCHANGE]: (e, obj) => { this.state.ServerValue = obj.getValue() }
                                            }}></Input>

                                        </div>
                                    </div>
                                </div>

                                {
                                    this.renderUser()

                                }

                              
                            </form>

                            <hr />

                            <div className='' style={{ padding: 5 }}>
                                <div className='box_flex' style={{ width: '100%' }}>
                                    <div style={{ marginLeft: '5px', fontWeight: 'bold' }}>
                                        Total Params:
                                        &nbsp;
                                        <span style={{ color: 'red' }}>{this.state.totalFrom}</span>
                                    </div>
                                    <button className='button btn btn-sm btn-info' style={{ margin: 'auto 0px auto auto' }} onClick={() => {
                                        variables.push({
                                            id: makeId(),
                                            name: '',
                                            type: 'INPUT',
                                            data: []
                                        });
                                        this.setState({
                                            variables,
                                        });
                                    }}>{lang('Add')}</button>
                                </div>

                                <div style={{ width: '100%' }} key={this.state.needUpdate}>
                                    {variables.map((item, key) => {

                                        let variableContex = {}

                                        return <DragSort key={item['id']} style={{ textAlign: 'center' }} changeOrder={(src_id, des_id) => { this.changeOrder(src_id, des_id) }} src_weight={key} src_id={key} icon={false}>

                                            <div className="box_flex">

                                                <div style={{ flex: 2, padding: 5, position: 'relative' }} className="box_flex">
                                                    <div className='button' style={{ marginLeft: 3 }} onMouseEnter={() => {
                                                        variableContex.copyTooltip.set(true, 'Click to copy variable name', false)
                                                    }} onClick={(e) => {
                                                        this.onCache(item)
                                                        variableContex.copyTooltip.set(true, 'Copied', false)
                                                    }}>
                                                        <i className="fa fa-clipboard" style={{ color: "gray" }}></i>
                                                        <Tooltip ref={tooltip => variableContex.copyTooltip = tooltip}></Tooltip>
                                                    </div>

                                                    <Input style={{ flex: 1 }} className='input' placeholder={lang('Name')} struct={{
                                                        [INPUT_TYPE]: 'text',
                                                        [INPUT_DEFAULT]: item['name'],
                                                        [INPUT_ONCHANGE]: (e, obj) => {
                                                            var val = obj.input.getValue();
                                                            item['name'] = val;
                                                            this.setState({
                                                                variables
                                                            });
                                                        },
                                                    }}></Input>
                                                </div>
                                                <div style={{ flex: 1, padding: 5 }}>

                                                    <Input className='input' struct={{
                                                        [INPUT_TYPE]: 'select',
                                                        [INPUT_DEFAULT]: item['type'],
                                                        [INPUT_ONCHANGE]: (e, obj) => {
                                                            var val = obj.input.getValue();
                                                            item['type'] = val;
                                                            if (val == 'EXPRESSIONS')
                                                                item['data'] = ''
                                                            else
                                                                item['data'] = []

                                                            this.setState({
                                                                variables
                                                            });
                                                        },
                                                        [INPUT_OPTION]: {
                                                            'INPUT': 'INPUT',
                                                            'EXPRESSIONS': 'EXPRESSIONS',
                                                            'SETS': 'SETS'
                                                        }
                                                    }}></Input>
                                                </div>

                                                {item['type'] == 'INPUT'

                                                    ? <div className='box_flex' style={{ flex: 5 }}>
                                                        <div style={{ display: 'flex', flex: 1, padding: 5 }}>
                                                            <Input className='input' ref={c => variableContex.startInput = c} placeholder={'Start'} struct={{
                                                                [INPUT_TYPE]: 'number',
                                                                [INPUT_ONCHANGE_BLUR]: (e, obj) => {
                                                                    this.renderResultData(variableContex)
                                                                }
                                                            }}></Input>
                                                            <Input className='input' ref={c => variableContex.stopInput = c} placeholder={'Stop'} struct={{
                                                                [INPUT_TYPE]: 'number',
                                                                [INPUT_ONCHANGE_BLUR]: (e, obj) => {
                                                                    this.renderResultData(variableContex);
                                                                }
                                                            }}></Input>
                                                            <Input className='input' placeholder={'Step'} ref={c => variableContex.stepInput = c} struct={{
                                                                [INPUT_TYPE]: 'number',
                                                                [INPUT_ONCHANGE_BLUR]: (e, obj) => {
                                                                    this.renderResultData(variableContex)
                                                                }
                                                            }}></Input>
                                                        </div>


                                                        <div style={{ flex: 1, padding: 5, minWidth: 50 }}>

                                                            <Input className='input' ref={c => variableContex.dataInput = c} placeholder={'Ex: 1,2,3'} struct={{
                                                                [INPUT_TYPE]: 'textarea',
                                                                [INPUT_DEFAULT]: item['data'].join(", "),
                                                                [INPUT_ONBLUR]: (e, obj) => {
                                                                    var val = obj.input.getValue();
                                                                    val = val.split(",").filter(item => item != null && item != '')
                                                                    item.data = val
                                                                    this.setState({
                                                                        variables
                                                                    }, () => this.calTotalForm());

                                                                }
                                                            }}></Input>

                                                        </div>
                                                    </div>

                                                    : item['type'] == 'SETS'

                                                        ? <div style={{ flex: 5 }}>
                                                            <Input className='input' ref={c => variableContex.dataInput = c} placeholder={'Ex: [1,2,3], [2,3,4]'} struct={{
                                                                [INPUT_TYPE]: 'textarea',
                                                                [INPUT_DEFAULT]: item['data'].map(item => JSON.stringify(item)).join(","),
                                                                [INPUT_ONBLUR]: (e, obj) => {
                                                                    var val = obj.input.getValue();


                                                                    try {
                                                                        val = eval("[" + val + "]")
                                                                        let leng = null
                                                                        for (let item of val) {
                                                                            if (leng === null) {
                                                                                leng = item.length
                                                                            } else {
                                                                                if (leng != item.length) {
                                                                                    obj.tooltip.set(true, "All parameter sets must have the same length", false)
                                                                                    obj.getInput().getInput().focus()
                                                                                    return
                                                                                }
                                                                            }
                                                                        }
                                                                    } catch (error) {
                                                                        obj.tooltip.set(true, 'Wrong format', false)
                                                                        obj.getInput().getInput().focus()
                                                                        return
                                                                    }



                                                                    item.data = val
                                                                    this.setState({
                                                                        variables
                                                                    }, () => this.calTotalForm());

                                                                }
                                                            }}></Input>
                                                        </div>
                                                        : <div style={{ flex: 5 }}>

                                                            <Input className='input' placeholder={'Ex: 100/(#A# + #B#)'} struct={{
                                                                [INPUT_TYPE]: 'textarea',
                                                                [INPUT_DEFAULT]: item['data'],
                                                                [INPUT_ONBLUR]: (e, obj) => {
                                                                    var val = obj.input.getValue();
                                                                    item.data = val
                                                                    this.setState({
                                                                        variables
                                                                    }, () => this.calTotalForm());

                                                                }
                                                            }}></Input>

                                                        </div>
                                                }


                                                <div style={{ padding: 5 }}>
                                                    <div className='button close' onClick={() => {
                                                        variables.splice(key, 1);
                                                        this.setState({
                                                            variables
                                                        }, () => this.calTotalForm());
                                                    }}>&times;</div>
                                                </div>

                                            </div>
                                        </DragSort>
                                    })
                                    }
                                </div>
                            </div>



                        </div>

                        <div className="modal-footer">
                            <button type="button" className="btn btn-warning" onClick={() => { this.saveData() }}>{lang('Save')}</button>
                            <button type="button" className="btn btn-danger" data-dismiss="modal">{lang('Close')}</button>
                        </div>
                    </div>
                </div>
            </div>
        );
    }
}

export default FuncAddAOptimize;
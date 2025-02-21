import React, { Component } from 'react';


import Lab_optimization from '../../model/admin/Lab_optimization'
import Lab_opt_schedule from '../../model/admin/Lab_opt_schedule'
import Lab_account from '../../model/admin/Lab_account'
import Input from '../../components/input/Input';
import InputV2 from '../../components/Input_v2/Input';
import DragSort from '../common/DragSort';
import Tooltip from '../common/Tooltip';
import Lab_schedule from '../../model/admin/Lab_schedule';

class FunLabSchedule extends Component {
    constructor(props) {
        super(props);
        this.id = makeId();
        this.state = {

            NameValue: '',
            IdValue: null,
            variables: [],
            needUpdate: 0,
            optionsOpt: [],
            optionsStatus: {},
            optionsServer: {},
            ServerName: [],
            AccountValue: '',
            optionsAccount: {},
            optionsUser:{} ,
            UserValue : '',

        }

        this.optModel = new Lab_optimization();
        this.accountModel = new Lab_account();
    }


    modal(cmd = 'show') {
        if (cmd == 'hide') {
            $("#add_row_modal" + this.id).modal('hide');
        } else {
            $("#add_row_modal" + this.id).modal();

        }
    }

    setValue(opti = null, clone = null) {
        var options = this.props.table().mapping.lab_sche_param;
        options[''] = "--Select Status--";


        var optionsServer = this.props.table().mapping['Lab_sche_server'];
        if (opti == null) {
            this.setState({

                NameValue: '',
                IdValue: null,
                variables: [],
                optionsStatus: options,
                needUpdate: this.state.needUpdate + 1,
                optionsServer,
                ServerName: '',
                AccountValue: '',
                optionsAccount: {}
            })
        } else {
            var lab_opt_scheduleModel = new Lab_schedule();
            lab_opt_scheduleModel.read({
                [LAB_SCHE_ID]: opti
            }).then( async (res) => {
                if (!res['result']) {
                    error_handle(res);
                    return
                }
                if (!isset(res['data'][0])) {
                    return
                }

                var optionsUser = this.props.table().mapping[LAB_SCHE_USER];
                optionsUser[''] = "--Select User--";

                var optiObj = res['data'][0]
                let serverName = await this.getServerByAccount(JSON.parse(optiObj[LAB_SCHE_PARAM])[0]['account'])
                serverName = serverName.charAt(0).toUpperCase() + serverName.slice(1)
                this.setState({
                    NameValue: clone ? optiObj[LAB_SCHE_NAME] + '_Copy' : optiObj[LAB_SCHE_NAME],
                    optionsStatus: options,
                    IdValue: clone ? null : optiObj[LAB_SCHE_ID],
                    variables: JSON.parse(optiObj[LAB_SCHE_PARAM]),
                    needUpdate: this.state.needUpdate + 1,
                    optionsServer,
                    ServerName: serverName,
                    optionsUser,
                    UserValue : optiObj[LAB_SCHE_USER]
                },() => this.getAcount(serverName))
         
                
            })
        }
    }

    saveData() {
        var context = this.state;
        var data = {
            [LAB_SCHE_NAME]: context.NameValue,
            [LAB_SCHE_PARAM]: JSON.stringify(context.variables),
        }
        if(App.user[AUTHEN_GROUP] == 0 && this.state.IdValue !== null ){
            data[LAB_SCHE_USER] = context.UserValue
        }
        var lab_opt_scheduleModel = new Lab_schedule();
        if (this.state.IdValue == null) {
            lab_opt_scheduleModel.add(data).then(res => {
                if (res['result']) {
                    this.modal('hide')
                    this.props.table().filter();
                } else {
                    error_handle(res)
                }
            });
        } else {
            lab_opt_scheduleModel.edit({
                [LAB_SCHE_ID]: this.state.IdValue
            }, data).then(res => {
                if (res['result']) {
                    this.modal('hide')
                    this.props.table().filter();
                } else {
                    error_handle(res)
                }
            })
        }

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

    async getServerByAccount(id){
        var accountData = await this.accountModel.read({[LAB_ACCOUNT_ID] : id});
        if (accountData['result']) {
            accountData = accountData['data']
            return accountData[0]['lab_account_server'] 
        }
    }


    async getAcount(server, params) {
    
        var accountOptions = {};
        let testOptions = [];
        accountOptions[''] = '---Select Account---';
        var accountData = await this.accountModel.read({[LAB_ACCOUNT_SERVER] : server});
        if (accountData['result']) {
            accountData = accountData['data']
            accountData.reverse();
    
            accountData.map(item => {
                accountOptions[item[LAB_ACCOUNT_ID]] = item[LAB_ACCOUNT_NAME]
                testOptions.push({
                    'value' : item[LAB_ACCOUNT_ID],
                    'label' : item[LAB_ACCOUNT_NAME]
                })
            })
        }
    
        if(params){
            this.setState({
                AccountValue:  checkboxAccount ,
                optionsAccount: optionAccount,
                needUpdate: this.state.needUpdate + 1,
            });

    
        }else{
            this.setState({
                // AccountValue: checkboxAccount ,
                // optionsOpt: accountOptions,
                optionsOpt: testOptions,

            }); 
        }

       
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

    render() {
        var variables = this.state.variables;
        return (
            <div className="modal fade" id={"add_row_modal" + this.id} onClick={() => { addClass($('body')[0], 'modal-open') }}>
                <div className="modal-dialog modal-lg modal-dialog-centered" style={{ maxWidth: '70%' }}>
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
                                                Server <span style={{ color: 'red' }}>*</span>
                                            </div>
                                        </div>

                                        <div className='cus_checkbox_style'>
                                            <style>{`
                                                .cus_checkbox_style .checkboxs_text{
                                                    font-weight: bold;
                                                }
                                            `}</style>
                                            <Input ref={c => this.ServerInput = c} className='input ' struct={{
                                                [INPUT_TYPE]: 'radio',
                                                [INPUT_NULL]: true,
                                                [INPUT_DEFAULT]: this.state.ServerName,
                                                [INPUT_OPTION]: this.state.optionsServer,
                                                [INPUT_ONCHANGE]: (e, obj) => {
                                                    var value = obj.getValue();
                                                    console.log(value)
                                                    this.getAcount(value);

                                                }
                                            }}></Input>
                                        </div>
                                    </div>
                                </div>
                                    
                

                                {
                                    this.renderUser()

                                }


                            </form>

                            <hr />

                            <div >
                                <div className='box_flex' style={{ width: '100%' }}>
                                    <div style={{ marginLeft: '5px', fontWeight: 'bold' }}>
                                        Params:

                                    </div>
                                    <button className='button btn btn-sm btn-info' style={{ margin: 'auto 0px auto auto' }} onClick={() => {
                                        variables.push({
                                            id: makeId(),
                                            account: '',
                                            status: 'PENDING',

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

                                                    <span   >Account :</span>
                                                    {/* <Input style={{ flex: 1 }} className='input' placeholder={lang('Name')} struct={{
                                                        [INPUT_TYPE]: 'select',
                                                        [INPUT_DEFAULT]: item['account'],
                                                        [INPUT_OPTION]: this.state.optionsOpt,
                                                        [INPUT_ONCHANGE]: (e, obj) => {
                                                            var val = obj.input.getValue();
                                                          
                                                            item['account'] = val;
                                                            this.setState({
                                                                variables
                                                            });
                                                        },
                                                    }}></Input> */}
                                                   <div style={{ flex: 1 }}>
                                                   <InputV2  className='input' placeholder={lang('Name')} type="select" DefaultValue={item['account']} Options={this.state.optionsOpt} OnChange={
                                                        (value, obj) => {
                                                     
                                                          
                                                            item['account'] = value;
                                                            this.setState({
                                                                variables
                                                            });
                                                        }
                                                    }>
                                                    </InputV2>
                                                   </div>
                                                </div>


                                                <div style={{ flex: 1, padding: 5, position: 'relative' }} className="box_flex">

                                                    <span >Status :</span>
                                                    <Input style={{ flex: 1 }} className='input' struct={{
                                                        [INPUT_TYPE]: 'select',
                                                        [INPUT_DEFAULT]: item['status'],
                                                        [INPUT_OPTION]: this.state.optionsStatus,
                                                        [INPUT_ONCHANGE]: (e, obj) => {
                                                            var val = obj.input.getValue();
                                                            item['status'] = val;
                                                            this.setState({
                                                                variables
                                                            });
                                                        },
                                                    }}></Input>
                                                </div>



                                                <div style={{ padding: 5 }}>
                                                    <div className='button close' onClick={() => {
                                                        variables.splice(key, 1);
                                                        this.setState({
                                                            variables
                                                        });
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

export default FunLabSchedule;
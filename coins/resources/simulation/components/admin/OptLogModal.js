import React, { Component } from 'react';

import Lab_account from '../../model/admin/Lab_account'
import Lab_optimization from '../../model/admin/Lab_optimization'
import Input from '../../components/input/Input';
import DragSort from '../common/DragSort';
import Tooltip from '../common/Tooltip';

class OptLogModal extends Component {
    constructor(props) {
        super(props);
        this.id = makeId();
        this.state = {
            inputValue : ''
        }
    }



    modal(cmd = 'show') {
        if (cmd == 'hide') {
            $("#add_row_modal" + this.id).modal('hide');
           
        } else {
            $("#add_row_modal" + this.id).modal();
            this.setState({
                inputValue : ''
            });

        }
    }

    setValue(id , account=false) {
        if(account == true){
            var optModal = new Lab_account()
            optModal.getLog(id).then(res => {
                if (res['result']) {
                    res = res['data'];
                   this.setState({
                       inputValue : res
                   });
                }else {
                    error_handle(res);
                }
            })
        }else{
            var optModal = new Lab_optimization()
            optModal.getLog(id).then(res => {
                if (res['result']) {
                    res = res['data'];
                   this.setState({
                       inputValue : res
                   });
                }else {
                    error_handle(res);
                }
            })
        }
      
    }





    componentDidMount() {

    }

    render() {

        return (
            <div className="modal fade" id={"add_row_modal" + this.id} onClick={() => { addClass($('body')[0], 'modal-open') }}>
                <div className="modal-dialog modal-lg modal-dialog-centered" style={{ maxWidth: '75%' }}>
                    <div className="modal-content">

                        <div className="modal-header">
                            <h4 className="modal-title">{lang("Log")}</h4>
                            <button type="button" className="close" data-dismiss="modal">&times;</button>
                        </div>

                        <div className="modal-body" >

                            <Input key={this.state.inputValue} height={500} className='input' struct={{
                                [INPUT_TYPE]: 'ace',
                                [INPUT_NULL]: true,
                                [INPUT_DEFAULT]: this.state.inputValue,
                      
                                // [INPUT_ONCHANGE]: (e, obj) => { this.state.NameValue = obj.getValue() }
                            }}></Input>



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

export default OptLogModal;
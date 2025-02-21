import React, { Component } from 'react'


class MakeOrderModal extends Component {

    constructor(props) {
        super(props);

        this.id = makeId();

        this.state = {
            accountId: '',
            accountName: '',
            type: ACTION_TYPE_LONG,
            data: {},
            flows: {},
            flow: '',
        }


    }


    modal(cmd = 'show') {
        if (cmd == 'hide') {
            $("#add_row_modal" + this.id).modal('hide');
        } else {
            $("#add_row_modal" + this.id).modal();
        }
    }


    loadData(data, type) {
        var account = App.accountSelector.getSelectedAccount();
        var accountName = account[ACCOUNT_NAME];
        var accountId = account[ACCOUNT_ID];
        this.setState({
            accountId,
            accountName,
            data,
            type,
        }, ()=>{
            this.getFlows();
        })
    }


    getFlows() {
        App.loading(true);
        return axios.request({
            url: '/admin/actions/getFlows',
            method: 'POST',
            data: {
                account: this.state.accountId,
                type: this.state.type,
                symbol: get(this.state.data[ORDER_TRACK_SYMBOL], ''),
            }

        })
            .then(response => {
                App.loading(false, 'Loading...');
                response = response['data'];
                if (!response['result']) {
                    error_handle(response);

                }else{
                    var flows = response['data'];
                    var selectFlow = '';
                    if(Object.keys(flows).length > 0){
                        selectFlow = Object.keys(flows)[0];
                    }
                    
                    this.setState({
                        flows,
                        flow: selectFlow
                    })
                }
            })

            .catch((error) => {
                console.log(error);
                App.loading(false, 'Loading...');
                error_handle(error)

            })
    }


    makePosition() {

        // var account = App.accountSelector.getSelectedAccount();
        // var accountName = account[ACCOUNT_NAME];
        // var accountId = account[ACCOUNT_ID];

        var type = this.state.type;
        var symbol = get(this.state.data[ORDER_TRACK_SYMBOL], '');
        var flow = this.state.flow;
        var accountId = this.state.accountId;

        if(type == '' || symbol == '' || flow == '' || accountId === ''){
            showLog('Please define type, symbol, account and flow');
            return;
        }

        App.loading(true);
        return axios.request({
            url: '/admin/actions/makeOrder',
            method: 'POST',
            data: {
                type,
                symbol,
                account: accountId,
                flow: flow
            }
        })

            .then(response => {
                App.loading(false);
                response = response['data'];
                this.modal('hide');
                if (!response['result']) {
                    error_handle(response)
                }
            })

            .catch((error) => {
                App.loading(false);
                error_handle(error)
                return false;
            })

    }

    render() {

      
        return (
            <div className="modal fade" id={"add_row_modal" + this.id} onClick={() => { addClass($('body')[0], 'modal-open') }}>
                <div className="modal-dialog modal-lg modal-dialog-centered">
                    <div className="modal-content">

                        <div className="modal-header">
                            <h4 className="modal-title">{get(this.props.title, lang("Make Order"))}</h4>
                            <button type="button" className="close" data-dismiss="modal">&times;</button>
                        </div>

                        <div className="modal-body" style={{ padding: 15 }}>

                            <li style={{marginBottom:8}}>Symbol: <b>{get(this.state.data[ORDER_TRACK_SYMBOL], '')}</b></li>
                            <li style={{marginBottom:8}}>Type: <b>{this.state.type == ACTION_TYPE_LONG ? 'LONG' : 'SHORT'}</b></li>
                            <li style={{marginBottom:8}}>Account: <b>{get(this.state.accountName, '')}</b></li>
                            <li style={{marginBottom:8}}>Flow: <select className='input' value={this.state.flow} onChange={e => this.setState({
                                flow: e.target.value
                            })}>
                                <option value=''>--Select Flow--</option>
                                {Object.keys(this.state.flows).map(flow => {
                                    return <option key={flow} value={flow}>{flow}</option>
                                })}    
                            </select></li>

                        </div>

                        <div className="modal-footer">
                            <button type="button" className="btn btn-primary" onClick={() => { this.makePosition() }}>{lang('Make Position')}</button>
                            <button type="button" className="btn btn-danger" data-dismiss="modal">{lang('Close')}</button>
                        </div>
                    </div>
                </div>
            </div>
        );
    }
}

export default MakeOrderModal
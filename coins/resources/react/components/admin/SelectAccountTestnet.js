import React, { Component } from 'react'
import { Dropdown } from 'primereact/dropdown';
import Testnet_account from '../../model/admin/Testnet_account';


class SelectAccountTestnet extends Component {

    constructor(props) {
        super(props);

        this.state = {
            accountSelected: '',
            accountOptions: [],
        }

        App.accountSelectorTestnet = this

        this.onChanges = [];
        this.accountIndex = {};

    }

    register(name, cb) {
        this.onChanges[name] = cb;
    }

    unregister(name) {
        this.onChanges[name] = null;
    }

    selected() {
        return this.state.accountSelected;
    }

    getSelectedAccount() {
        return this.accountIndex[this.state.accountSelected];
    }

    render() {
        var style = get(this.props.style, {})
        return (
            <div>
                <Dropdown className="drop selectAccount" value={this.state.accountSelected} options={this.state.accountOptions} onChange={(e) => {
                    this.selectAccount(e.value);
                }} placeholder={lang('Select an Account')} style={style} />
                <style>{`
                .selectAccount .p-inputtext{
                    
                }
                .p-dropdown-items-wrapper{
                    max-height: 800px !important;
                }
            `}</style>
            </div>
        );
    }

    selectAccount(projectId) {
        projectId = Number(projectId);
        this.setState({
            accountSelected: projectId,
        }, () => {
            for (let i in this.onChanges) {
                if (this.onChanges[i]) {
                    this.onChanges[i](this.accountIndex[projectId]);
                }
            }
        });
        localStorage.setItem('selected_account_testnet', projectId);
        if (this.props.onSelect) this.props.onSelect(projectId);
    }

    componentDidMount() {
        this.getAccount()
    }


    getAccount() {

        var accountSymbol = new Testnet_account();
        accountSymbol.read(null, false).then((res) => {
            if (res['data']) {
                var response = res['data'];
                response.sort(function(a, b) {
                    return b.testnet_account_id - a.testnet_account_id;
                });
                var accountOptions = [];

                response.map(item => {

                    if(App.user[AUTHEN_GROUP] == 0){
                        accountOptions.push({
                            'label': item[TESTNET_ACCOUNT_NAME],
                            'value': Number(item[TESTNET_ACCOUNT_ID]),
                        });
    
                        this.accountIndex[item[TESTNET_ACCOUNT_ID]] = item;
                    }else{
                        if(App.user.authen_id == item['testnet_account_user']){
                            accountOptions.push({
                                'label': item[TESTNET_ACCOUNT_NAME],
                                'value': Number(item[TESTNET_ACCOUNT_ID]),
                            });
        
                            this.accountIndex[item[TESTNET_ACCOUNT_ID]] = item;
                        }
                    }

          
                });

                this.setState({ accountOptions }, () => {
                    if (accountOptions.length == 0) return;
                    var selectAccount = localStorage.getItem('selected_account_testnet');
                    if (App.parsed.account) selectAccount = App.parsed.account;
                    if (selectAccount == null || selectAccount == '' || !accountOptions.find((item) => item.value == selectAccount)) {
                        selectAccount = Number(accountOptions[0]['value']);
                    }
                    this.selectAccount(selectAccount);
                })


            }
        })


    }

}

export default SelectAccountTestnet
import React, { Component } from 'react'
import { Dropdown } from 'primereact/dropdown';
import Accounts from '../../model/admin/Accounts';


class SelectAccount extends Component {

    constructor(props) {
        super(props);

        this.state = {
            accountSelected: '',
            accountOptions: [],
        }

        App.accountSelector = this

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
        localStorage.setItem('selected_account', projectId);
        if (this.props.onSelect) this.props.onSelect(projectId);
    }

    componentDidMount() {
        this.getAccount()
    }


    getAccount() {

        var accountSymbol = new Accounts();
        accountSymbol.read(null, false).then((res) => {
            if (res['data']) {
                var response = res['data'];
                var accountOptions = [];

                response.map(item => {

                    accountOptions.push({
                        'label': item[ACCOUNT_NAME],
                        'value': Number(item[ACCOUNT_ID]),
                    });

                    this.accountIndex[item[ACCOUNT_ID]] = item;
                });

                this.setState({ accountOptions }, () => {
                    if (accountOptions.length == 0) return;
                    var selectAccount = localStorage.getItem('selected_account');
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

export default SelectAccount
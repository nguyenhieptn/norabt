import React, { Component } from 'react'
import { Dropdown } from 'primereact/dropdown';
import Lab_account from '../../model/admin/Lab_account';
import InputV2 from '../../components/Input_v2/Input';

class SelectAccountLab extends Component {

    constructor(props) {
        super(props);

        this.state = {
            accountSelected: '',
            accountOptions: [],
           
        }

        App.accountSelectorLab = this

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
                {/* <Dropdown className="drop selectAccount" value={this.state.accountSelected} options={this.state.accountOptions} onChange={(e) => {
                    this.selectAccount(e.value);
                }} placeholder={lang('Select an Account')} style={style} />
                <style>{`
                .selectAccount .p-inputtext{
                    
                }
                .p-dropdown-items-wrapper{
                    max-height: 800px !important;
                }
            `}</style> */}


                <InputV2 className='input' type="select"  key={this.state.accountSelected}  DefaultValue={this.state.accountSelected} Options={this.state.accountOptions} OnChange={
                    (value, obj) => {
                        this.selectAccount(value);
                    }
                }>
                </InputV2>

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
        localStorage.setItem('selected_account_lab', projectId);
        if (this.props.onSelect) this.props.onSelect(projectId);
    }

    componentDidMount() {
        this.getAccount()
    }


    getAccount() {

        var accountSymbol = new Lab_account();
        accountSymbol.read(null, false).then((res) => {
            if (res['data']) {
                var response = res['data'];
                response.sort(function (a, b) {
                    return b.lab_account_id - a.lab_account_id;
                });
               
                var accountOptions = [];

                response.map(item => {
                    if (App.user[AUTHEN_GROUP] == 0) {
                        accountOptions.push({
                            'label': item[LAB_ACCOUNT_NAME],
                            'value': Number(item[LAB_ACCOUNT_ID]),
                        });

                        this.accountIndex[item[LAB_ACCOUNT_ID]] = item;
                    } else {
                        if (App.user.authen_id == item['lab_account_user']) {
                            accountOptions.push({
                                'label': item[LAB_ACCOUNT_NAME],
                                'value': Number(item[LAB_ACCOUNT_ID]),
                            });

                            this.accountIndex[item[LAB_ACCOUNT_ID]] = item;
                        }
                    }

                });
                this.setState({ accountOptions }, () => {
                    if (accountOptions.length == 0) return;
                    var selectAccount = localStorage.getItem('selected_account_lab');
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

export default SelectAccountLab
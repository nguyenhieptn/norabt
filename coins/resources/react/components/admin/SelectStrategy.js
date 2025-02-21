import React, { Component } from 'react'
import { Dropdown } from 'primereact/dropdown';
import Strategies from '../../model/admin/Strategies';


class SelectStrategy extends Component {

    constructor(props) {
        super(props);

        this.state = {
            strategySelected: '',
            strategyOptions: [],
            activeIndex: Number(get(App.parsed['tab'], 0)),
        }

        this.strategyIndex = {};

        App.strategySelector = this;
        this.onChanges = [];

    }

    register(name, cb) {
        this.onChanges[name] = cb;
    }

    unregister(name) {
        this.onChanges[name] = null;
    }

    selected() {
        return this.state.strategySelected;
    }

    render() {
        var style = get(this.props.style, {})
        return (
            <div>
                <Dropdown panelStyle={{ whiteSpace: 'nowrap' }} className="drop" value={this.state.strategySelected} options={this.state.strategyOptions} onChange={(e) => {
                    this.selectStrategy(e.value);
                }} placeholder={lang('Select a Strategy')} style={style} />
            </div>
        );
    }

    selectStrategy(projectId = null) {
        if (projectId != null) {
            projectId = Number(projectId);
            this.setState({
                strategySelected: projectId,
            }, () => {
                for (let i in this.onChanges) {
                    if (this.onChanges[i]) {
                        this.onChanges[i](this.strategyIndex[projectId]);
                    }
                }
            });
            localStorage.setItem('selected_strategy', projectId);
        } else {
            projectId = this.state.strategySelected;
        }

    }

    componentDidMount() {
        this.getStrategy()
    }

    getStrategy() {
        var wlModel = new Strategies();
        wlModel.read({[STRATEGY_CONTAINER]:null}, false).then((res) => {
            if (res['data']) {
                var response = res['data'];
                var strategyOptions = [];


                response.map(item => {

                    strategyOptions.push({
                        'label': item[STRATEGY_NAME],
                        'value': Number(item[STRATEGY_ID]),
                    });

                    this.strategyIndex[item[STRATEGY_ID]] = item;
                });

                this.setState({ strategyOptions }, () => {
                    if (strategyOptions.length == 0) return;
                    var selectStrategy = localStorage.getItem('selected_strategy');
                    if (App.parsed.strategy) selectStrategy = App.parsed.strategy;
                    if (selectStrategy == null || selectStrategy == '' || !strategyOptions.find((item) => item.value == selectStrategy)) {
                        selectStrategy = strategyOptions[0]['value'];
                    }
                    this.selectStrategy(selectStrategy);
                })
            }
        })
    }
}

export default SelectStrategy
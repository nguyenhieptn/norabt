import React, { Component } from 'react'
import { Dropdown } from 'primereact/dropdown';
import Lab_strategies from '../../model/admin/Lab_strategies';


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

    selected(){
        return this.state.strategySelected
    }

    register(name, cb){
        this.onChanges[name] = cb;
    }

    unregister(name){
        this.onChanges[name] = null;
    }

    render() {
        var style = get(this.props.style, {})
        return (
            <>
            <Dropdown panelStyle={{whiteSpace:'nowrap'}} className="drop" value={this.state.strategySelected} options={this.state.strategyOptions} onChange={(e) => {
                this.selectStrategy(e.value);
            }} placeholder={lang('Select a Strategy')} style={style} />
            </>
        );
    }

    selectStrategy(projectId = null) {
        if(projectId != null){
            projectId = Number(projectId);
            localStorage.setItem('selected_lab_strategy', projectId);
        }else{
            projectId = this.state.strategySelected;
        }
        this.setState({
            strategySelected: projectId,
        }, ()=>{
            for(let i in this.onChanges){
                if(this.onChanges[i]){
                    this.onChanges[i](this.strategyIndex[projectId]);
                }
            }
        });
        
    }

    componentDidMount() {
        this.getStrategy()
    }

    getStrategy() {
        var wlModel = new Lab_strategies();
        wlModel.read(null, false).then((res)=>{
            if(res['data']){
                var response = res['data'];
                var strategyOptions = [];
                console.log(response)

                response.map(item => {

                    strategyOptions.push({
                        'label': item[LAB_STRATEGY_NAME],
                        'value': Number(item[LAB_STRATEGY_ID]),
                    });

                    this.strategyIndex[item[LAB_STRATEGY_ID]] = item;
                });

                this.setState({strategyOptions}, ()=>{
                    if (strategyOptions.length == 0) return;
                    var selectStrategy = localStorage.getItem('selected_lab_strategy');
                    if(App.parsed.strategy) selectStrategy = App.parsed.strategy;
                    if (selectStrategy == null || selectStrategy == '' || !strategyOptions.find((item)=>item.value == selectStrategy)) {
                        selectStrategy = strategyOptions[0]['value'];
                    }
                    this.selectStrategy(selectStrategy);
                })
            }
        })
    }
}

export default SelectStrategy
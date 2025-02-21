import React, { Component } from 'react'
import Watchlist from '../../model/admin/Watchlist';


class SelectSymbol extends Component {

    constructor(props) {
        super(props);

        this.state = {
            symbolSelected: '',
            symbolOptions: [],
            activeIndex: Number(get(App.parsed['tab'], 0)),
        }

        App.selectSymbol = this

    }

    render() {
        var style = get(this.props.style, {})
        return (
            <div>
                <select className="input" value={this.state.symbolSelected} onChange={(e) => {
                    this.selectSymbol(e.target.value);
                }} placeholder={lang('Select a Symbol')} style={style} >
                    {this.state.symbolOptions.map(item => {
                        return <option key={item['value']} value={item['value']}>{item['label']}</option>
                    })}
                </select>
                
            </div>
        );
    }

    selectSymbol(projectId, action = true) {
        this.setState({
            symbolSelected: projectId,
        });
        localStorage.setItem('selected_symbol', projectId);
        if(this.props.onSelect && action) this.props.onSelect(projectId);
    }

    componentDidMount() {
        this.getSymbol()
    }

    getSymbol() {

        var wlModel = new Watchlist();
        wlModel.read(null, false).then((res)=>{
            if(res['data']){
                var response = res['data'];
                var symbolOptions = [];

                response.map(item => {

                    symbolOptions.push({
                        'label': item[WL_SYMBOL],
                        'value': item[WL_SYMBOL],
                    });
                });

                this.setState({symbolOptions}, ()=>{
                    if (symbolOptions.length == 0) return;
                    var selectSymbol = localStorage.getItem('selected_symbol');
                    if(App.parsed.symbol) selectSymbol = App.parsed.symbol;
                    if (selectSymbol == null || selectSymbol == '' || !symbolOptions.find((item)=>item.value == selectSymbol)) {
                        selectSymbol = symbolOptions[0]['value'];
                    }
                    this.selectSymbol(selectSymbol);
                })

                
            }
        })

        
    }




}

export default SelectSymbol
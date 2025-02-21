import React, { Component } from 'react'

class ChartTooltip extends Component {

	constructor(props) {
        super(props);
		this.state = {
			tooltip: ''
		}
	}

    setTooltip(tooltip){
        this.setState({tooltip});
    }

    render(){
        return <><div className="tooltip_chart" dangerouslySetInnerHTML={{__html: this.state.tooltip}}></div>
        <style>{`
            .tooltip_chart > div {
                min-height: 85px;
                font-size: 11px;
            }
        
        `}</style>
    </>
    }

}


export default ChartTooltip
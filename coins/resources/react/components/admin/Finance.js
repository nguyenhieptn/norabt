import React, { Component } from 'react';
import Finances from '../../model/admin/Finance';



class Finance extends Component {

    constructor(props) {
        super(props);
        this.state = {
            data: [],
        };
    }


    componentDidMount() {
        var finance = new Finances();
        finance.getStock().then(res => {
            if(res['result']){
                this.setState({
                    data: res.data
                });
            }
           
        })

 
        this.updateInterval = setInterval(() => {
            finance.getStock().then(res => {
                if(res['result']){
                    this.setState({
                        data: res.data
                    });
                }
            })
       
        }, 300000);

    }

    componentWillUnmount() {
		 if (this.updateInterval) clearInterval(this.updateInterval);
		
	}

    renderPercent(data) {
        if (data == 0) {
            return `0 %`;
        } else if (data > 0) {
            return <span style={{ color: '#137333' }}>{`+ ${Math.round(data * 1000) / 1000} %`}</span>;
        } else {
            return <span style={{ color: '#a50e0e' }}>{`- ${Math.round(-data * 1000) / 1000} %`}</span>;
        }
    }

    renderIcon(data) {

        if (data == 0) {
            return (
                <span className='finance_icon' style={{ background: ' rgb(193 200 208 / 1)', color: '#5f6368' }} >

                    <i className="pi pi-arrow-right"></i>

                </span>
            )
        } else if (data > 0) {
            return (
                <span className='finance_icon' style={{ background: ' #e6f4ea', color: '#137333' }}>

                    <i className="pi pi-arrow-up"></i>

                </span>
            )
        } else {
            return (
                <span className='finance_icon' style={{ background: ' #fce8e6', color: '#a50e0e' }}>

                    <i className="pi pi-arrow-down"></i>

                </span>
            )
        }

    }
    render() {
        return (
            <div className='p-grid dashboard' >

                {
                    this.state.data.map(item => {


                        return (
                            <div key={item[FINANCE_ID]} className='p-col-12 p-lg-3'>
                                <div className='finance_box'>

                                    {
                                        this.renderIcon(item[FINANCE_PERCENT])
                                    }

                                    <div className='finance_box_1'>
                                        <div className='finance_box_1_text'>
                                            {`${item[FINANCE_NAME]}`}
                                        </div>
                                        <div>
                                            {formatNumber(Math.round(item[FINANCE_CLOSE_NOW] * 100) / 100)}
                                        </div>
                                    </div>

                                    <div className='finance_box_2'>
                                        <div className='finance_box_1_text'>
                                            {
                                                this.renderPercent(item[FINANCE_PERCENT])
                                            }
                                        </div>
                                        <div>
                                            {formatNumber(Math.round(item[FINANCE_CLOSE_PREVIOUS] * 100) / 100)}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )
                    })
                }



            </div>


        );
    }
}

export default Finance;
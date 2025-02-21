import React, { Component } from 'react';

class SystemInfo extends Component {
    constructor(props) {
        super(props);
        this.state = {
            cpu: 0,
            ram: 0,
            totalRam: 0,
            swap: 0,
            totalSwap: 0,
            disk: 0,
            totalDisk: 0,
        }
    }

    componentDidMount() {
        this.getSystemInfo()

        this.interval = setInterval(()=>{
            this.getSystemInfo(false)
        }, 30000)
    }

    componentWillUnmount(){
        if(this.interval){
            clearInterval(this.interval)
        }
    }

    getSystemInfo(loading=true) {
        if(loading) App.loading(true);
        return axios.request({
            url: '/control/control/getSystemInfo',
            method: 'GET',
        })

            .then(response => {
                if(loading) App.loading(false);
                response = response['data']['data'];
                var totalRam = Math.round( (response['total_ram'] / 1000000) *10 ) / 10;
                var totalSwap = Math.round( (response['total_swap'] / 1000000) *10 ) / 10;
              
                this.setState({
                    cpu: `${response['cpu']} `,
                    ram: `${response['ram']} `,
                    totalRam: `${totalRam}G`,
                    swap: `${response['swap'] } `,
                    totalSwap: `${totalSwap}G`,
                    disk: `${response['disk']}G`,
                    totalDisk: response['total_disk'] ,
                });
            })

            .catch((error) => {
                console.log(error);
                if(loading) App.loading(false);
                error_handle(error)
                return false;
            })
    }

    render() {
        return (
            <div className='p-grid dashboard' >
          
                <div className='p-col-12 p-lg-3 d-flex' >
                    <div className='box-cus systemInfo_box  systemInfo_box1 card' style={{ width: '100%' , padding : '10px' }}>
                        <div className='box-cus-title'>
                            <i className="pi pi-money-bill"></i>
                            <span className='box-cus-title'>CPU </span>

                        </div>
                        <div className='p-grid overview-detail'>

                            <div className="p-col-6">
                                <div className="overview-number" style={this.state.cpu <= 50 ? {color : 'limegreen'} : { color : 'red'} } >{`${this.state.cpu} %`}</div>
                                <div className="overview-subtext">Used</div>
                            </div>

                            <div className="p-col-6">
                                <div className="overview-number">100 %</div>
                                <div className="overview-subtext">Total</div>
                            </div>

                        </div>


                    </div>

                </div>

                <div className='p-col-12 p-lg-3 d-flex' >
                    <div className='box-cus systemInfo_box systemInfo_box2 card' style={{ width: '100%' , padding : '10px' }}>
                        <div className='box-cus-title'>
                            <i className="pi pi-money-bill"></i>
                            <span className='box-cus-title'>RAM </span>

                        </div>
                        <div className='p-grid overview-detail'>

                            <div className="p-col-6">
                                <div className="overview-number"style={this.state.ram <= 50 ? {color : 'limegreen'} : { color : 'red'} } >{`${this.state.ram} %`}</div>
                                <div className="overview-subtext">Used</div>
                            </div>

                            <div className="p-col-6">
                                <div className="overview-number">{this.state.totalRam}</div>
                                <div className="overview-subtext">Total</div>
                            </div>

                        </div>


                    </div>

                </div>

                <div className='p-col-12 p-lg-3 d-flex' >
                    <div className='box-cus systemInfo_box systemInfo_box3 card' style={{ width: '100%' , padding : '10px'}}>
                        <div className='box-cus-title'>
                            <i className="pi pi-money-bill"></i>
                            <span className='box-cus-title'>SWAP </span>

                        </div>
                        <div className='p-grid overview-detail'>

                            <div className="p-col-6">
                                <div className="overview-number" style={this.state.swap <= 50 ? {color : 'limegreen'} : { color : 'red'} }>{`${this.state.swap} %`}</div>
                                <div className="overview-subtext">Used</div>
                            </div>

                            <div className="p-col-6">
                                <div className="overview-number">{this.state.totalSwap}</div>
                                <div className="overview-subtext">Total</div>
                            </div>

                        </div>


                    </div>

                </div>

                <div className='p-col-12 p-lg-3 d-flex' >
                    <div className='box-cus systemInfo_box systemInfo_box4 card' style={{ width: '100%', padding : '10px'}}>
                        <div className='box-cus-title'>
                            <i className="pi pi-money-bill"></i>
                            <span className='box-cus-title'>DISK </span>

                        </div>
                        <div className='p-grid overview-detail'>

                            <div className="p-col-6">
                                <div className="overview-number">{this.state.disk}</div>
                                <div className="overview-subtext">Used</div>
                            </div>

                            <div className="p-col-6">
                                <div className="overview-number">{this.state.totalDisk}</div>
                                <div className="overview-subtext">Total</div>
                            </div>

                        </div>


                    </div>

                </div>



            </div>
        );
    }
}

export default SystemInfo;
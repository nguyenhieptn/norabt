import React, { Component } from 'react';

import '../Dashboard/index.scss'

import OrderTrack from '../../model/admin/Order_track';
import Order_track from '../../model/admin/Order_track';

import Ctrl from '../../model/control/Ctrl'
class OrderTracking extends Component {

    constructor(props) {
        super(props);
        this.state = {
            fear: 0,
            WMA45: 0,
            WMA451W: 0,
            RSI4h: 0,
            totalCoin: 0,
            message: null,

            cpu: 0,
            ram: 0,
            totalRam: 0,
            swap: 0,
            totalSwap: 0,
            disk: 0,
            totalDisk: 0,

        }
    }

    setData(data) {

        this.setState({
            fear: data
        });
    }

    setDataCoin(data) {

        var total_coin = data[PAGE_TOTAL];
        this.setState({
            totalCoin: total_coin
        })

        var row = data[DATA_TABLE].filter(row => row.order_track_symbol == 'BTCUSDT');
        if (row[0]) {
            var WMA45 = row[0][ORDER_TRACK_1D_RSI_WMA].toFixed(2);
            var WMA451W = row[0][ORDER_TRACK_1W_RSI_WMA].toFixed(2);
            var RSI4h = row[0][ORDER_TRACK_RSI4H_0].toFixed(2);

            this.setState({
                WMA45: WMA45,
                WMA451W: WMA451W,
                RSI4h: RSI4h,
            })
        }



    }


    getBTCData() {
        var model = new Order_track();
        model.read({ [ORDER_TRACK_SYMBOL]: 'BTCUSDT' }).then(res => {
            if (res['result']) {
                var data = res['data'];

                if (isset(data[0])) {
                    this.setState({
                        WMA45: data[0][ORDER_TRACK_1D_RSI_WMA].toFixed(2),
                        WMA451W: data[0][ORDER_TRACK_1W_RSI_WMA].toFixed(2),
                        RSI4h: data[0][ORDER_TRACK_RSI4H_0].toFixed(2),
                    })
                }
            }
        })
    }

    getSystemInfo(loading = true) {
        if (loading) App.loading(true);
        return axios.request({
            url: '/control/control/getSystemInfo',
            method: 'GET',
        })

            .then(response => {
                if (loading) App.loading(false);
                response = response['data']['data'];
                var totalRam = Math.round((response['total_ram'] / 1000000) * 10) / 10;
                var totalSwap = Math.round((response['total_swap'] / 1000000) * 10) / 10;

                this.setState({
                    cpu: `${response['cpu']} `,
                    ram: `${response['ram']} `,
                    totalRam: `${totalRam}G`,
                    swap: `${response['swap']} `,
                    totalSwap: `${totalSwap}G`,
                    disk: `${response['disk']}G`,
                    totalDisk: response['total_disk'],
                });
            })

            .catch((error) => {
                console.log(error);
                if (loading) App.loading(false);
                error_handle(error)
                return false;
            })
    }


    componentDidMount() {
        this.getBTCData();
        this.getSystemInfo()
        this.getBTCInterval = setInterval(() => { this.getBTCData(); this.getSystemInfo(false) }, 300000);

        var ctrl = new Ctrl();
        ctrl.get('volatility_alert_message', null).then(cfg => {

            this.setState({ message: cfg })

        });
    }

    componentWillUnmount() {
        if (this.getBTCInterval) {
            clearInterval(this.getBTCInterval);
        }
    }


    render() {
        return (
            <div className='p-grid dashboard mt-2' >

                <div className='p-col-12 p-lg-3 d-flex' >
                    <div className='box-cus box-2' style={{ width: '100%' }}>
                        <div className='box-cus-title'>
                            <i className="pi pi-shopping-cart"></i>
                            <span className='box-cus-title'>{`Fear & Greed`}</span>

                        </div>
                        <div className="overview-box-count ">{this.state.fear}</div>
                    </div>

                </div>

                <div className='p-col-12 p-lg-3 d-flex' >
                    <div className='box-cus box-1' style={{ width: '100%' }}>
                        <div className='box-cus-title'>
                            <i className="pi pi-money-bill"></i>
                            <span className='box-cus-title'>WMA45 1D/1W</span>

                        </div>
                        <div className="overview-box-count ">{this.state.WMA45} / {this.state.WMA451W}</div>
                    </div>

                </div>


                <div className='p-col-12 p-lg-3 d-flex' >
                    <div className='box-cus box-4' style={{ width: '100%'  }}>
                        <div className='box-cus-title'>
                            <i className="pi pi-chart-bar"></i>
                            {/* <span className='box-cus-title'>RSI 4H-BTC</span> */}
                            <span className='box-cus-title'>System Info</span>

                        </div>
                        {/* <div className="overview-box-count ">{this.state.RSI4h}</div> */}

                        <div className='row p-0 text-center' style={ App.isMobile() ? { fontSize: '15px' , marginTop : '25px' } : {fontSize: '15px'}}>
                            <div className='col-3 p-0'>
                                <div ><b>CPU</b></div>
                                <div><span style={this.state.cpu <= 50 ? {color : 'limegreen'} : { color : 'red'} }>{`${this.state.cpu} %`}</span> / 100%</div>
                            </div>
                            <div className='col-3 p-0'>
                                <span><b>RAM</b></span>
                                <div><span style={this.state.ram <= 50 ? {color : 'limegreen'} : { color : 'red'} }>{`${this.state.ram} %`}</span> / 100%</div>
                            </div>
                            <div className='col-3 p-0'>
                                <span><b>SWAP</b></span>
                                <div><span style={this.state.swap <= 50 ? {color : 'limegreen'} : { color : 'red'} }>{`${this.state.swap} %`}</span> / {this.state.totalSwap}</div>
                            </div>
                            <div className='col-3 p-0'>
                                <span><b>DISK</b></span>
                                <div>{this.state.disk} / {this.state.totalDisk}</div>
                            </div>
                        </div>
                    </div>
                </div>

                <div className='p-col-12 p-lg-3 d-flex' >
                    <div className='box-cus box-3' style={{ width: '100%' }}>
                        <div className='box-cus-title'>
                            <i className="pi pi-star-o"></i>
                            {/* <span className='box-cus-title' >Total Coin</span> */}
                            <span className='box-cus-title' >4H Order</span>

                        </div>
                        {/* <div className="overview-box-count ">{this.state.totalCoin}</div> */}
                        <div style={App.isMobile() ? { fontSize: '25px', marginTop: '15px' } : { fontSize: '17px' }} className="overview-box-count ">{this.state.message}</div>

                    </div>

                </div>
            </div>
        );
    }
}

export default OrderTracking;
import React, { Component } from 'react'
import '../../components/user/css/responsive.scss';
import { Link } from 'react-router-dom';


class PagesHome extends Component {
	
	constructor(props) {
        super(props);
        this.state = {
            vouchers: [],
        }
    }

    loadVoucher() {
        App.loading(true);
        axios({
            method: 'POST',
            url: '/user/pages/getVouchers',
            dataType: 'json',
            
        })
            .then(response => {
                App.loading(false);
                response = response.data;
                if (response['result']) {
                    this.setState({ vouchers: response['data'] });
                } else {
                    error_handle(response);
                }

            })
            .catch(error => {
                App.loading(false);
                console.log(error);
                error_handle(error.response);
            });
    }

    componentDidMount(){
        this.loadVoucher();
    }

    render(){
        if(this.state.vouchers.length == 0){
            return <div className='container box_padding'>
                <div className="alert alert-warning" role="alert">
                    Bạn đã sử dụng hết mã giảm giá
                </div>
            </div>
        }
        return <>
        <div className='container box_padding'>
            {this.state.vouchers.map(item => {
                return <Link to="/user/pages/home" key={item[VOUCHER_CODE]}><div className='box_shadow box_padding box_flex' style={{marginBottom:5}}>
                    <div>
                        <i className="fa fa-gift" style={{fontSize:42, color:'red', marginRight:15}}></i>
                    </div>
                    <div>
                        <div>Bạn nhận được mã giảm giá <b>{formatNumber(item[VOUCHER_VALUE])}&nbsp;VNĐ</b> khi mua các sản phẩm trên hệ thống.</div>
                        <div>Mã giảm giá: <b>{item[VOUCHER_CODE]}</b></div>
                        <div>Thời gian từ <b>{moment(item[VOUCHER_TIME], 'X').format(DATE_FORMAT)}</b> đến <b>{moment(item[VOUCHER_EXPIRE], 'X').format(DATE_FORMAT)}</b></div>
                    </div>
                </div></Link>
            })}
        </div>
        </>
    }
}
export default PagesHome
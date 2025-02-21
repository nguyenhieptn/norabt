import React, { Component } from 'react'
import Loading from '../common/Loading';
import {withRouter} from 'react-router-dom';


class SaleBanner extends Component {
    constructor(props) {
        super(props);
        this.id = makeId();

        this.state = {
            vouchers: [],
            search: '',
        }


    }



    loadVoucher() {
       
        axios({
            method: 'POST',
            url: '/user/pages/getVouchers',
            dataType: 'json',
            
        })
            .then(response => {
                response = response.data;
                if (response['result']) {
                    this.setState({ vouchers: response['data'] });
                } else {
                    error_handle(response);
                }

            })
            .catch(error => {
                console.log(error);
                error_handle(error.response);
            });
    }

    componentDidMount(){
        this.loadVoucher();
        $('#saleBanner').carousel()
    }

    render() {

        return <div id="saleBanner" className="carousel slide" data-ride="carousel" style={{marginTop:7}}>
            <ol className="carousel-indicators">
                
                {this.state.vouchers.map((item, key) => {
                    return <li key={key} data-target="#saleBanner" data-slide-to={key} className={key==0?'active':''}></li>
                })}
                <li data-target="#saleBanner" data-slide-to={this.state.vouchers.length} className={this.state.vouchers.length==0?'active':''}></li>
            </ol>
            <div className="carousel-inner">
                
                {this.state.vouchers.map((item, key) => {
                    return  <div key={key} className={`carousel-item ${key==0?'active':''}`} style={{backgroundImage: `url(${require("./images/sale_bg.png")})`, justifyContent:'center'}}>
                        <div className='box_flex box_padding' style={{paddingRight:'25%', height:'100%'}} onClick={()=>{this.props.history.push('/user/pages/vouchers')}}>
                            <div style={{color:'white', textAlign:'center'}}>
                                <div>Bạn được tặng một voucher giảm giá <strong>{formatNumber(item[VOUCHER_VALUE])} VNĐ</strong> khi mua bất kỳ mặt hàng nào trên hệ thống.</div>
                                <div><b>Từ {moment(item[VOUCHER_TIME], 'X').format('DD/MM')} đến {moment(item[VOUCHER_EXPIRE], 'X').format('DD/MM')}</b></div>
                            </div>
                        </div>
                    </div>
                })}
                <div onClick={()=>{this.props.history.push('/user/pages/vouchers')}} className={`carousel-item ${this.state.vouchers.length==0?'active':''}`} style={{backgroundImage: `url(${require("./images/firstSale.jpeg")})`}}></div>
            </div>
    <style>{`
        
    `}</style>
        </div>

    }
}

export default withRouter(SaleBanner);

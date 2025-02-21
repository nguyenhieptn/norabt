import React, { Component } from 'react'
import '../../components/user/css/responsive.scss';
import { Link } from 'react-router-dom';


class PagesHome extends Component {
	
	constructor(props) {
        super(props);
        this.state = {
            orders: [],
        }
    }

    loadOrders() {
        App.loading(true);
        axios({
            method: 'POST',
            url: '/user/pages/getOrders',
            dataType: 'json',
            
        })
            .then(response => {
                App.loading(false);
                response = response.data;
                if (response['result']) {
                    this.setState({ orders: response['data'] });
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
        this.loadOrders();
    }

    render(){
        if(this.state.orders.length == 0){
            return <div className='container box_padding'>
                <div className="alert alert-warning" role="alert">
                    Bạn không có đơn hàng nào
                </div>
            </div>
        }
        return <>
        <div className='container box_padding'>
            {this.state.orders.map(item => {
                var status = <b style={{color:'red'}}>Đã Đặt Hàng</b>;
                if(item[ORDER_STATUS] == ORDER_STATUS_PENDING)status = <b style={{color:'orange'}}>Đang xử lý</b>;
                if(item[ORDER_STATUS] == ORDER_STATUS_COMPLETED)status = <b style={{color:'green'}}>Hoàn thành</b>;
                if(item[ORDER_STATUS] == ORDER_STATUS_CANCEL)status = <b style={{color:'gray'}}>Đã hủy</b>;

                return <Link to={`/user/pages/product?id=${item[ORDER_PID]}`} key={item[ORDER_ID]}><div className='box_shadow box_padding box_flex' style={{marginBottom:5}}>
                    <div>
                        <i className="fa fa-shopping-cart" style={{fontSize:42, color:'#4CAF50', marginRight:15}}></i>
                    </div>
                    <div>
                        <div>Tên sản phẩm: <span>{item[ORDER_PNAME]}</span></div>
                        <div>Đơn giá: <b>{formatNumber(item[ORDER_PPRICE])}</b></div>
                        <div>Số lượng: <b>{item[ORDER_PNUMBER]}</b></div>
                        <div className='box_flex'>
                            <div style={{color:'gray', fontWeight:'bold', display: item[ORDER_VVALUE] == 0 ? 'none' : 'block', textDecoration: 'line-through' }}>{formatNumber(Number(item[ORDER_PPRICE]) * Number(item[ORDER_PNUMBER]))}&nbsp;VNĐ</div>
                            <div style={{color:  item[ORDER_VVALUE] == 0?'red':'green', fontWeight:'bold', marginLeft: 15}}>{formatNumber(Number(item[ORDER_PPRICE]) * Number(item[ORDER_PNUMBER]) - Number(item[ORDER_VVALUE]))}&nbsp;VNĐ</div>
                        </div>

                        <div>Trạng thái: {status}</div>
                        
                    </div>
                </div></Link>
            })}
        </div>
        </>
    }
}
export default PagesHome
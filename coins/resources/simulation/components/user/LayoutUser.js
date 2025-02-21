import React, { Component } from 'react'
import scss from '@root/assets/css/constants'
import { Link } from 'react-router-dom';

class LayoutUser extends Component {

	constructor(props) {
		super(props);
		this.state = {
			vouchers: 0,
			orders: 0,
		}
	}

	render() {
		return (

			<>

				<div className='main'>
					{this.props.children}
				</div>

				<div className='user_menu container' style={{padding:0}}>
					<div className={`box_flex button ${App.activeFunc == 'home' ? 'active' : ''}`}>
						<Link to='/user/pages/home/'><i className='fa fa-home'></i>&nbsp; Trang chủ</Link></div>
					<div className={`box_flex button ${App.activeFunc == 'vouchers' ? 'active' : ''}`}>
						<Link to='/user/pages/vouchers'><i className='fa fa-tags'></i>&nbsp; Mã giảm giá
							{this.state.vouchers > 0 ? <div className='quantity'>{this.state.vouchers}</div> : ''}
						</Link>
					</div>
					<div className={`box_flex button ${App.activeFunc == 'orders' ? 'active' : ''}`}>
						<Link to='/user/pages/orders'><i className='fa fa-shopping-cart'></i>&nbsp; Đơn hàng
							{this.state.orders > 0 ? <div className='quantity'>{this.state.orders}</div> : ''}
						</Link>
					</div>
				</div>

			</>
		);
	}

	loadInfo(){
		
        axios({
            method: 'POST',
            url: '/user/pages/getLayoutInfo',
            dataType: 'json',
            
        })
            .then(response => {
                
                response = response.data;
                if (response['result']) {
					var data = response['data'];
					this.setState({
						vouchers : data['vouchers'],
						orders: data['orders'],
					})
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
		this.loadInfo();
	}


}
export default LayoutUser

import React, { Component } from 'react'
import '../../components/user/css/responsive.scss';
import InputVoucherOption from '../../components/user/InputVoucherOption';
import {withRouter} from 'react-router-dom';



class PagesHome extends Component {
	
	constructor(props) {
        super(props);

        this.state = {
            product: {},
            mainImage: '',
            vouchers: {},
            voucher: 0,
            quantity: 1,
            venders: {},
            note: '',
        }

        this.pid = get(App.parsed['id'], '');
    }

    componentDidMount(){
        this.loadProduct();
        this.loadMapping();
    }

    loadMapping(){
        axios({
            method: 'POST',
            url: '/user/pages/getProductMapping',
            dataType: 'json',
            data: {
                [PRODUCT_ID]: this.pid
            }
        })
            .then(response => {
                App.loading(false);
                response = response.data;
                if (response['result']) {
                    
                    var data = response['data']
                    this.setState({ 
                        vouchers: data[VOUCHERS_TABLE],
                        venders: data[VENDERS_TABLE],
                    });
                    
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

    loadProduct(){
        App.loading(true);
        axios({
            method: 'POST',
            url: '/user/pages/getProduct',
            dataType: 'json',
            data: {
                [PRODUCT_ID]: this.pid
            }
        })
            .then(response => {
                App.loading(false);
                response = response.data;
                if (response['result']) {
                    if(isset(response['data'][0])){
                        this.setState({ 
                            product: response['data'][0] ,
                            mainImage: response['data'][0][PRODUCT_IMAGE],
                        });
                    }
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

    loadProduct(){
        App.loading(true);
        axios({
            method: 'POST',
            url: '/user/pages/getProduct',
            dataType: 'json',
            data: {
                [PRODUCT_ID]: this.pid
            }
        })
            .then(response => {
                App.loading(false);
                response = response.data;
                if (response['result']) {
                    if(isset(response['data'][0])){
                        this.setState({ 
                            product: response['data'][0] ,
                            mainImage: response['data'][0][PRODUCT_IMAGE],
                        });
                    }
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


    order(){
        App.loading(true);
        axios({
            method: 'POST',
            url: '/user/pages/order',
            dataType: 'json',
            data: {
                [ORDER_PID]: this.pid,
                [ORDER_PNUMBER]: this.state.quantity,
                [ORDER_VCODE]: this.voucherInput.getValue(),
                [ORDER_NOTE]: this.state.note,
            }
        })
            .then(response => {
                App.loading(false);
                response = response.data;
                if (response['result']) {
                    swal({
                        html: response['data'],
                        showCloseButton: false,
                        showCancelButton: false,
                        showConfirmButton: true,
                        onClose: ()=>{this.props.history.push('/user/pages/home');}    
                    }).then( ()=>{
                        
                    });
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


    render(){
        console.log(this.state.product);
        if(!isset(this.state.product[PRODUCT_ID])) return '';

        var vender = this.state.venders[this.state.product[PRODUCT_VENDER]];
        var venderName = vender? vender[VENDER_NAME]: '';
        var venderImg = vender? file_public(vender[VENDER_IMAGE]): '';


        if(this.state.product[PRODUCT_PROMOTION] != '' && this.state.product[PRODUCT_PROMOTION] != null){
            var listPromotion = this.state.product[PRODUCT_PROMOTION].split("\n");

            var productPromotion = <div className='box_border' style={{borderColor: '#ccc', borderRadius:5, marginTop:10}}>
                <div style={{borderBottom:'solid thin #ccc', padding:5, background:'#eee', fontWeight:'bold'}}>Khuyến mãi áp dụng</div>
                <div className='box_padding'>
                    {listPromotion.map((item, key) => <div key={key} style={{padding:'3px 0px'}}>
                        <i className="fa fa-check-square" style={{color:'green'}}></i>
                        <div style={{display:'inline-block', paddingLeft:5}}>{item}</div>
                    </div>)}
                </div>
            </div>
        }else{
            var productPromotion = '';
        }
                    

        return <div className='container product_page' style={{padding:0}}>

        <div className='row'>
            <div className='col-md-6'>
                <div className='product_page_image_frame'>
                    <div><div className='box_line title'>{this.state.product[PRODUCT_NAME]}</div></div>
                    <div className='product_page_image_active'>
                        <img style={{width:'80%', height:'100%', objectFit:'contain'}} src = {this.state.mainImage == '' ? '' : file_public(this.state.mainImage)}></img>
                    </div>
                    <div className='box_flex' style={{justifyContent:'center'}}>
                        <div className={`product_page_image_child box_shadow ${this.state.product[PRODUCT_IMAGE] == this.state.mainImage ? 'active': ''}`}
                            onClick={()=>{this.setState({mainImage: this.state.product[PRODUCT_IMAGE]})}}
                        >
                            <img style={{width:'100%', height:'100%', objectFit:'contain'}} src={file_public(this.state.product[PRODUCT_IMAGE])}></img>
                        </div>
                        {this.state.product[PRODUCT_IMAGES_TABLE].map(item => {
                            return <div key={item[PRODUCT_IMG_ID]} className={`product_page_image_child box_shadow ${item[PRODUCT_IMG_PATH] == this.state.mainImage ? 'active': ''}`}
                                        onClick={()=>{this.setState({mainImage: item[PRODUCT_IMG_PATH]})}}
                                    >
                                        <img style={{width:'100%', height:'100%', objectFit:'contain'}} src={file_public(item[PRODUCT_IMG_PATH])}></img>
                                </div>
                        })}
                    </div>
                </div>

                

            </div>
            <div className='col-md-6'>

                <div>
                    <div className='product_item_name' title={this.state.product[PRODUCT_NAME]}><b>{this.state.product[PRODUCT_NAME]}</b></div>
                    <div>Mã Sản phẩm: <strong>{this.state.product[PRODUCT_MODEL]}</strong></div>
                    <div>Đơn giá: <strong>{formatNumber(this.state.product[PRODUCT_PRICE_REAL])}&nbsp;VNĐ</strong></div>
                    {this.state.product[PRODUCT_STATUS] == PRODUCT_STATUS_CONHANG
                        ? <strong style={{color:'green'}}>Còn hàng</strong>
                        : <strong style={{color:'red'}}>Hết hàng</strong>
                    }
                    <div className='box_flex' style={{margin:'5px 0px'}}>Hãng sản xuất:&nbsp;
                        {venderImg == ''? '' : <img style={{height:20}} src={venderImg}></img>}
                        <b>&nbsp;{venderName}</b>
                    </div>

                    {productPromotion}
            
                    <div style={{marginTop:10}}><strong>Số lượng </strong></div>
                    <div className='box_flex'>
                        <div  className='button' style={{background:'#ccc', padding:5, borderRadius:5, fontWeight:'bold', color:'white',  width:30, textAlign:"center"}}
                        onClick = {()=>{if(this.state.quantity > 1) this.setState({quantity: Number(this.state.quantity) - 1})}}
                        >-</div>
                        <input className='input_item_input' style={{width:50, margin:'0px 5px'}} type='number' min="0" value={this.state.quantity} onChange={(e)=>this.setState({quantity: e.target.value})}></input>
                        <div className='button' style={{background:'#ccc', padding:5, borderRadius:5,  fontWeight:'bold', color:'white', width:30, textAlign:"center"}}
                        onClick = {()=>{this.setState({quantity: Number(this.state.quantity) + 1})}}
                        >+</div>
                    </div>
                    
                    <div style={{marginTop:10}}><strong>Thanh Toán</strong></div>
                    <div className='box_flex'>
                        <div style={{color:'gray', fontWeight:'bold', fontSize:'medium', display: this.state.voucher == 0 ? 'none' : 'block', textDecoration: 'line-through' }}>{formatNumber(Number(this.state.product[PRODUCT_PRICE_REAL]) * Number(this.state.quantity))}&nbsp;VNĐ</div>
                        <div style={{color: this.state.voucher == 0?'red':'green', fontWeight:'bold', fontSize:'large', marginLeft: 15}}>{formatNumber(Number(this.state.product[PRODUCT_PRICE_REAL]) * Number(this.state.quantity) - Number(this.state.voucher))}&nbsp;VNĐ</div>
                    </div>
                    <div className='box_flex'>
                        <InputVoucherOption onApply={(voucher)=>{this.setState({
                            voucher: voucher[VOUCHER_VALUE],
                        })}} className='input_item_input' placeholder="Mã Giảm Giá" option={this.state.vouchers} ref={c=>this.voucherInput = c}></InputVoucherOption>
                        <div className='button btn btn-danger' onClick={()=>{this.order()}}>Đặt Hàng</div>
                    </div>

                    <div style={{marginTop:10}}><textarea className='input_item_input' style={{width:'100%'}} placeholder='Ghi chú của bạn' value={this.state.note} onChange={e=>this.setState({note:e.target.value})}></textarea></div>
                </div>

            </div>
        </div>

        <div className='box_padding'>
            <div className='box_flex title'><i className="fa fa-cog"></i>&nbsp;<strong>Thông số kỹ thuật:</strong></div>
            <table className='table table-bordered table-striped'>
                <thead>
                    <tr>
                        <th>STT</th>
                        <th style={{whiteSpace: 'nowrap'}}>Tên Tham số</th>
                        <th>Giá trị</th>
                    </tr>
                </thead>
                <tbody>
                    {this.state.product[SPECIFICATIONS_TABLE].map((item, key) => {
                        return <tr key={key}>
                            <td>{key+1}</td>
                            <td>{item[SPECT_NAME]}</td>
                            <td>{item[SPECT_VALUE]}&nbsp;{item[SPECT_UNIT]}</td>
                        </tr>
                    })}
                </tbody>
            </table>
        </div>

        <div className='box_padding'>
            <div className='box_flex title'><i className="fa fa-book"></i>&nbsp;<strong>Mô tả sản phẩm</strong></div>
            <div className='ck-content' dangerouslySetInnerHTML={{ __html: output_secure(get(this.state.product[PRODUCT_DESCRIPTION], ''))}}></div>
        </div>
        
        </div>

        
    }
}
export default withRouter(PagesHome)
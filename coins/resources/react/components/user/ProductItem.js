import React, { Component } from 'react';
import { Link } from "react-router-dom";

class ProductItem extends Component {

    constructor(props) {
        super(props);
    }

    render() {
        var item = this.props.product;
        return <div className='product_item'>
            <Link to={`/user/pages/product?id=${item[PRODUCT_ID]}`}><div className='box_shadow box_flex box_padding'>

                <div className='product_item_image'>
                    <img src={file_public(item[PRODUCT_IMAGE])}></img>
                </div>

                <div style={{ marginLeft: 15, width:'80%' }}>
                    <div className='product_item_name box_line' title={item[PRODUCT_NAME]}>{item[PRODUCT_NAME]}</div>
                    <div>Mã Sản phẩm: <strong>{item[PRODUCT_MODEL]}</strong></div>
                    <div style={{ color: 'red' }}>{formatNumber(item[PRODUCT_PRICE_REAL])}VNĐ</div>
                </div>
                <div style={{position:'absolute', bottom:15, right:15}}>
                    {item[PRODUCT_STATUS] == PRODUCT_STATUS_CONHANG
                        ? <strong style={{color:'green'}}>Còn hàng</strong>
                        : <strong style={{color:'red'}}>Hết hàng</strong>
                    }
                </div>
            </div>
            </Link>
        </div>
    }
}

export default ProductItem
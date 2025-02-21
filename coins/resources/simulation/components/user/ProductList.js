import React, { Component } from 'react';
import { Link } from "react-router-dom";
import ProductItem from './ProductItem';
class ProductList extends Component {

    constructor(props) {
        super(props);
        this.state = {
            products : []
        }
    }

    filter(filterVender, filterSpects, productType, orderPrice){
        App.loading(true);
        axios({
            method: 'POST',
            url: '/user/pages/productFilter',
            dataType: 'json',
            data: {
                [PRODUCT_VENDER]: filterVender, 
                [PRODUCT_TYPE]: productType,
                spects: filterSpects,
                price : orderPrice
            }
            
        })
        .then(response => {
            App.loading(false);
            response = response.data;
            if (response['result']) {
                this.setState({products: response['data']})
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

    render() {
        
        return <div className='product_list' style={{marginTop:15}}>
            {this.state.products.map(item => <ProductItem key={item[PRODUCT_ID]} product={item}></ProductItem>)}
        </div>
    }
}

export default ProductList
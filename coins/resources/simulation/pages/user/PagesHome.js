import React, { Component } from 'react'
import SearchProductBox from '../../components/user/SearchProduct';
import SaleBanner from '../../components/user/SaleBanner';
import '../../components/user/css/responsive.scss';
import ProductTypes from '../../components/user/ProductTypes';
import ProductFilter from '../../components/user/ProductFilter';
import ProductList from '../../components/user/ProductList';


class PagesHome extends Component {
	
	constructor(props) {
        super(props);
    }

    render(){
        return <>
        <div className='container box_padding'>
            <SearchProductBox></SearchProductBox>
            <SaleBanner></SaleBanner>
            <ProductTypes onClick={(item)=>{
                this.productFilter.setProductType(item)
            }}></ProductTypes>
            <ProductFilter ref={c=>this.productFilter = c} onChange={(filterVender, filterSpects, productType, price)=>{
                this.productList.filter(filterVender, filterSpects, productType, price);
            }}></ProductFilter>
            <ProductList ref={c=>this.productList = c}></ProductList>
        </div>
        </>
    }
}
export default PagesHome
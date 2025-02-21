import React, { Component } from 'react'
import Loading from '../common/Loading';
import { Link } from 'react-router-dom';


class SearchProduct extends Component {
    constructor(props) {
        super(props);
        this.id = makeId();

        this.state = {
            products : [],
            search: '',
        }

        this.searchProductProccess = null;
    }

    onChangeHandle(e){
        this.setState({search: e.target.value}, ()=>{this.searchProduct()})
    }

    searchProduct(){
        if(this.searchProductProccess) clearTimeout(this.searchProductProccess);
        this.searchProductProccess = setTimeout(()=>{this.loadProduct()}, 500);
    }

    loadProduct(){
        this.loader.loading(true)
        axios({
			method: 'POST',
            url: '/user/pages/search',
            dataType: 'json',
            data: {
               search: this.state.search,
            }
            })
			.then(response => {
                this.loader.loading(false);
                response = response.data;
                if(response['result']){
                    this.setState({products: response['data'].slice(0,10)});
                }else{
                    error_handle(response);
                }
                
			})
			.catch(error => {
                this.loader.loading(false);
                console.log(error);
                error_handle(error.response);
		});
    }

    onSelectProduct(Product){
        
    }

    render() {

        return <div style={{position:'relative'}}>
            
            <input id='search_Product_input' onFocus={()=>{this.loadProduct()}} type='text' style={{width: '100%', padding:5, border:'solid thin #ccc', borderRadius:5}} placeholder="Tìm kiếm Sản phẩm" value={this.state.search} onChange={(e)=>this.onChangeHandle(e)}></input>
            
            <div id="search_Product_suggest">
                {this.state.products.map(item => {
                    return <Link to={`/user/pages/product?id=${item[PRODUCT_ID]}`} key={item[PRODUCT_ID]}><div className='box_flex button product_suggest_item' onClick={()=>{this.onSelectProduct(item)}}>
                        <div style={{padding:5}}><img src={file_public(item[PRODUCT_IMAGE])}></img></div>
                        <div>
                            <div className='box_line'><b>{item[PRODUCT_NAME]}</b></div>
                            <div style={{color:'red', fontSize:10}}>{formatNumber(item[PRODUCT_PRICE_REAL])} VNĐ</div>
                        </div>
                    </div></Link>
                })}
                <Loading ref={c=>this.loader=c} style={{position:'absolute'}}></Loading>
            </div>
            <style>{`
                #search_Product_input:focus ~ #search_Product_suggest{
                    display: block;
                    padding: 5px;
                }
                #search_Product_input ~ #search_Product_suggest:hover{
                    display: block;
                }
                #search_Product_input ~ #search_Product_suggest{
                    display: none;
                    position: absolute;
                    border-radius: 5px;
                    border: solid thin #ccc;
                    top: 100%;
                    left: 0px;
                    right:0px;
                    z-index: 1;
                    background: white;
                    min-height: 100px;
                    max-height: 500px;
                    overflow-y: auto;
                    overflow-x: hidden;
                }
                .product_suggest_item img{
                    width: 30px;
                }
                .product_suggest_item {
                    padding: 5px;
                }
            `}</style>

        </div>

    }
}

export default SearchProduct;

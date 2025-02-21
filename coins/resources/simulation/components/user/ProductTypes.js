import React, { Component } from 'react'


class ProductTypes extends Component {
    constructor(props) {
        super(props);
        this.id = makeId();

        this.state = {
            types: [],
        }
        
        this.currentProductType = get(App.currentProductType, 0);

    }

    loadTypes() {

        axios({
            method: 'POST',
            url: '/user/pages/getProductTypes',
            dataType: 'json',
            
        })
            .then(response => {
               
                response = response.data;
                if (response['result']) {
                    this.setState({ types: response['data'] });
                    if(response['data'][this.currentProductType]) this.onClickHandle(response['data'][this.currentProductType]);
                    if(this.props.onLoad) this.props.onLoad(response['data']);
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
        this.loadTypes();
    }

    onClickHandle(item){
        if(this.props.onClick) this.props.onClick(item);
    }

    render() {

        return <div className='product_types_frame' style={{display:'flex'}}>
            {this.state.types.map((item, key) => {
                return <div key={item[PRODUCT_TYPE_ID]} className='product_type_item box_shadow button' onClick={()=>{
                        this.onClickHandle(item);
                        App.currentProductType = key;
                    }}>
                    <div className='product_type_image' style={{backgroundImage:`url(${file_public(item[PRODUCT_TYPE_IMAGE])})`}}></div>
                    <div className='product_type_title'>{item[PRODUCT_TYPE_NAME]}</div>
                </div>
            })}
        </div>

    }
}

export default ProductTypes;

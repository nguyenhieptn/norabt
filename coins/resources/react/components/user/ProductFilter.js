import React, { Component } from 'react'
import Input from '../input/Input';


class ProductFilter extends Component {
    constructor(props) {
        super(props);
        this.id = makeId();

        var state = {
            type: {},

            venderOptions: {},
            spectOptions: {},

            price: 'asc',
            filter: false,

            filterVender: '',
            filterSpects: {},
        }

        this.state = get(App.currentFilterState, state);
        console.log('save filter');

        this.struct = [];

        this.closeFilterBar = this.closeFilterBar.bind(this);

    }

    setProductType(type){
        
        if(type[PRODUCT_TYPE_ID] == this.state.type[PRODUCT_TYPE_ID]){
            this.onChangeHandle();
            this.setTemplate(type[PRODUCT_TYPE_TEMPLATE]);
        }else{
            this.setState({
                type: type,
                filter: false,
                price: 'asc',
                filterVender: '',
                filterSpects: {},
            }, ()=>{
                this.setTemplate(type[PRODUCT_TYPE_TEMPLATE]);
                this.onChangeHandle();
            });
        }
        
    }

    setTemplate(template){
        this.struct = global.templates[template] ? global.templates[template]: [];
        this.loadSuggest();
    }

    loadSuggest(){
       
        axios({
            method: 'POST',
            url: '/user/pages/getSuggest',
            dataType: 'json',
            data: {
                [PRODUCT_TYPE_ID]: this.state.type[PRODUCT_TYPE_ID],
                spects: this.struct,
            }
            
        })
            .then(response => {
               
                response = response.data;
                if (response['result']) {
                    this.setState({
                        venderOptions: response['data']['venderOptions'],
                        spectOptions: response['data']['spectOptions'],
                        
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



    onChangeHandle(){
        if(this.props.onChange) this.props.onChange(
            this.state.filterVender, 
            this.state.filterSpects, 
            this.state.type[PRODUCT_TYPE_ID],
            this.state.price,
        )

        this.setState({filter: false}, ()=>{App.currentFilterState = this.state});
       

    }

    handleFilterBar(event){
        var newState = !this.state.filter;
        this.setState({filter: newState});
        if(newState){
            window.addEventListener('click', this.closeFilterBar);
        }
        event.stopPropagation();
    }

    closeFilterBar(event){
        if(event.target.closest(".product_filter_template") == null){
            this.setState({filter: false});
            window.removeEventListener('click', this.closeFilterBar);
            event.stopPropagation();
            event.preventDefault();
        }
    }

    componentWillUnmount(){
        window.removeEventListener('click', this.closeFilterBar);
    }

    
    render() {

        return <div className='product_filter_frame' style={{paddingTop:15}}>
            <div className='box_flex'>
                {/* <div className='product_type_image' style={{backgroundImage: `url(${file_public(this.state.type[PRODUCT_TYPE_IMAGE])})`}}></div> */}
                <div className='product_type_title box_line' >{this.state.type[PRODUCT_TYPE_NAME]}</div>

                <div className='box_flex product_type_control' style={{margin:'auto 0px auto auto'}}>
                    <div className='box_flex button' onClick={()=>{this.setState({price: this.state.price == 'asc'?'desc':'asc'}, ()=>{this.onChangeHandle()})}}>
                        <i className={this.state.price == 'asc' ? 'fa fa-long-arrow-down' : 'fa fa-long-arrow-up'}></i>&nbsp; Giá</div>
                    <div className='box_flex button' onClick={(e)=>{this.handleFilterBar(e)}}>
                        <i className="fa fa-filter"></i>&nbsp; Lọc</div>
                </div>
            </div>
           
            <div className='product_filter_template' style={{display: this.state.filter ? 'flex': 'none'}}>
                <div style={{margin:5}}>
                    <select className='input_item_input' value={this.state.filterVender} onChange={(e)=>{this.setState({filterVender: e.target.value}, ()=>{this.onChangeHandle()} )}}>
                        <option value=''>-- Lựa chọn Hãng --</option>
                        {Object.keys(this.state.venderOptions).map(key => <option key={key} value={key}>{this.state.venderOptions[key]}</option>)}
                    </select>
                </div>
                {this.struct.map(item => {
                    var suggest = this.state.spectOptions[item.name]? this.state.spectOptions[item.name] : [];
                    return <div key={item.name} style={{margin:5}}>
                                <select className='input_item_input' value={isset(this.state.filterSpects[item.name])? this.state.filterSpects[item.name] : '' } onChange={(e)=>{
                                        var filterSpects = this.state.filterSpects;
                                        if(e.target.value == ''){
                                            delete(filterSpects[item.name])
                                        }else{
                                            filterSpects[item.name] = e.target.value;
                                        }
                                        this.setState({filterSpects}, ()=>{this.onChangeHandle()} )
                                    }}>
                                    <option value=''>-- {item.name} --</option>
                                {suggest.map(key => <option key={key} value={key}>{key} {item.unit?`(${item.unit})`: ''}</option>)}
                                </select>
                            </div>
                })}

                <div style={{margin:5}}>
                    <div className='button btn btn-info'  style={{padding:'3px 5px'}} onClick={()=>{this.setState({
                        filterVender: '', filterSpects: {}
                    }, ()=>{this.onChangeHandle()} )}}>Xóa Lọc</div>
                </div>

            </div>
    <style>{`
        .product_filter_template{
            flex-wrap: wrap;
            display: none;
            position: absolute;
            border-radius: 5px;
            border: solid thin #ccc;
            top: 100%;
            left: 0px;
            right:0px;
            z-index: 1;
            background: #eeea;
            overflow-y: auto;
            overflow-x: hidden;
        }
        .product_filter_frame .button{
            padding: 5px;
        }
        .product_filter_frame .product_type_image{
            width: 32px;
            height: 32px;
            background-size: contain;
            background-repeat: no-repeat;
            background-position: center;
            margin-bottom: 5px;
        }
        .product_filter_frame .product_type_title{
            margin-left: 10px;
            font-weight: bold;
            font-size: 18px;
            color: #ff9800;
        }

        .product_filter_frame .product_type_control{
            color: #ff9800;
        }

        .product_filter_frame{
            position: relative;
        }
    `}</style>
        </div>

    }
}

export default ProductFilter;

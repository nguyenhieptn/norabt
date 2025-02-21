import React, { Component } from 'react'
import {Link} from 'react-router-dom'

class SpectMenu extends Component {
	
	constructor(props) {
	    super(props);
	    
    }
    
    onClickHandle(i){
        console.log(i);
        if(this.props.onClick) this.props.onClick(i);
    }
    render(){
        var active = this.props.active
        return <><div style={{width:'100%', justifyContent:'flex-end'}} className='box_flex multi_access_menu'>
            <div className={`box_flex multi_access_menu_item button ${active == 1 ? 'active': ''}`} onClick={()=>this.onClickHandle(1)}><i className='fa fa-cubes'></i>&nbsp; Thống số kỹ thuật</div>
            <div className={`box_flex multi_access_menu_item button ${active == 2 ? 'active': ''}`} onClick={()=>this.onClickHandle(2)}><i className='fa fa-id-card-o'></i>&nbsp; Mô tả sản phẩm</div>
        </div>
    <style>{`
        .multi_access_menu_item.button {
            padding: 2px 10px;
            background: #0d274d;
            color: white;
            margin-left: 4px;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
            border: solid 2px #0d274d;
        }

        .multi_access_menu_item.button.active {
            background: white;
            color: unset;
            position: relative;
        }

        .multi_access_menu_item.button.active::after {
            content: '';
            position: absolute;
            height: 8px;
            left: 0px;
            right: 0px;
            bottom: -8px;
            z-index: 1;
            background: white;
        }


        .multi_access_menu {
            border-bottom: solid medium #0d274d;
        }
    `}</style>
        </>
    }
}
export default SpectMenu

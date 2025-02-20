import React, { Component } from 'react'

class ContextMenu extends Component {

	constructor(props) {
		super(props);
		this.state = {
            content : this.props.children,
            show : false,
            top: null,
            bottom: null,
            right: null,
            left: null,
		}
        this.id = makeId();
        this.hide = this.hide.bind(this);
    }


    show(event){
        event.preventDefault();
        event.stopPropagation();
        var x = event.clientX;     
        var y = event.clientY;
        var width = window.innerWidth;
        var height = window.innerHeight;
        var cor = {};
        if(x > (width/2)){
            cor.left = x;
            cor.right = null;
        }else{
            cor.right = width - x;
            cor.left = null;
        }

        if(y > (height/2)){
            cor.bottom = height - y; 
            cor.top = null;
        }else{
            cor.top = y;
            cor.bottom = null;
        }

        this.setState({...cor, show: true});
        document.addEventListener('click', this.hide);
    }

    hide(){
        this.setState({show:false});
        document.removeEventListener('click', this.hide);
    }

    setMenu(content){
        this.setState({content})
    }

    componentDidMount(){
        App.ContextMenu = this;
        
    }

    componentWillUnmount(){
        
    }

    render(){
        var style = {display: (this.state.show?'block':'none'), position:'fixed', zIndex:2000};
        if(this.state.top != null) style.top = this.state.top;
        if(this.state.bottom != null) style.bottom = this.state.bottom;
        if(this.state.right != null) style.right = this.state.right;
        if(this.state.left != null) style.left = this.state.left;
        return <div style={style}
            >
            {this.state.content}
        </div>
    }
}

export default ContextMenu

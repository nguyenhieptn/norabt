import React, { Component } from 'react';
import Lab_account from '../../model/admin/Lab_account'
import folder from'../../../assets/img/folder.webp';
class Lab_account_groupView extends Component {

    constructor(props) {
        super(props);
        this.state = {
            group: {}
        }

        this.model = new Lab_account()
    }


    componentDidMount() {
    

        this.model.getGroup().then(res => {
     

            let temp = {}
            Object.keys(res['data']).map(item => {
                if(item != ''){
                    temp[item] = res['data'][item]
                }
            })

            this.setState({
                group: temp
            });
        })
    }
    click(item){
        window.location.href = App.link('/admin/lab_account/view?group=' + item)
    }
    changeGroupnameFu(newGr, oldGr){
        return this.model.changeGroupName(newGr, oldGr)
    }


    render() {
        return (
            <div style={{ display : 'flex' , flexWrap : 'wrap'}}>
                {
                    Object.keys(this.state.group).map(item => {
                        return (
                            <GroupFolder key={item} name={item} onClick={this.click.bind(this)} onChangeFolder={(newGr, oldGr)=>{ return this.changeGroupnameFu(newGr,oldGr)}}></GroupFolder>
                        )
                    })
                }
            </div>
        );
    }
}

export default Lab_account_groupView;


class GroupFolder extends Component {
    constructor(props) {
        super(props);
        this.state = {
            name: this.props.name,
            edit: false,
        }
        this.originName = this.props.name
    }

    onBlur(){
        if(this.state.name == this.originName){
            this.setState({edit:false});
            return;
        }
        if(this.props.onChangeFolder){
            this.props.onChangeFolder(this.state.name, this.originName).then(res => {
                if(!res['result']){
                    this.setState({name: this.originName})
                }else{
                    this.originName = this.state.name
                    this.setState({edit: false})
                }
            })
        }
    }

    render() {
        return (
            
            <div style={{ marginRight : '30px', cursor : 'pointer'}} >
                <img onClick={() => this.props.onClick(this.state.name)}  src={folder} style={{width : '100px', cursor:'pointer'}}  alt="fireSpot"/>
                {this.state.edit 
                ?<div><input ref={c => this.input = c} className='input' type="text" value={this.state.name} onChange={(e)=>this.setState({name: e.target.value})} onBlur={()=>{this.onBlur()}}></input></div> 
                :<div style={{ textAlign : 'center' , cursor:'pointer'}} onDoubleClick={()=>{this.setState({edit: true}, ()=>{
                    this.input.focus()
                })}}>{this.state.name}</div>}
            </div>
                        
        );
    }
}
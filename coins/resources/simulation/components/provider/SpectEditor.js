import React, { Component } from 'react'
import AddSpectModal from './AddSpectModal';
import CopySpectModal from './CopySpectModal';

class SpectEditor extends Component {
    constructor(props) {
        super(props)

        this.state = {
            values : {}
        }

        this.struct = []
        this.pid = this.props.pid;

    }

    setTemplate(template){
        this.struct = global.templates[template] ? global.templates[template]: [];
        this.loadValue();
    }

    loadValue(){
        if(this.pid == undefined) return; 
        return axios.request({
            url: '/provider/specifications/read',
            method: 'post',
            data: {
                [PRODUCT_ID]: this.pid,
            }
        })

            .then(response => {
                App.loading(false, 'Adding...');
                response = response['data'];
                if(response['result']){
                    this.setValues(response['data']);
                    return true;
                }
                return Promise.reject(response);
            })

            .catch((error)=> {
                console.log(error);
                App.loading(false, 'Adding...');
                error_handle(error)
                return Promise.reject();
            })
    }

    getValues(){
        return Object.values(this.state.values);
    }

    setValues(values){
        var struct = {};
        this.struct.map(item => struct[item.name] = item);
        
        var valuesIndex = {};
        values.map(item => {
            if(!struct[item[SPECT_NAME]]){
                struct[item[SPECT_NAME]] = {
                    name : item[SPECT_NAME],
                    type : 'text',
                    weight: item[SPECT_WEIGHT],
                    unit: '',
                }
            }else{
                struct[item[SPECT_NAME]].weight = item[SPECT_WEIGHT]
            }

            valuesIndex[item[SPECT_NAME]] = item;
        });
        struct = Object.values(struct);
        struct = struct.sort((a, b) => Number(a.weight) - Number(b.weight));
        this.struct = struct;

        this.setState({values: valuesIndex});
    
    }

    changeValue(item, value){
        var values = this.state.values;
        values[item.name] = {
            [SPECT_NAME] : item.name,
            [SPECT_VALUE]: value,
            [SPECT_WEIGHT]: item.weight,
            [SPECT_UNIT]: item.unit,
        }
        this.setState({values});
    }

    addSpect(name){
        this.struct.push({
            name: name,
            type : 'text',
            weight: this.struct.length + 1,
            unit: '',
        });
        this.struct = this.struct.sort((a, b) => Number(a.weight) - Number(b.weight));
        this.forceUpdate();
    }

    changeOrder(item, value){
        item.weight = value;
        this.struct = this.struct.sort((a, b) => Number(a.weight) - Number(b.weight));
        this.forceUpdate();
    }

    onDelete(key, name){
        this.struct.splice(key, 1);
        var values = this.state.values;
        delete(values[name]);
        this.setState({values});
    }

    componentDidMount(){
        this.loadValue();
    }

    render(){
       
        return <div style={{width:'100%'}}>
            <div className='box_flex' style={{justifyContent:'flex-end'}}>
                <div className='button btn btn-xs btn-primary' onClick={()=>this.copySpectModal.modal()}>Copy tham số</div>&nbsp;
                <div className='button btn btn-xs btn-primary' onClick={()=>this.addSpectModal.modal()}>Thêm thống số</div>&nbsp;
            </div>
            <br/>
            <table className='table table-bordered main_table'>
                <thead><tr><th>Tên tham số</th><th>Giá trị</th><th>Thứ tự</th><th></th></tr></thead>
                <tbody>
                    {this.struct.map((item, key) => {
                        var value = this.state.values[item.name] == undefined ? '' : this.state.values[item.name][SPECT_VALUE];
                        var inputComp = <input className='input_item_input' style={{width:'100%'}} type='text' value={value} onChange={(e)=>this.changeValue(item, e.target.value)}></input>
                        if(item.type == 'number')  inputComp = <input className='input_item_input' style={{width:'100%'}} type='number' value={value} onChange={(e)=>this.changeValue(item, e.target.value)}></input>
                        if(item.type == 'select')  inputComp = <select className='input_item_input' style={{width:'100%'}} value={value} onChange={(e)=>this.changeValue(item, e.target.value)}>
                            <option value=''>-- {item.name} --</option>
                            {item.options.map(option => <option key={option} value={option}>{option}</option>)}
                        </select>

                    return <tr key={item.name}>
                        <td style={{whiteSpace:'nowrap'}}>{item.name}&nbsp;{item.unit? `(${item.unit})`: ''}</td>
                        <td>{inputComp}</td>
                        <td style={{textAlign:'center'}}><input className='input_item_input' style={{width: 100}} type='number' value={item.weight} onChange={(e)=>{this.changeOrder(item, e.target.value)}}></input></td>
                        <td style={{textAlign:'center'}}><div className='button btn btn-xs btn-danger' onClick={()=>this.onDelete(key, item.name)}>Xóa</div>&nbsp;</td>
                        </tr>
                    })}
                </tbody>
            </table>

            <AddSpectModal ref={c => this.addSpectModal = c} onClick={(name)=>this.addSpect(name)}></AddSpectModal>
            <CopySpectModal ref={c => this.copySpectModal = c} onCopy={(data)=>{this.setValues(data)}}></CopySpectModal>
            
        </div>
    }
}

export default SpectEditor
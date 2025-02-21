import React, { Component } from 'react'

class InputVoucherOption extends Component {
	
	constructor(props) {
		super(props);
		
		this.id = makeId();
	    
	    this.state = {
            value: get(this.props.value, ''),
            show: false,
		}
		this.closeOptionBar = this.closeOptionBar.bind(this);
		this.oldValue = this.state.value;
	}
	
	initial(){
        var {onChange, onFocus, option, onApply, onBlur, ...rent} = this.props;
        this.onChange = get(onChange, ()=>{});
        this.onFocus = get(onFocus, ()=>{});
	    this.rent = rent;
	}
	
	setValue(value){
		if(value == null) value = '';
		this.setState({value: value});
	}
	
	getValue(){
		var value = this.state.value;
		return value;
	}
	
	openOptionBar(event){
        var newState = true;
        this.setState({show: newState});
        if(newState){
            window.addEventListener('click', this.closeOptionBar);
        }
        event.stopPropagation();
    }

    closeOptionBar(event){
        if(event.target.closest(`#option${this.id}`) == null){
            this.setState({show: false});
            window.removeEventListener('click', this.closeOptionBar);
            event.stopPropagation();
            event.preventDefault();
        }
    }

    componentWillUnmount(){
        window.removeEventListener('click', this.closeOptionBar);
    }
	

	getVoucher(){
		if(this.state.value == this.oldValue) return;
		this.oldValue = this.state.value;

		if(this.state.value == ''){
			if(this.props.onApply) this.props.onApply({[VOUCHER_VALUE]: 0});
			return;
		}

		App.loading(true);
		axios({
            method: 'POST',
            url: '/user/pages/getVoucher',
            dataType: 'json',
            data: {
                voucher: this.state.value
            }
        })
            .then(response => {
                App.loading(false);
                response = response.data;
                if (response['result']) {
                    if(this.props.onApply) this.props.onApply(response['data']);
                } else {
					if(this.props.onApply) this.props.onApply({[VOUCHER_VALUE]: 0});
                    error_handle(response);
                }

            })
            .catch(error => {
                App.loading(false);
				console.log(error);
				if(this.props.onApply) this.props.onApply({[VOUCHER_VALUE]: 0});
                error_handle(error);
            });
	}
	
	
	
	render(){
		this.initial();	
		return(
				<div className='input_option' style={{position:'relative'}}>
					<input
						
						value={this.state.value} 
						onChange={(event)=>{this.setState({value: event.target.value})}}
						onFocus={(event)=>{this.openOptionBar(event)} }
						onClick={(e)=>{e.stopPropagation()}}
						onBlur = {()=>{this.getVoucher()}}
						ref = {input => this.input = input}
						{...this.rent}
					/>

                    <div id={`option${this.id}`} className='box_shadow' style={{display:this.state.show?'block':'none', position:'absolute', left:0, padding:5, background:'white', zIndex:1}}>
                        {Object.keys(this.props.option).map(item =>{
                            return <div key={item} className='box_flex button box_line' style={{padding:5}} onClick={(e)=>{
                                this.setState({value: item, show:false}, ()=>{this.getVoucher()})
                            }}><i className='fa fa-tag'></i>&nbsp; <b>{item}</b>&nbsp;{`(Giảm giá ${this.props.option[item]} VNĐ)`}</div>
                        })}
                    </div>
					<style>{`
						.input_option::after{
							content: "\\f0d7";
							font: normal normal normal 14px/1 FontAwesome;
							position: absolute;
							right: 5px;
							top: 5px;
						}
					`}</style>
            	</div>
		)
	}
}

export default InputVoucherOption;
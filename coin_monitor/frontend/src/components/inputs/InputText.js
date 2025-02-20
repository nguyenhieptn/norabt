import React, { Component } from 'react'
import { get, isset, makeId } from '../../helpers/Default';
import InputParent from './InputParent';
import axios from 'axios'

/**
 * props
 * - Direct: true/false
 * - DecoratorIn : (value, this) => {}
 * - DecoratorOut : (value, this) => {}
 * - OnChange : (value, this) => {}
 * - Suggest : an URL
 * - DefaultValue : default value
 * - Options: an array [{key:..., value:...}]
 * - OnChangeBlur: (value, this)=>{} Onchange and value is modified
 */

class InputText extends InputParent {
	
	constructor(props) {
	    super(props);
	    
	    this.state = {
	    	value: get(this.props.DefaultValue, ''),
	    	suggest: [],
	    	loading: false,
	    }

		this.id = makeId();
		this.oldValue = get(this.props.DefaultValue, '');
		
	}
	

	onBlurHandle(event){
		if(this.props.onBlur) this.props.onBlur(event);
		let val = event.target.value;
		if(val != this.oldValue){
			if(this.props.OnChangeBlur){
				this.oldValue = val;
				this.props.OnChangeBlur(val, this)
			}
		}
	}
	
	loadSuggest(){
		if(isset(this.props.Suggest)){
			if(this.suggestTimeout) clearTimeout(this.suggestTimeout);
			if(isset(this.revert[this.state.value])){
				this.setState({loading: false});
				return;
			}
			this.setState({loading: true});
			this.suggestTimeout = setTimeout(()=>{this.querySuggest()}, 1000);
		}
	}
	
	querySuggest(){
		axios.request ({
		    url: this.suggest,
		    method: 'post',
		    data:{
			    	search: this.state.value
		    	}
			})
			
	      .then(response => {
	    	  response = response['data'];
	    	  this.setState({
	    		  loading: false,
	    		  suggest: response['data'],
	    	  });
	      })
	      .catch((error)=>{
	    	  this.setState({
	    		  loading: false,
	    	  });
	      })
	}
	
	onFocusHandle(event){
		if(this.props.onFocus) this.props.onFocus(event);
		var value = event.target.value;
		if(value==''){
			this.querySuggest();
		}
	}

	onChangeHandle(event){
		var val = event.target.value;
		
		if(!this.props.Direct){
			this.setState({'label': event.target.value}, ()=>{
				if(this.props.OnChange) this.props.OnChange(val, this);
				if(this.props.onChange) this.props.onChange(event);
				this.loadSuggest()
			})
		}else{
			if(this.props.onChange) this.props.onChange(event);
			if(this.props.OnChange){
				if(this.props.DecoratorOut) val = this.props.DecoratorOut(val, this);
				this.props.OnChange(val, this);
			}
		}
		
	}
	
	render(){
		
		this.initial();

		var datalist = [];
		this.revert = {};
		
		for(let option of this.state.suggest){
			  datalist.push(<option key={option['value']} value={option['value']}>{option['label']}</option>);
			  this.revert[option['label']] = option['value'];
		}
		
		if(this.props.Options){
			for(let option of this.props.Options){
				if(!isset(this.revert[option['label']])){
					datalist.push(<option key={option['value']} value={option['value']}>{option['label']}</option>);
					this.revert[option['label']] = option['value'];
				}
			}
		}
		
		
		var loading = '';
		if(this.state.loading){
			loading = <i style={{margin: 'auto', padding: 5}} className="fa fa-circle-o-notch fa-spin"></i>
		}

		
		var val = this.showValue()
		
		return(
				<div style={{display:'flex'}}>
					<input
						value={val} 
						onChange={(event)=>{this.onChangeHandle(event)}}
						onFocus={(event)=>this.onFocusHandle(event)} 
						onBlur={event => this.onBlurHandle(event)}
						ref = {input => this.input = input}
						list = {"editlist"+this.id}
						{...this.rent}
					/>
					{loading}
					<datalist id = {"editlist"+this.id}>
	            		{datalist}
	            	</datalist>
            	</div>
		)
	}
}

export default InputText;
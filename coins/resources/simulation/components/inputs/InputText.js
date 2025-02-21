import React, { Component } from 'react'
import InputParent from './InputParent';

/**
 * props
 * - Direct: true/false
 * - DecoratorIn : (value, this) => {}
 * - DecoratorOut : (value, this) => {}
 * - OnChange : (value, this) => {}
 * - Suggest : an URL
 * - DefaultValue : default value
 * - Options: an object
 * - OnChangeBlur: (value, this)=>{} Onchange and value is modified
 */

class InputText extends InputParent {
	
	constructor(props) {
	    super(props);
	    this.state.suggest = {};
		this.state.loading = false;
		
	}
	
	initial(){
		this.makeProps([
			'onFocus', 
			'onBlur'
		]);
		this.makeDecorator();
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
			this.setState({'value': event.target.value}, ()=>{
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
		
		for(let i in this.state.suggest){
			  datalist.push(<option key={i} value={this.state.suggest[i]}>{this.state.suggest[i]}</option>);
			  this.revert[this.state.suggest[i]] = i;
		}
		
		if(this.props.Options){
			for(let i in this.props.Options){
				if(!this.state.suggest[i]){
					datalist.push(<option key={i} value={this.props.Options[i]}>{this.props.Options[i]}</option>);
					this.revert[this.props.Options[i]] = i;
				}
			}
		}
		
		
		var loading = '';
		if(this.state.loading){
			loading = <i style={{margin: 'auto', padding: 5}} className="fa fa-circle-o-notch fa-spin"></i>
		}

		if(this.props.Direct){
			var val = this.props.value;
			if(this.DecoratorIn) val = this.DecoratorIn(val, this);
		}else{
			// debugger
			var val = this.state.value;
			
		}
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
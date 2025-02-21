import React, { Component } from 'react'


class InputBlade extends Component {
	
	constructor(props) {
	    super(props);
	    
	    this.initial();
	    
	    this.state = {
	    	value: '',
            suggestBlock: '',
            suggestFilter: '',
            suggestX: '0',
            suggestY: '100%',
            show: false,
	    }

        this.suggests = {
            '@': ['foreach', 'endforeach', 'if' , 'else', 'endif', 'elseif'],
            '$': []
        }
	    
	}

    setSuggest(suggest){
        this.suggests = {...this.suggests, ...suggest}
    }

    showSuggest(show){
        var x = 0;
        var y = 0;
        if(show){
            var value = this.state.value;
            var index = this.input.selectionStart;
            var valueRows = value.substring(0, index).split("\n");
            var numberOfRow = valueRows.length;
            
            y = numberOfRow * 16;
            y = this.input.clientHeight - y + 30 + this.input.scrollTop;
            
            this.rule.textContent = valueRows[numberOfRow-1];
            x = this.rule.offsetWidth%this.input.clientWidth;
        
        }
        
        this.setState({show, suggestX: x, suggestY: y})
    }
	
	initial(){
		var {id, value, decoratorOut, decoratorIn, onChange, ...rent} = this.props;
		this.id = get(id, '');
		this.onChange = get(onChange, ()=>{})
	    this.decoratorOut = get(decoratorOut, null);
	    this.decoratorIn = get(decoratorIn, null);
	    this.rent = rent;
	}
	
	setValue(value){
		
		if(isset(this.decoratorIn)) value = this.decoratorIn(value);
		if(value == null) value = '';
		this.setState({value: value});
	}
	
	getValue(){
		var value = this.state.value;
		if(isset(this.decoratorOut)) value = this.decoratorOut(value);
		return value;
	}
	
	revertValue(value){
		if(isset(this.decoratorOut)) value = this.decoratorOut(value);
		return value;
	}
	
	getInput(){
		return this.input;
	}

    validate(){
        return true;
    }

    insertText(str, jump=0){
        var value = this.state.value;
        var index = this.input.selectionStart;
        value = value.substring(0, index) + str + value.substring(index, value.length);
        
        this.setState({value}, ()=>{
            this.input.selectionStart = index + str.length + jump;
            this.input.selectionEnd = index + str.length + jump;
        })
    }

    delText(del, callback){
        var value = this.state.value;
        var index = this.input.selectionStart;
        value = value.substring(0, index-del) + value.substring(index, value.length);
        
        this.setState({value}, ()=>{
            this.input.selectionStart = index-del;
            this.input.selectionEnd = index-del;
            callback();
        })
    }
	
	render(){
		this.initial();

        var suggests = get(this.suggests[this.state.suggestBlock], []);
        suggests = suggests.filter(item => item.includes(this.state.suggestFilter));

       
       
		return(
				<div style={{position:'relative', width:'100%'}}>
                    <textarea
                        value={this.state.value} 
                        onChange={(event)=>{console.log('test') ;this.setState({'value': event.target.value}, ()=>{this.onChange()})}} 
                        ref = {input => this.input = input}
                        style={{width:'100%', minHeight:200, lineHeight:16, ...get(this.props.style, {})}}
                        {...this.rent}
                    >
                    </textarea>
                   <div style={{minWidth:200, display:(this.state.show && suggests.length > 0)?'block':'none', position:'absolute', bottom:this.state.suggestY, left:this.state.suggestX, background:'azure', padding:5, borderRadius:5}} className='box_shadow'>
                        {suggests.map(item => {
                            return <div key={item} className='button suggest_item' style={{padding:5}} onClick={()=>{
                                this.delText(this.state.suggestFilter.length, ()=>{this.insertText(item + " ")})
                                this.showSuggest(false)
                            }}>{item}</div>
                        })}
                   </div>

                   <style>{`
                        .suggest_item:hover{
                            background: aliceblue;
                            font-weight: bold;
                        }
                   `}</style>
                   <span style={{visibility:'hidden'}} ref={c => this.rule = c}></span>
                </div>
		)
	}


    updateSuggestFilter(){
        var value = this.state.value;
        var pointer = this.input.selectionStart;
        var allowKey = Object.keys(this.suggests);
        var filter = [];
    
        for(let i = pointer-1; i >= 0 ; i--){
            if(allowKey.includes(value[i])){
                var filterString = filter.reverse().join('');
                this.setState({
                    suggestFilter: filterString,
                    suggestBlock: value[i],
                })
                this.showSuggest(true);
                return;
            }
            if(!/\w/.test(value[i])){
                this.showSuggest(false)
                return;
            }
            filter.push(value[i]);

        }
        this.showSuggest(false)
    }

	componentDidMount(){
		if(isset(this.props.value)){
			this.setValue(this.props.value);
		}

        $(this.input).click(()=>{
            if(this.state.show){
                this.showSuggest(false)
            }
        })

        $(this.input).keyup((e)=>{
            
            var allowKey = Object.keys(this.suggests);

            if(allowKey.includes(e.key)){
                this.setState({
                    show: true,
                    suggestBlock: e.key,
                    suggestFilter: ''
                })
            }else{

                if(this.suggestTimeout){
                    clearTimeout(this.suggestTimeout);
                }
                this.suggestTimeout = setTimeout(()=>{
                    this.updateSuggestFilter();
                },100)
            }



            if(!/\w/.test(e.key)){
                if(isset(this.suggests[this.state.suggestBlock]) && !this.suggests[this.state.suggestBlock].includes(this.state.suggestFilter)){
                    this.suggests[this.state.suggestBlock].push(this.state.suggestFilter);
                }
                this.showSuggest(false)
                
            }

            if(e.key == '{'){
                setTimeout(()=>{
                    this.insertText('}', -1)
                }, 100) 
            }

            else if(e.key == '<'){
                setTimeout(()=>{
                    this.insertText('>', -1)
                }, 100) 
            }

            else if(e.key == '('){
                setTimeout(()=>{
                    this.insertText(')', -1)
                }, 100) 
            }

            else if(e.key == '['){
                setTimeout(()=>{
                    this.insertText(']', -1)
                }, 100) 
            }

            else if(e.key == '"'){
                setTimeout(()=>{
                    this.insertText('"', -1)
                }, 100) 
            }

            else if(e.key == "'"){
                setTimeout(()=>{
                    this.insertText("'", -1)
                }, 100) 
            }
            
        });
	}
}

export default InputBlade;
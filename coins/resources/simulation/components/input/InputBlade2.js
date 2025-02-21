import React, { Component } from 'react'


class InputBlade extends Component {
	
	constructor(props) {
	    super(props);
	    
	    this.initial();
	    
	    this.state = {
	    	value: '',
            suggestBlock: '',
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
        this.setState({show})
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
		this.input.innerHTML = value;
	}
	
	getValue(){
		var value = this.input.innerHTML;
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
	
	render(){
		this.initial();

        var suggests = get(this.suggests[this.state.suggestBlock], []);

		return(
				<div style={{position:'relative', width:'100%'}}>
                    
                    <div className='input'
                        ref = {input => this.input = input}
                        contentEditable={true}
                        {...this.rent}
                    >
                    </div>

                   <style>{`
                        .suggest_item:hover{
                            background: aliceblue;
                            font-weight: bold;
                        }
                   `}</style>
                </div>
		)
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

        $(this.input).keypress((e)=>{
            console.log(e.key);
            var allowKey = Object.keys(this.suggests);

            if(allowKey.includes(e.key)){
                this.setState({
                    show: true,
                    suggestBlock: e.key
                })
            }

            if(e.key == ' '){
                this.showSuggest(false)
            }

            if(e.key == '{'){
                setTimeout(()=>{
                    this.insertText('}', -1)
                }, 100) 
            }

            if(e.key == '<'){
                setTimeout(()=>{
                    this.insertText('>', -1)
                }, 100) 
            }

            if(e.key == '('){
                setTimeout(()=>{
                    this.insertText(')', -1)
                }, 100) 
            }

            if(e.key == '['){
                setTimeout(()=>{
                    this.insertText(']', -1)
                }, 100) 
            }
            
        });
	}
}

export default InputBlade;
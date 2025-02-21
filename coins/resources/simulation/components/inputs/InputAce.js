import React, { Component } from 'react'
import AceEditor from "react-ace";

import "ace-builds/src-noconflict/mode-json";
import "ace-builds/src-noconflict/theme-monokai";

class InputAce extends Component {

    constructor(props) {
        super(props);

        this.state = {
            value: get(this.props.value, ''),
            expand: false,
        }

    }

    initial() {
        var { id, value, decoratorOut, decoratorIn, onChange, ...rent } = this.props;
        this.id = get(id, '');
        this.onChange = get(onChange, () => { });
        this.decoratorOut = get(decoratorOut, null);
        this.decoratorIn = get(decoratorIn, null);
        this.rent = rent;
    }

    setValue(value) {
        if (this.decoratorIn) value = this.decoratorIn(value);
        if (value == null) value = '';
        this.setState({ value: value });
    }

    getValue() {
        var value = this.state.value;
        if (this.decoratorOut) value = this.decoratorOut(value);
        return value;
    }

    getInput() {
        return this.input;
    }


    render() {
        this.initial();


        return (
            <div style={this.state.expand 
                    ? { position: "fixed", left: 0, right: 0, top: 0, height: "90%", zIndex: 1000}
                    : { height: 500, resize:'vertical', overflow: 'auto', position:'relative'}
                }>
                <div style={{position: "absolute", zIndex: 100, right: 5, top: 5}} className='button' onClick={()=>{this.setState({expand : !this.state.expand})}}>
                    <i className={this.state.expand ? "fa fa-compress" : "fa fa-expand"} style={{fontSize:24, color:'darkgray'}}></i>
                </div>
                <AceEditor
                    mode="json"
                    theme="monokai"
                    name="blah2"
                    //onLoad={this.onLoad}
                    onChange={(val) => { this.setState({ 'value': val }, () => { this.onChange() }) }}
                    fontSize={14}
                    showPrintMargin={true}
                    showGutter={true}
                    highlightActiveLine={true}
                    value={this.state.value}
                    width="100%"
                    maxLines={Infinity}
                    setOptions={{
                        enableSnippets: false,
                        showLineNumbers: true,
                        tabSize: 2,
                    }}
                    ref={input => this.input = input}
                />
            </div>

        )
    }

    componentDidMount(){
        this.input.editor.resize();
        this.input.editor.renderer.updateFull();
        this.input.editor.renderer.setPadding(8);
    }
}

export default InputAce;
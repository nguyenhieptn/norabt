import React, { Component } from 'react'
import Input from './Input';

class InputObject extends Component {

    constructor(props) {
        super(props);

        this.state = {
            value: get(this.props.value, { "": "" })
        }

        this.initial();
    }


    initial() {
        var { decoratorOut, decoratorIn, ...rent } = this.props;
        this.decoratorOut = get(decoratorOut, null);
        this.decoratorIn = get(decoratorIn, null);
        this.rent = rent;
    }


    setValue(value) {
        if (typeof value == 'string') {
            try { value = JSON.parse(value); } catch (error) { console.log(error); value = null }
        }

        if (!value) value = { "": "" }
        if (this.decoratorIn) value = this.decoratorIn(value);
        this.setState({ value })
    }

    getValue() {
        var value = this.state.value;

        var returnVals = {};
        for (let key in value) {
            if (key != "" && key != null) {
                returnVals[key] = value[key];
            }
        }
        if (this.decoratorOut) returnVals = this.decoratorOut(returnVals);
        return returnVals;
    }

    revertValue(value) {
        return '';
    }

    getInput() {
        return this.input;
    }

    validate() {
        return true;
    }



    render() {
        var value = this.state.value;
        this.initial();
        return (
            <div style={{ width: "100%" }}>
                <div className='box_flex' style={{ marginBottom: 15 }}>
                    <div className='editor_item_text'>{get(this.props.text, '')}</div>
                    <div className='button' style={{ margin: 'auto 0px auto auto' }} onClick={() => {
                        value[''] = ''
                        this.setState({ value });

                    }}>
                        <i className="fa fa-plus-square"></i>&nbsp;{lang('Add')}
                    </div>
                </div>
                <div>
                    {Object.keys(value).map(item => {
                        return <div className='box_flex' key={item}>



                            <div style={{ width: '50%' }}>
                                <Input style={{ width: '100%' }} className='input' placeholder='key'
                                    struct={{
                                        [INPUT_TYPE]: 'text',
                                        [INPUT_DEFAULT]: item,
                                        [INPUT_ONCHANGE_BLUR]: (e, obj) => {

                                            var val = obj.input.getValue();
                                            delete (value[item]);
                                            value[val] = value[item];
                                            this.setState({ value })

                                        }
                                    }}>
                                </Input>
                            </div>

                            <div style={{ width: '50%' }}>
                                <Input style={{ width: '100%' }} className='input' placeholder='value'
                                    struct={{
                                        [INPUT_TYPE]: 'text',
                                        [INPUT_DEFAULT]: value[item],
                                        [INPUT_ONCHANGE_BLUR]: (e, obj) => {

                                            var val = obj.input.getValue();
                                            value[item] = val.replace(/\"/g, "'");
                                            this.setState({ value })

                                        }
                                    }}>
                                </Input>

                            </div>

                            <div style={{ width: '30px' }}><i className="button fa fa-trash" onClick={() => {
                                delete (value[item]);
                                this.setState({ value })
                            }}></i></div>

                        </div>
                    })}
                </div>
            </div>
        )
    }
}

export default InputObject;
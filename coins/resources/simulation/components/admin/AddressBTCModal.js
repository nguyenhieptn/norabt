import React, { Component } from 'react';



class AddressBTCModal extends Component {
    constructor(props) {
        super(props);
        this.id = makeId();
        this.state = {
            Value: [],
            title : ''
        }
    }



    modal(cmd = 'show') {
        if (cmd == 'hide') {
            $("#add_row_modal" + this.id).modal('hide');

        } else {
            $("#add_row_modal" + this.id).modal();
        }
    }

    setValue(data , title) {
        var data = data.split(" ");
        this.setState({
            Value: data,
            title : title
        });

    }





    componentDidMount() {

    }

    render() {

        return (
            <div className="modal fade" id={"add_row_modal" + this.id} onClick={() => { addClass($('body')[0], 'modal-open') }}>
                <div className="modal-dialog modal-lg modal-dialog-centered" style={{ maxWidth: '75%' }}>
                    <div className="modal-content">

                        <div className="modal-header">
                            <h4 className="modal-title">{this.state.title}</h4>
                            <button type="button" className="close" data-dismiss="modal">&times;</button>
                        </div>

                        <div className="modal-body" >

                            <div className='row'>
                                <div className='col-6'>
                                    <div style={{display : 'flex'}}>
                                        <span style={{flex : 1}} >STT</span>
                                        <b style={{flex : 3}}> Address  </b>
                                    </div>
                                    {

                                        this.state.Value.map((item, index) => {
                                            if (index % 2 == 0) {
                                                return (
                                                    <div style={{display : 'flex'}}>
                                                        <span style={{flex : 1}} >{index}</span>
                                                        <b style={{flex : 3}}> {item}  </b>
                                                    </div>
                                                )
                                            }
                                        })
                                    }
                                </div>
                                <div className='col-6'>
                                    <div style={{display : 'flex'}}>
                                        <span style={{flex : 1}} >STT</span>
                                        <b style={{flex : 3}}> Address  </b>
                                    </div>
                                    {

                                        this.state.Value.map((item, index) => {
                                            if (index % 2 !== 0) {
                                                return (
                                                    <div style={{display : 'flex'}}>
                                                        <span style={{flex : 1}} >{index}</span>
                                                        <b style={{flex : 3}}> {item}  </b>
                                                    </div>
                                                )
                                            }
                                        })
                                    }

                                </div>
                            </div>





                        </div>

                        <div className="modal-footer">
                            <button type="button" className="btn btn-danger" data-dismiss="modal">{lang('Close')}</button>
                        </div>
                    </div>
                </div>
            </div>
        );
    }
}

export default AddressBTCModal;
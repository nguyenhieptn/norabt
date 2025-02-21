import React, { Component } from 'react'
import FileManager from '../input/FileManager';
import ContractModal from '../admin/ContractModal';


class Contract extends Component {
    constructor(props) {
        super(props);
        this.state = {
            ...this.props.data ? this.props.data : {},
            isShow: false,
        }

    }

    onSave() {
        App.loading(true)
        axios.request({
            url: App.saleApi(`/api/contract_template`),
            method: 'post',
            data: {
                "fileId": this.state.fileId,
                "name": this.state.name,
                "productType": this.state.productType == 0 ? Object.keys(App.project.projectTypes)[0] : this.state.productType,
                "projectCode": App.project.code
            }
        })

            .then(response => {
                App.loading(false)
                showLog('Thêm thành công', 'success');

                if(this.props.load) this.props.load();

            })


            .catch((error) => {
                App.loading(false)
                console.log(error);
                error_handle(error);
            })

    }

    onEdit() {

        makeQuestion(lang('Bạn có muốn sửa?'), lang('Có'), lang('Không'), 'warning').then(res => {
            if (res) {
                App.loading(true)
                axios.request({
                    url: App.saleApi(`/api/contract_template`),
                    method: 'put',
                    data: {
                        "fileId": this.state.fileId,
                        "id": this.state.id,
                        "name": this.state.name,
                        "productType": this.state.productType,
                        "projectCode": App.project.code
                    }
                })

                    .then(response => {
                        App.loading(false)
                        showLog('Sửa thành công', 'success');

                        if(this.props.load) this.props.load();

                    })


                    .catch((error) => {
                        App.loading(false)
                        console.log(error);
                        error_handle(error);
                    })
            }


        })

    }

    onDel() {
        makeQuestion(lang('Bạn có muốn xóa?'), lang('Có'), lang('Không'), 'warning').then(res => {
            if (res) {
                axios.request({
                    url: App.saleApi(`/api/contract_template/${this.state.id}`),
                    method: 'delete',
                })

                    .then(response => {

                        App.loading(false)
                        showLog('Xóa thành công', 'success');

                        if(this.props.load) this.props.load();


                    })

                    .catch((error) => {
                        App.loading(false)
                        console.log(error);
                        error_handle(error);
                    })
            }


        })


    }
    componentDidMount() {
        if (!App.project[PROJECT_CODE]) return;
        if (this.props.data.fileId) {
            axios.request({
                url: App.baseApi(`/api/file/info1/${this.props.data.fileId}`),
                method: 'get',
            })
                .then(response => {

                    response = response['data'];
                    this.setState({ preview: response });

                })

        }



    }
    loadfile() {
        axios.request({
            url: App.baseApi(`/api/file/download?id=${this.state.preview.id}`),
            method: 'get',
            responseType: 'blob'

        })
            .then(response => {
                var blob = response['data'];
                var url = window.URL.createObjectURL(blob);
                var a = document.createElement('a');
                a.href = url;
                a.download = this.state.preview['name'];

                a.click();
            })
    }
    render() {
        return (
            <div className="Contract-item box_shadow" style={{ marginBottom: 15, padding: 5 }}>


                <div className="row" style={{ padding: 5 }}>

                    <div className="col-sm-12 col-md-4 col-lg-4" style={{ padding: 5, overflow: 'hidden' }}>


                        {(() => {
                            if (this.state.preview == null) return '';

                            return <>

                                <div style={{ padding: 5 }}>

                                    <table>
                                        <tbody>
                                            <tr><th style={{ whiteSpace: 'nowrap' }}>{lang('Tên file')}</th><td>:</td><td style={{ wordBreak: 'break-all' }}>

                                                <div style={{ fontWeight: 'bold', color: '#17a2b8', cursor: 'pointer' }} className='box_line' onClick={() => {
                                                    this.loadfile()
                                                }}>
                                                    {this.state.preview['name']}
                                                </div>

                                            </td></tr>
                                            <tr><th style={{ whiteSpace: 'nowrap' }}>{lang('Kích thước')}</th><td>:</td><td style={{ wordBreak: 'break-all' }}>{this.FileManager.showSize(this.state.preview['size'])}</td></tr>
                                            <tr><th style={{ whiteSpace: 'nowrap' }}>{lang('Người tạo')}</th><td>:</td><td style={{ wordBreak: 'break-all' }}>{this.state.preview['createUsername']}</td></tr>
                                        </tbody>
                                    </table>

                                </div>

                            </>


                        })()}


                    </div>


                    <div className="col-sm-12 col-md-8 col-lg-8" style={{ padding: 5 }}>

                        <div className='box_flex' style={{ padding: 5 }}>
                            <b className='col-md-4' style={{ padding: 5 }}>{lang('name')}:</b>
                            <input className='input' style={{ width: '100%' }} type="text" value={this.state.name} onChange={(e) => this.setState({ name: e.target.value })} /><br />
                        </div>

                        <div className='box_flex' style={{ padding: 5 }}>
                            <b className='col-md-4' style={{ padding: 5 }}>{lang('productType')}:</b>
                            <select className='input' style={{ width: '100%' }} onChange={(e) => this.setState({ productType: e.target.value })}>
                                {

                                    App.project.projectTypes && Object.keys(App.project.projectTypes).map((key) => {
                                        if (this.state.productType == App.project.projectTypes[key]) {
                                            this.setState({
                                                productType: App.project.projectTypes[key]
                                            });
                                            return <option selected key={key} value={key}>{App.project.projectTypes[key]}</option>
                                        } else {
                                            return <option key={key} value={key}>{App.project.projectTypes[key]}</option>
                                        }
                                    }
                                    )

                                }
                            </select>
                        </div>

                    </div>



                </div>

                <div className="">
                    {(() => {
                        if (!this.props.data.fileId) {
                            return <div style={{ padding: 5 }}>
                                <button className="button btn btn-info btn-sm" onClick={() => { this.uploadFile(); }}>
                                    <i className="fa fa-folder" ></i>&nbsp;{lang('Tải File lên')}
                                </button>

                                <button className="button btn btn-info btn-sm" onClick={() => this.onSave()}>
                                    <i className="fa fa-plus-square" data-toggle="tooltip" data-placement="bottom" title="Lưu" ></i>&nbsp;{lang('Lưu')}
                                </button>

                            </div>
                        }

                        return <div style={{ padding: 5 }}>

                            <button className="button btn btn-info btn-sm" onClick={() => { this.uploadFile(); }}>
                                <i className="fa fa-folder" ></i>&nbsp;{lang('Tải File lên')}
                            </button>

                            <button className="button btn btn-info btn-sm" onClick={() => this.EditBladeModal.modal()}>
                                <i className="fa fa-eye" data-toggle="tooltip" data-placement="bottom" title="Show"></i>&nbsp;{lang('Xem tham số')}
                            </button>

                            <button className="button btn btn-info btn-sm" onClick={() => this.onEdit()}>
                                <i className="fa fa-save" data-toggle="tooltip" data-placement="bottom" title="Lưu"></i>&nbsp;{lang('Lưu')}
                            </button>


                            <button className="button btn btn-danger btn-sm" onClick={() => this.onDel()}>
                                <i className="fa fa-trash" style={{ color: 'white' }} data-toggle="tooltip" data-placement="bottom" title="Xóa" ></i>&nbsp;{lang('Xóa')}
                            </button>


                        </div>
                    })()}

                </div>

                <FileManager ref={c => this.FileManager = c}></FileManager>
                <ContractModal key={this.state.productType} ref={c => this.EditBladeModal = c} productType={this.state.productType}></ContractModal>
            </div >



        )
    }


    uploadFile() {
        this.FileManager.modal();
        this.FileManager.setOnSelect((res) => {

            this.setState({ fileId: Object.keys(res)[0] });
            this.FileManager.modal('hide');



            axios.request({
                url: App.baseApi(`/api/file/info1/${Object.keys(res)[0]}`),
                method: 'get',
            })

                .then(response => {
                    App.loading(false)
                    response = response['data'];
                    this.setState({ preview: response });
                })

                .catch((error) => {
                    App.loading(false)
                    console.log(error);
                    error_handle(error);
                })


        })
    }
}

export default Contract;
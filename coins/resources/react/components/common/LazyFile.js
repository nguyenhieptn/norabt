import React, { Component } from 'react'

class LazyFile extends Component {

    constructor(props) {
        super(props);
        this.state = {
            id: this.props.id,
            info: {},
        }

    }


    previewFile() {
        if(this.state.id == '') return;
        return axios.request({
            url: App.baseApi(`/api/file/info1/${this.state.id}`),
            method: 'get',
        })
            .then(response => {
                response = response['data'];
                this.setState({info: response});
            })

            .catch((error)=> {
                console.log(error);
                this.setState({ info: {} })
            })
    }

    downloadFile(filename) {
        if(this.state.id == '') return;
        return axios.request({
            url: App.baseApi(`/api/file/download1?code=${this.state.id}`),
            method: 'get',
            responseType: 'blob'
        })
            .then(response => {
                var blob = response['data'];
                const blobURL = window.URL.createObjectURL(blob);
                var url = window.URL.createObjectURL(blob);
                var a = document.createElement('a');
                a.href = url;
                a.download = filename;
                a.click();
            })

            .catch((error)=>{
                console.log(error);
                this.setState({ link: '' })
            })
    }

    componentDidMount() {
        this.previewFile();
    }

    render() {
        var item = this.state.info;
        if(!isset(item['id'])) return '';
        return <div key={item} style={{padding:5}} className='box_flex box_line button' onClick={e => this.downloadFile(item['name'])}>
            <i className={item['mime'].includes('image') ? "fa fa-file-image-o" : "fa fa-file-o"} style={{ color: 'gray', fontSize: 16 }}></i> &nbsp; {item['name']}
        </div>
    }
}
export default LazyFile

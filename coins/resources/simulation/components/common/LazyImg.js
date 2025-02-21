import React, { Component } from 'react'

class LazyImg extends Component {

    constructor(props) {
        super(props);
        this.state = {
            id: this.props.id,
            link: ''
        }

    }


    previewFile() {
        if(this.state.id == '') return;
        return axios.request({
            url: App.baseApi(`/api/file/download1?code=${this.state.id}`),
            method: 'get',
            responseType: 'blob'
        })
            .then(response => {
                var blob = response['data'];
                const blobURL = window.URL.createObjectURL(blob);
                this.setState({ link: blobURL })
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
        if (this.state.link == '') return '';
        var {id, style, ...rent} = this.props;
        if(!style) style = {width:'100%'};
        return <img style={style} src={this.state.link} {...rent}></img>
    }
}
export default LazyImg

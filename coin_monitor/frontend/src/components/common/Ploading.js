import React, { Component } from 'react'
import { render } from 'react-dom'
import Style from './Style';

class Ploading extends Component {
	
	constructor(props) {
	    super(props);
	    this.state={
	    		flag: this.props.flag, 
	    		text: this.props.text,
				update: '',
				process: null,
		};
	    
	    
	}
	
	loading(flag, text, update='', process=null){
		if(flag){
			this.loader12Timeline.play()
		}else{
			this.loader12Timeline.pause()
		}
		this.setState({
			flag: flag, 
			text: text,
			update: update,
			process: process,
			});
	}
	update(update, process=null){
		if(!update) update = '';
		if(!process) process = null;
		this.setState({update, process});
	}

	componentDidMount(){
		this.loader12Timeline = new global.TimelineMax({repeat: -1});
		
		this.loader12Timeline.to('.loader12__path-top', 0.75, {
			attr: {
				cx: 50,
				cy: 50
			}
		}, "l12_1")
			.to('.loader12__path-left', 0.75, {
				attr: {
					cx: 27,
					cy: 5
				}
			}, "l12_1")
			.to('.loader12__path-right', 0.75, {
				attr: {
					cx: 5,
					cy: 50
				}
			}, "l12_1");

		this.loader12Timeline.pause()
	}
	
	  render () {
		  
		  return (
		  
		   <>
			<Style id="loadingcss">{`
				.loading_text {
					color: white;
					font-weight:bold;
				}
				.loading_container{
					margin: auto;
					text-align: center;
				}
				
				.loading_cover.none {
					display: none;
				}
				
				.loading_cover {
					position: fixed;
				    background: rgba(0, 0, 0, 0.2); 
					display: flex;
				    top: 0;
				    bottom: 0;
				    left: 0;
				    right: 0;
					z-index: 10000;
				}
				
			`}</Style>
			
			<div className={"loading_cover" + (this.state.flag?"":" none ")} style={this.props.style}>
			    <div className = "loading_container" style={{width:'50%', minWidth:300}}>
			        <div className="lds-spinner" >
						<svg className="loader12" height="57" stroke="#fff" viewBox="0 0 57 57" width="57"
							xmlns="http://www.w3.org/2000/svg">
							<g fillRule="evenodd" fill="none">
								<g strokeWidth="2" transform="translate(1 1)">
									<circle className="loader12__path-left" cx="5" cy="50" r="5"></circle>
									<circle className="loader12__path-top" cx="27" cy="5" r="5"></circle>
									<circle className="loader12__path-right" cx="50" cy="50" r="5"></circle>
								</g>
							</g>
						</svg>
			        </div>
			        <div className="loading_text">{this.state.text}</div>
			        <div className="loading_text">{this.state.update}</div>
						  {this.state.process != null
							  ? <div className="progress" style={{backgroundColor:'white'}}>
								  	<div className="progress-bar progress-bar-striped active" role="progressbar" style={{width:`${this.state.process}%`}}>
									  {this.state.process}%
									</div>
							  </div>
							  : ''
						  }
					
			    </div>
		    </div>
	    </>
		  )
		  
	  }
}




export default Ploading;
	  
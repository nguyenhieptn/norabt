import React, { Component } from 'react'
import Style from '../common/Style'
import Logout from './Logout'
import Notice from '../notice/Notice';
import { Link } from 'react-router-dom';


class Namecard extends Component {
	constructor(props) {
		super(props);

		this.state = {
			expand: false,
			user: {},
		}
		this.id = makeId();



	}

	render() {
		return (
			<>
				<Style id="namecardcss">{`
					.profile {
						padding: 15px 0px;
						overflow: auto;
						width: 100%;
					    -webkit-box-shadow: 0 2px 5px 0 rgba(0, 0, 0, 0.15);
					    -moz-box-shadow: 0 2px 5px 0 rgba(0, 0, 0, 0.15);
					    box-shadow: 0 2px 5px 0 rgba(0, 0, 0, 0.15);
						background: #363a41;
					}
	
					.profile-image {
						width: 45px;
					    height: 45px;
					    float: left;
					    margin: 0px 10px;
						border-radius: 50%;    
						border: solid thin darkgray;
					}
	
					.profile-name {
						display: block;
					    color: white;
					    vertical-align: middle;
					    font-size: 16px;
					    font-weight: bold;
					    text-align: left;
					    margin-top: 4px;
					}
					.profile-role{
						display: block;
					    text-align: left;
					    font-size: 12px;
						margin-top: 4px;
					    color: white;
					}
					.profile-menu{
						background: #363a41;
						border-bottom: 1px solid #d6d5d5;
						margin-top: 16px;
						padding-bottom: 16px;
						display: none;
					}
					.profile-menu-item {
						display: block;
						position: relative;
						cursor: pointer;
						white-space: nowrap;
						border-left: solid transparent;
					}
					.profile-menu-item div {
						white-space: nowrap;
						padding: 10px 15px;
						display: flex;
						align-items: center;
					}

					.profile-menu-item:HOVER {
						background-color: #4a4d54;
					}

					.profile-menu-item div i {
						margin-right: 15px;
						font-size: 16px;
						color: white;
						
					}

					.profile-menu-item a div  {
						
						color: white;
						
					}

					.profile-menu-item div span {
						
						font-size: 14px;
						
						
					}

				`}</Style>

				<div className="profile button" style={{ margin: 0 }} onClick={() => {
					this.setState({ expand: !this.state.expand });
					this.profileMenu.slideToggle();
				}}>
					<img alt="profile" className="profile-image"
						src={(!this.state.user[AUTHEN_IMG] || this.state.user[AUTHEN_IMG] == '') ? require('./responsive/phoenix-viewer-logo.png').default : `/auth/profile/uploader_read?file=${this.state.user[AUTHEN_IMG]}`}
					/>
					<div className="profile-name">{get(this.state.user[AUTHEN_USERNAME], '')}</div>
					<span className="profile-role box_line">
						{get(this.state.user[AUTHEN_EMAIL], '')}
					</span>

				</div>
				<div className='profile-menu' id={this.id}>
					<li className="profile-menu-item" ><Logout /></li>
					<li className="profile-menu-item" ><Link to={App.link('/auth/profile/view')}><div className='box_flex'><i className="pi pi-user" ></i><span>Profile</span></div></Link></li>
				</div >



			</>
		)
	}

	componentDidMount() {
		global.getUser().then(res => {
			if (res) {
				this.setState({ user: res })
			}
		})
		this.profileMenu = $(`#${this.id}`);
	}
}

export default Namecard;
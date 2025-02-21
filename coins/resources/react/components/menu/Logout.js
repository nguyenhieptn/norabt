import React, { Component } from 'react'

class Logout extends Component {
	constructor(props) {
		super(props);
		this.struct = {
			[AUTHEN_USERNAME]: {
				[INPUT_NAME]: AUTHEN_USERNAME,
				[INPUT_TYPE]: 'text',
				[INPUT_NULL]: false,
				[INPUT_DEFAULT]: this.props.value
			}
		}
	}



	render() {
		return (
			<div className="" style={{ display: 'flex' }} onClick={() => { logout() }}>
				<i className="pi pi-sign-out"></i><span>Logout</span>
			</div>
		)
	}
}






export default Logout
import React, { Component } from 'react'

class RegisterView extends Component {

	constructor(props) {
		super(props);

		this.state = {
			
		}
		this.struct = {
			[USER_EMAIL]: {
				[INPUT_NAME]: lang(USER_EMAIL),
				[INPUT_TYPE]: 'text',
				[INPUT_NULL]: false,
				[INPUT_VALIDATE]: 'email'

			},
			[USER_MOBILE]: {
				[INPUT_NAME]: lang(USER_MOBILE),
				[INPUT_TYPE]: 'text',
				[INPUT_NULL]: false,

			},
			[USER_PASSWD]: {
				[INPUT_NAME]: lang(USER_PASSWD),
				[INPUT_TYPE]: 'password',
				[INPUT_NULL]: false,

			},
			'USER_PASSWD_REPEATE': {
				[INPUT_NAME]: lang('Nhập lại Mật khẩu'),
				[INPUT_TYPE]: 'password',
				[INPUT_NULL]: false,

			},
		}

	}


	render() {

		return (
			<div className='box_flex' style={{justifyContent:'center'}}>

				<div className='box_flex' style={{maxWidth:400}}>
					<div className='box_flex' style={{justifyContent:'center'}}>
						<img src={{AP}}></img>
					</div>
				</div>


			</div>
		);
	}
}

export default RegisterView;

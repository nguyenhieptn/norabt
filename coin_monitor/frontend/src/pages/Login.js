import React from 'react';
import { InputText } from 'primereact/inputtext';
import { Button } from 'primereact/button';

export const Login = (props) => {

	return (
		<div className="login-body">
			<div className="login-image">
				<img src={`public/assets/layout/images/pages/login-${props.colorScheme === 'light' ? 'ondark' : 'onlight'}.png`} alt="atlantis" />
			</div>
			<div className="login-panel p-fluid">
				<div className="flex flex-column">
					<div className="flex align-items-center mb-6 logo-container">
						<img src={`public/assets/layout/images/logo-${props.colorScheme === 'light' ? 'dark' : 'light'}.png`} className="login-logo" alt="login-logo"/>
						<img src={`public/assets/layout/images/appname-${props.colorScheme === 'light' ? 'dark' : 'light'}.png`} className="login-appname" alt="login-appname"/>
					</div>
					<div className="form-container">
						<span className="p-input-icon-left">
							<i className="pi pi-envelope"></i>
							<InputText value="email" type="text" placeholder="Email" />
						</span>
						<span className="p-input-icon-left">
							<i className="pi pi-key"></i>
							<InputText value="password" type="password" placeholder="Password" />
						</span>
						<button className="flex p-link">Forgot your password?</button>
					</div>
					<div className="button-container">
						<Button type="button" label="Login"></Button>
						<span>Don’t have an account?<button className="p-link" >Sign-up here</button></span>
					</div>
				</div>

				<div className="login-footer flex align-items-center">
					<div className="flex align-items-center login-footer-logo-container">
						<img src="public/assets/layout/images/logo-gray.png" className="login-footer-logo" alt="login-footer-logo" />
						<img src="public/assets/layout/images/appname-gray.png" className="login-footer-appname" alt="login-footer-appname" />
					</div>
					<span>Copyright 2021</span>
				</div>
			</div>
		</div>
	)
}
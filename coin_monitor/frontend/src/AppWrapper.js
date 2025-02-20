import React, { useEffect, useState } from 'react';
import { Route, withRouter, useLocation } from 'react-router-dom';
import App from './App';
import { Login } from './pages/Login';
import { Error } from './pages/Error';
import { NotFound } from './pages/NotFound';
import { Access } from './pages/Access';
import { get } from './helpers/Default';


export const ThemeContext = React.createContext({
    theme: localStorage.getItem('colorScheme')
});

const AppWrapper = (props) => {
	const [colorScheme, setColorScheme] = useState(get(window.localStorage.getItem('colorScheme'), 'dark'))
	const [theme, setTheme] = useState('blue');
	const [componentTheme, setComponentTheme] = useState('blue');

	let location = useLocation();

	useEffect(() => {
		window.scrollTo(0, 0)
	}, [location]);

	useEffect(()=>{
		onColorSchemeChange(colorScheme)
	}, [])

	const onColorSchemeChange = (scheme) => {
		if(scheme  == 'light'   ){
			global.App.color = "#44486D";
		}else{
			global.App.color = 'white';
		}
		changeStyleSheetUrl('layout-css', 'layout-' + scheme + '.css', 1);
		changeStyleSheetUrl('theme-css', 'theme-' + scheme + '.css', 1);
		setColorScheme(scheme);
		window.localStorage.setItem('colorScheme', scheme)
	}

	const changeStyleSheetUrl = (id, value, from) => {
		const element = document.getElementById(id);
		const urlTokens = element.getAttribute('href').split('/');

		if (from === 1) {           // which function invoked this function - change scheme
			urlTokens[urlTokens.length - 1] = value;
		} else if (from === 2) {       // which function invoked this function - change color
			urlTokens[urlTokens.length - 2] = value;
		}

		const newURL = urlTokens.join('/');

		replaceLink(element, newURL);
	}

	const onMenuThemeChange = (theme) => {
		const layoutLink = document.getElementById('layout-css');
		const href = 'public/assets/layout/css/' + theme + '/layout-' + colorScheme + '.css';

		replaceLink(layoutLink, href);
		setTheme(theme);
	}

	const onComponentThemeChange = (theme) => {
		const themeLink = document.getElementById('theme-css');
		const href = 'public/assets/theme/' + theme + '/theme-' + colorScheme + '.css';

		replaceLink(themeLink, href);
		setComponentTheme(theme);
	}

	const replaceLink = (linkElement, href, callback) => {
		const id = linkElement.getAttribute('id');
		const cloneLinkElement = linkElement.cloneNode(true);

		cloneLinkElement.setAttribute('href', href);
		cloneLinkElement.setAttribute('id', id + '-clone');

		linkElement.parentNode.insertBefore(cloneLinkElement, linkElement.nextSibling);

		cloneLinkElement.addEventListener('load', () => {
			linkElement.remove();
			cloneLinkElement.setAttribute('id', id);

			if (callback) {
				callback();
			}
		});
	}

	switch (props.location.pathname) {
		case '/login':
			return <Route path="/login" render={() => <Login colorScheme={colorScheme} />} />
		case '/error':
			return <Route path="/error" render={() => <Error colorScheme={colorScheme} />} />
		case '/notfound':
			return <Route path="/notfound" render={() => <NotFound colorScheme={colorScheme} />} />
		case '/access':
			return <Route path="/access" render={() => <Access colorScheme={colorScheme} />} />
		default:
			return <ThemeContext.Provider value={colorScheme}><App colorScheme={colorScheme} onColorSchemeChange={onColorSchemeChange}
				componentTheme={componentTheme} onComponentThemeChange={onComponentThemeChange}
				theme={theme} onMenuThemeChange={onMenuThemeChange} /></ThemeContext.Provider>;
	}

}

export default withRouter(AppWrapper);
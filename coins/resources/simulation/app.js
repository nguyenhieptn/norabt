require('./bootstrap');



/**
 * Next, we will create a fresh React component instance and attach it to
 * the page. Then, you may begin adding components to this application
 * or customize the JavaScript scaffolding to fit your unique needs.
 */

import React, { lazy, Suspense } from 'react';
import { render } from 'react-dom'
import { Route, Link, BrowserRouter as Router, Switch } from 'react-router-dom';
import Layout from './components/common/Layout'
import Loading from './components/common/Loading'

import * as qs from 'query-string';
import 'primereact/resources/themes/nova-light/theme.css';
import 'primereact/resources/primereact.min.css';
import 'primeicons/primeicons.css';
import 'primeflex/primeflex.css';


global.App = {};
App.pages = {};
App.parsed = {};
App.symbol = get(localStorage.getItem('lab_selected_symbol'), '');


var pageLoader = require.context('./pages/', true, /\.js$/, 'lazy');
pageLoader.keys().forEach((key) => {
	var match = /.*\/([^\/]+)\/([^\.]+)\.js/.exec(key);
	if (match) {
		var pageName = match[1] + match[2];
		if (match[1] == 'user') return;
		App.pages[pageName.toLowerCase()] = lazy(() => { return import(/* webpackChunkName: "./react/pages/[request]" */'./pages/' + match[1] + '/' + match[2] + '.js') });
	}
});

App.loading = (flag, text) => {
	App.Loading.loading(flag, text);
	return '';
}

App.getInitialProps = (search) => {
	search = search.replace(/^[^?]*/, '');
	var parsed = qs.parse(search);
	App.parsed = parsed;
}

App.link = (link) => {
	return `/lab/#${link}`
}

getUser().then((user) => {

	// Chưa đăng nhập: error_handle trong getUser đã điều hướng về /login.
	if (!user) return;

	render(<Router ref={router => App.router = router}>

		<Layout ref={layout => App.Layout = layout}>

			<Suspense fallback={<Loading flag={true} text="Loading..." />}>

				<Switch>
					<Route ref={route => App.route = route}

						component={(props) => {

							var hash = props.location.hash;
							var match = /.*#\/(\w+)\/(\w+)\/(\w+).*/.exec(hash);

							if (match) {
								var folder = match[1];
								var page = match[2];
								var func = match[3];
							} else {

								window.location.href = '/lab/#/admin/lab_watchlist/view'

							}

							App.getInitialProps(props.location.hash);
							var pageIndex = folder + page + func;
							var Page = App.pages[pageIndex];

							if (Page) {
								return (<Page key={`${App.symbol}_${pageIndex}`} />);
							} else {
								return ''
							}

						}} />

				</Switch>

			</Suspense>

			<Loading ref={(loading) => { App.Loading = loading }} flag={false} text="Loading..." />

		</Layout>

	</Router>, document.getElementById('app'));


});

App.isMobile = () => {
	return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}











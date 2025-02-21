import React, { Component } from 'react'
import(/* webpackMode: "eager" */'./responsive/menu.scss')
import Namecard from './Namecard'
import { Link } from 'react-router-dom';
import mnf from './menu_func';
import SelectStrategy from '../admin/SelectStrategy';
import SelectAccount from '../admin/SelectAccount';
import SelectAccountTestnet from '../admin/SelectAccountTestnet';


class Menu extends Component {

	constructor(props) {
		super(props);
		this.id = makeId();

		this.state = {
			selected: 'home',
			user: {},
		}

		App.menu = this;

		this.struct = {

			'/admin/testnet_order_track/view': {
				name: lang(ORDER_TRACK_TABLE),
				icon: 'fa fa-video-camera',
				link: App.link('/admin/testnet_order_track/view'),
				action: null,
				children: null,
				condition: () => this.state.user[AUTHEN_GROUP] == 0 || this.state.user[AUTHEN_GROUP] == 4
			},
			'/admin/testnet_indicator/view': {
				name: 'Indicator',
				icon: 'fa fa-video-camera',
				link: App.link('/admin/testnet_indicator/view'),
				action: null,
				children: null,
				condition: () => this.state.user[AUTHEN_GROUP] == 0 || this.state.user[AUTHEN_GROUP] == 4
			},
			'/admin/strategies/view': {
				name: lang(STRATEGIES_TABLE),
				icon: 'pi pi-android',
				link: App.link('/admin/strategies/view'),
				action: null,
				children: null,
				condition: () =>  this.state.user[AUTHEN_GROUP] !== 4,
			},

			'/admin/testnet/view': {
				name: lang('Dashboard'),
				icon: 'pi pi-home',
				link: App.link('/admin/testnet/view'),
				action: null,
				children: null,
				condition: () =>  this.state.user[AUTHEN_GROUP] !== 4,
			},

			'/admin/testnet_results/view': {
				name: lang(TESTNET_RESULTS_TABLE),
				icon: 'pi pi-heart',
				link: App.link('/admin/testnet_results/view'),
				action: null,
				children: null,
				condition: () => SERVER_LOCATION == 'google' ? false : this.state.user[AUTHEN_GROUP] == 4 ? false : true ,
				
			},



			'Testnet': {
				name: 'Testnet',
				icon: 'pi pi-globe',
				link: null,
				action: null,
				condition: () => SERVER_LOCATION == 'google' ? false : this.state.user[AUTHEN_GROUP] == 4 ? false : true ,
				children: {
					'/admin/testnet_account/view': {
						name: lang(TESTNET_ACCOUNT_TABLE),
						icon: 'fa fa-user',
						link: App.link('/admin/testnet_account/view'),
						action: null,
						children: null,
						condition: null,
					},
					'/admin/testnet/view': {
						name: lang('Dashboard'),
						icon: 'pi pi-home',
						link: App.link('/admin/testnet/view'),
						action: null,
						children: null,
						condition: null,
					},
					'/admin/testnet_results/view': {
						name: lang(TESTNET_RESULTS_TABLE),
						icon: 'pi pi-heart',
						link: App.link('/admin/testnet_results/view'),
						action: null,
						children: null,
						condition: null,
					},
					'/admin/testnet_campaign/view': {
						name: lang(TESTNET_CAMPAIGN_TABLE),
						icon: 'pi pi-thumbs-up',
						link: App.link('/admin/testnet_campaign/view'),
						action: null,
						children: null,
						condition: null,
					},
					'/admin/testnetchart/single': {
						name: 'Chart',
						icon: 'pi pi-chart-line',
						link: App.link('/admin/testnetchart/single'),
						action: null,
						children: null,
						condition: null,
					},
					'/admin/testnetchart/view': {
						name: 'Multi Chart',
						icon: 'pi pi-chart-line',
						link: App.link('/admin/testnetchart/view'),
						action: null,
						children: null,
						condition: null,
					},

					'/admin/testnet_chart/flex': {
						name: lang('Chart Flex'),
						icon: 'pi pi-chart-line',
						link: App.link('/admin/testnet_chart/flex'),
						action: null,
						children: null,
						condition: null,
					},


					'/admin/testnet_event_logs/view': {
						name: lang(TESTNET_EVENT_LOGS_TABLE),
						icon: 'pi pi-key',
						link: App.link('/admin/testnet_event_logs/view'),
						action: null,
						children: null,
						condition: null,
					}
				}
			},

			'Alert': {
				name: lang('Alert'),
				icon: 'pi pi-send',
				action: null,
				condition: () => SERVER_LOCATION != 'google' && this.state.user[AUTHEN_GROUP] == 0,
				children: {

					'/admin/alert_order/view': {
						name: 'Alert Order',
						icon: 'pi pi-bell',
						link: App.link('/admin/alert_order/view'),
						action: null,
						children: null,
						condition: null,
					},
					'/admin/alert_order_track/view': {
						name: ' Order Track',
						icon: 'pi pi-bell',
						link: App.link('/admin/alert_order_track/view'),
						action: null,
						children: null,
						condition: null,
					},

					'/admin/alert_volume24h/view': {
						name: ' Volume24h',
						icon: 'pi pi-sun',
						link: App.link('/admin/alert_volume24h/view'),
						action: null,
						children: null,
						condition: null,
					},

					'/admin/alert_volatility/view': {
						name: ' Volatility ',
						icon: 'pi pi-flag',
						link: App.link('/admin/alert_volatility/view'),
						action: null,
						children: null,
						condition: null,
					},


					'/admin/alert_coinmarket/view': {
						name: 'Marketcap ',
						icon: 'pi pi-pencil',
						link: App.link('/admin/alert_coinmarket/view'),
						action: null,
						children: null,
						condition: null,
					},

					'/admin/alert_stock/view': {
						name: 'Stock ',
						icon: 'pi pi-heart',
						link: App.link('/admin/alert_stock/view'),
						action: null,
						children: null,
						condition: null,
					},


					'/admin/schedule_alert/view': {
						name: lang(SCHEDULE_ALERT_TABLE),
						icon: 'fa fa-calendar',
						link: App.link('/admin/schedule_alert/view'),
						action: null,
						children: null,
						condition: null,
					},

					'/admin/alert_system/view': {
						name: 'System',
						icon: 'fa fa-cog',
						link: App.link('/admin/alert_system/view'),
						action: null,
						children: null,
						condition: null,
					},

					




				},

			},
			'/admin/WMA/view': {
				name: lang('Trending'),
				icon: 'fa fa-bar-chart',
	
				children: {

					'/admin/wma_all/view': {
						name: '1D-1W',
						icon: 'fa fa-calendar',
						link: App.link('/admin/wma_all/view'),
						action: null,
						children: null,
						condition: null,
					},

					'/admin/treding4h/view': {
						name: '4H',
						icon: 'fa fa-cog',
						link: App.link('/admin/trending4h/view'),
						action: null,
						children: null,
						condition: null,
					},

					




				},
				action: null,
				condition: () => this.state.user[AUTHEN_GROUP] == 0
			},

			'/admin/sys_config/view': {
				name: lang('System Configuration'),
				icon: 'fa fa-cog',
				link: null,
				action: null,
				children: {
					'/admin/monitor/view': {
						name: lang('Monitor System'),
						icon: 'fa fa-binoculars',
						link: App.link('/admin/monitor/view'),
						action: null,
						children: null,
						condition: null,
					},

					'/auth/authentication/view': {
						name: lang('Account'),
						// name: lang(AUTHENTICATION_TABLE),
						icon: 'fa fa-user-circle-o',
						link: App.link('/auth/authentication/view'),
						action: null,
						children: null,
						condition: () => this.state.user[AUTHEN_GROUP] == 0
					},

					'/admin/tele/view': {
						name: 'Telegram ',
						icon: 'fa fa-telegram',
						children: {

							'/admin/tele_bot/view': {
								name: 'Bot ',
								icon: 'pi pi-eye',
								link:App.link('/admin/tele_bot/view'),
								action: null,
								children: null,
								condition: null,
							},

								
							'/admin/tele_group/view': {
								name: 'Group',
								icon: 'pi pi-eye',
								link:App.link('/admin/tele_group/view'),
								action: null,
								children: null,
								condition: null,
							},
							
						},
						action: null,
						link: null,
						condition: null,
					},


					'/admin/crawler/view': {
						name: 'Crawler',
						icon: 'fa fa-snowflake-o',
						link: null,
						action: null,
						children: {
							'/admin/watchlist/view': {
								name: lang(WATCHLIST_TABLE),
								icon: 'pi pi-eye',
								link: App.link('/admin/watchlist/view'),
								action: null,
								children: null,
								condition: null,
							},

							TimeFrame: {
								name: lang('Time Frame'),
								icon: 'pi pi-calendar',
								link: null,
								action: null,
								children: {
				
									'/admin/price_1s/view': {
										name: lang(PRICE_1S_TABLE),
										icon: 'pi pi-minus-circle',
										link: App.link('/admin/price_1s/view'),
										action: null,
										children: null,
										condition: null,
									},
				
									'/admin/candle_1m/view': {
										name: lang(CANDLE_1M_TABLE),
										icon: 'pi pi-minus-circle',
										link: App.link('/admin/candle_1m/view'),
										action: null,
										children: null,
										condition: null,
									},
				
									'/admin/candle_3m/view': {
										name: lang(CANDLE_3M_TABLE),
										icon: 'pi pi-minus-circle',
										link: App.link('/admin/candle_3m/view'),
										action: null,
										children: null,
										condition: null,
									},
				
									'/admin/candle_15m/view': {
										name: lang(CANDLE_15M_TABLE),
										icon: 'pi pi-minus-circle',
										link: App.link('/admin/candle_15m/view'),
										action: null,
										children: null,
										condition: null,
									},
				
									'/admin/candle_1h/view': {
										name: lang(CANDLE_1H_TABLE),
										icon: 'pi pi-minus-circle',
										link: App.link('/admin/candle_1h/view'),
										action: null,
										children: null,
										condition: null,
									},
									'/admin/candle_4h/view': {
										name: lang(CANDLE_4H_TABLE),
										icon: 'pi pi-minus-circle',
										link: App.link('/admin/candle_4h/view'),
										action: null,
										children: null,
										condition: null,
									},
				
									'/admin/candle_1d/view': {
										name: lang(CANDLE_1D_TABLE),
										icon: 'pi pi-minus-circle',
										link: App.link('/admin/candle_1d/view'),
										action: null,
										children: null,
										condition: null,
									},
				
								},
				
							},
						},
						condition: null,
					},
					system: {
						name: lang('File System'),
						icon: 'fa fa-file',
						link: null,
						action: null,
						condition: () => this.state.user[AUTHEN_GROUP] == 0,
						children: {
							'/uploader/uploader_disks/view': {
								name: lang(UPLOADER_DISKS_TABLE),
								icon: '	fa fa-hdd-o',
								link: App.link('/uploader/uploader_disks/view'),
								action: null,
								children: null,
								condition: null,
							},
							'/uploader/uploader_files/view': {
								name: lang(UPLOADER_FILES_TABLE),
								icon: 'fa fa-file-text-o',
								link: App.link('/uploader/uploader_files/view'),
								action: null,
								children: null,
								condition: null,
							},
							
		
						}
					},

				

				},
				condition: () => this.state.user[AUTHEN_GROUP] != 4
			},


			'EMonitor': {
				// name: lang('LAB'),
				name: 'Nora Monitor',
				icon: 'pi pi-github',
				link: null,
				action: () => { window.open('http://192.168.68.26:8030') },
				children: null,
				condition: () => SERVER_LOCATION == 'google' ? false : this.state.user[AUTHEN_GROUP] == 4 ? false : true ,
			},
			'nora': {
				// name: lang('LAB'),
				name: 'Nora Exchange',
				icon: 'pi pi-github',
				link: null,
				action: () => { window.open(App.link('/exchange/dashboard/view')) },
				children: null,
				condition: () => SERVER_LOCATION != 'google' && App.user[AUTHEN_GROUP] == 0,
				
			},
			'LAB': {
				// name: lang('LAB'),
				name: 'Nora Lab',
				icon: 'pi pi-github',
				link: null,
				action: () => { window.open('/lab/#/admin/dashboard/view') },
				children: null,
				condition: () => SERVER_LOCATION == 'google' ? false : this.state.user[AUTHEN_GROUP] == 4 ? false : true ,
			},

			
			
		}

		this.structNoraExchange = {
			'/exchange/order_track/view': {
				name: lang(ORDER_TRACK_TABLE),
				icon: 'fa fa-video-camera',
				link: App.link('/exchange/order_track/view'),
				action: null,
				children: null,
				condition: null,
			},
			'/exchange/strategies/view': {
				name: lang(STRATEGIES_TABLE),
				icon: 'pi pi-android',
				link: App.link('/exchange/strategies/view'),
				action: null,
				children: null,
				condition: null,
			},
			'/exchange/trades/view': {
				name: lang(TRADES_TABLE),
				icon: 'pi pi-map-marker',
				link: App.link('/exchange/trades/view'),
				action: null,
				children: null,
				condition: null,
			},

			

			'/exchange/dashboard/view': {
				name: lang('Dashboard'),
				icon: 'pi pi-home',
				link: App.link('/exchange/dashboard/view'),
				action: null,
				children: null,
				condition: null,
			},

			'/exchange/Trades': {
				name: lang('Exchange'),
				icon: 'pi pi-twitter',
				link: App.link('/exchange/watchlist/view'),
				action: null,
				children: {

					'/exchange/actions/view': {
						name: lang(ACTIONS_TABLE),
						icon: 'pi pi-video',
						link: App.link('/exchange/actions/view'),
						action: null,
						children: null,
						condition: null,
					},

					'/exchange/trades/view': {
						name: lang(TRADES_TABLE),
						icon: 'pi pi-map-marker',
						link: App.link('/exchange/trades/view'),
						action: null,
						children: null,
						condition: null,
					},

					'/exchange/tradechart/single': {
						name: 'Chart',
						icon: 'pi pi-chart-line',
						link: App.link('/exchange/tradechart/single'),
						action: null,
						children: null,
						condition: null,
					},
				

					'/exchange/users/view': {
						name: 'Account',
						icon: 'pi pi-id-card',
						link: App.link('/exchange/users/view'),
						action: null,
						children: null,
						condition: null,
					},

					'/exchange/orders/view': {
						name: lang(ORDERS_TABLE),
						icon: 'pi pi-shopping-cart',
						link: App.link('/exchange/orders/view'),
						action: null,
						children: null,
						condition: null,
					},

					'/exchange/used_weight/view': {
						name: lang(USED_WEIGHT_TABLE),
						icon: 'fa fa-clone',
						link: App.link('/exchange/used_weight/view'),
						action: null,
						children: null,
						condition: null,
					},
					'/exchange/funding_fee/view': {
						name: lang(FUNDING_FEE_TABLE),
						icon: 'pi pi-money-bill',
						link: App.link('/exchange/funding_fee/view'),
						action: null,
						children: null,
						condition: null,
					},
				},
				condition: null,
			},


			
			'/admin/sys_config/view': {
				name: lang('System Configuration'),
				icon: 'fa fa-cog',
				link: null,
				action: null,
				children: {
					'/admin/monitor/view': {
						name: lang('Monitor System'),
						icon: 'fa fa-binoculars',
						link: App.link('/admin/monitor/view/exchange'),
						action: null,
						children: null,
						condition: null,
					},

					'/auth/authentication/view': {
						name: lang('Account'),
						// name: lang(AUTHENTICATION_TABLE),
						icon: 'fa fa-user-circle-o',
						link: App.link('/auth/authentication/view/exchange'),
						action: null,
						children: null,
						condition: () => this.state.user[AUTHEN_GROUP] == 0
					},

					'/admin/tele/view': {
						name: 'Telegram ',
						icon: 'fa fa-telegram',
						children: {

							'/admin/tele_bot/view': {
								name: 'Bot ',
								icon: 'pi pi-eye',
								link:App.link('/admin/tele_bot/view/exchange'),
								action: null,
								children: null,
								condition: null,
							},

								
							'/admin/tele_group/view': {
								name: 'Group',
								icon: 'pi pi-eye',
								link:App.link('/admin/tele_group/view/exchange'),
								action: null,
								children: null,
								condition: null,
							},
							
						},
						action: null,
						link: null,
						condition: null,
					},


					'/admin/crawler/view': {
						name: 'Crawler',
						icon: 'fa fa-snowflake-o',
						link: null,
						action: null,
						children: {
							'/exchange/watchlist/view': {
								name: lang(WATCHLIST_TABLE),
								icon: 'pi pi-eye',
								link: App.link('/exchange/watchlist/view'),
								action: null,
								children: null,
								condition: null,
							},

							'/exchange/TimeFrame': {
								name: lang('Time Frame'),
								icon: 'pi pi-calendar',
								link: null,
								action: null,
								children: {
				
									'/exchange/price_1s/view': {
										name: lang(PRICE_1S_TABLE),
										icon: 'pi pi-minus-circle',
										link: App.link('/exchange/price_1s/view'),
										action: null,
										children: null,
										condition: null,
									},
				
									'/exchange/candle_1m/view': {
										name: lang(CANDLE_1M_TABLE),
										icon: 'pi pi-minus-circle',
										link: App.link('/exchange/candle_1m/view'),
										action: null,
										children: null,
										condition: null,
									},
				
									'/exchange/candle_3m/view': {
										name: lang(CANDLE_3M_TABLE),
										icon: 'pi pi-minus-circle',
										link: App.link('/exchange/candle_3m/view'),
										action: null,
										children: null,
										condition: null,
									},
				
									'/exchange/candle_15m/view': {
										name: lang(CANDLE_15M_TABLE),
										icon: 'pi pi-minus-circle',
										link: App.link('/exchange/candle_15m/view'),
										action: null,
										children: null,
										condition: null,
									},
				
									'/exchange/candle_1h/view': {
										name: lang(CANDLE_1H_TABLE),
										icon: 'pi pi-minus-circle',
										link: App.link('/exchange/candle_1h/view'),
										action: null,
										children: null,
										condition: null,
									},
									'/exchange/candle_4h/view': {
										name: lang(CANDLE_4H_TABLE),
										icon: 'pi pi-minus-circle',
										link: App.link('/exchange/candle_4h/view'),
										action: null,
										children: null,
										condition: null,
									},
				
									'/exchange/candle_1d/view': {
										name: lang(CANDLE_1D_TABLE),
										icon: 'pi pi-minus-circle',
										link: App.link('/exchange/candle_1d/view'),
										action: null,
										children: null,
										condition: null,
									},
				
								},
				
							},
						},
						condition: null,
					},


					system: {
						name: lang('File System'),
						icon: 'fa fa-file',
						link: null,
						action: null,
						condition: () => this.state.user[AUTHEN_GROUP] == 0,
						children: {
							'/uploader/uploader_disks/view': {
								name: lang(UPLOADER_DISKS_TABLE),
								icon: '	fa fa-hdd-o',
								link: App.link('/uploader/uploader_disks/view/exchange'),
								action: null,
								children: null,
								condition: null,
							},
							'/uploader/uploader_files/view': {
								name: lang(UPLOADER_FILES_TABLE),
								icon: 'fa fa-file-text-o',
								link: App.link('/uploader/uploader_files/view/exchange'),
								action: null,
								children: null,
								condition: null,
							},
							
		
						}
					},

				

				},
				condition: null,
			},


			// '/exchange/watchlist/view': {
			// 	name: lang(WATCHLIST_TABLE),
			// 	icon: 'pi pi-eye',
			// 	link: App.link('/exchange/watchlist/view'),
			// 	action: null,
			// 	children: null,
			// 	condition: null,
			// },

			


			// '/exchange/TimeFrame': {
			// 	name: lang('Time Frame'),
			// 	icon: 'pi pi-calendar',
			// 	link: null,
			// 	action: null,
			// 	children: {

			// 		'/exchange/price_1s/view': {
			// 			name: lang(PRICE_1S_TABLE),
			// 			icon: 'pi pi-minus-circle',
			// 			link: App.link('/exchange/price_1s/view'),
			// 			action: null,
			// 			children: null,
			// 			condition: null,
			// 		},

			// 		'/exchange/candle_1m/view': {
			// 			name: lang(CANDLE_1M_TABLE),
			// 			icon: 'pi pi-minus-circle',
			// 			link: App.link('/exchange/candle_1m/view'),
			// 			action: null,
			// 			children: null,
			// 			condition: null,
			// 		},

			// 		'/exchange/candle_3m/view': {
			// 			name: lang(CANDLE_3M_TABLE),
			// 			icon: 'pi pi-minus-circle',
			// 			link: App.link('/exchange/candle_3m/view'),
			// 			action: null,
			// 			children: null,
			// 			condition: null,
			// 		},

			// 		'/exchange/candle_15m/view': {
			// 			name: lang(CANDLE_15M_TABLE),
			// 			icon: 'pi pi-minus-circle',
			// 			link: App.link('/exchange/candle_15m/view'),
			// 			action: null,
			// 			children: null,
			// 			condition: null,
			// 		},

			// 		'/exchange/candle_1h/view': {
			// 			name: lang(CANDLE_1H_TABLE),
			// 			icon: 'pi pi-minus-circle',
			// 			link: App.link('/exchange/candle_1h/view'),
			// 			action: null,
			// 			children: null,
			// 			condition: null,
			// 		},
			// 		'/exchange/candle_4h/view': {
			// 			name: lang(CANDLE_4H_TABLE),
			// 			icon: 'pi pi-minus-circle',
			// 			link: App.link('/exchange/candle_4h/view'),
			// 			action: null,
			// 			children: null,
			// 			condition: null,
			// 		},

			// 		'/exchange/candle_1d/view': {
			// 			name: lang(CANDLE_1D_TABLE),
			// 			icon: 'pi pi-minus-circle',
			// 			link: App.link('/exchange/candle_1d/view'),
			// 			action: null,
			// 			children: null,
			// 			condition: null,
			// 		},

			// 	},

			// },


			// '/exchange/accounts': {
			// 	name: lang('Account'),
			// 	icon: 'pi pi-user-edit',
			// 	link: null,
			// 	action: null,
			// 	children: {
			// 		'/auth/authentication/view': {
			// 			name: lang(AUTHENTICATION_TABLE),
			// 			icon: 'fa fa-user-circle-o',
			// 			link: App.link('/auth/authentication/view/exchange'),
			// 			action: null,
			// 			children: null,
			// 			condition: null,
			// 		},

			// 	},
			// 	condition: () => this.state.user[AUTHEN_GROUP] == 0
			// },

			// system: {
			// 	name: lang('System'),
			// 	icon: 'fa fa-cog',
			// 	link: null,
			// 	action: null,
			// 	condition: () => this.state.user[AUTHEN_GROUP] == 0,
			// 	children: {
			// 		'/uploader/uploader_disks/view': {
			// 			name: lang(UPLOADER_DISKS_TABLE),
			// 			icon: '	fa fa-hdd-o',
			// 			link: App.link('/uploader/uploader_disks/view/exchange'),
			// 			action: null,
			// 			children: null,
			// 			condition: null,
			// 		},
			// 		'/uploader/uploader_files/view': {
			// 			name: lang(UPLOADER_FILES_TABLE),
			// 			icon: 'fa fa-file-text-o',
			// 			link: App.link('/uploader/uploader_files/view/exchange'),
			// 			action: null,
			// 			children: null,
			// 			condition: null,
			// 		},

			// 	}
			// },



			// '/admin/monitor/view': {
			// 	name: lang('Monitor'),
			// 	icon: 'fa fa-binoculars',
			// 	link: App.link('/admin/monitor/view'),
			// 	action: null,
			// 	children: null,
			// 	condition: null,
			// },


			
			'EMonitor': {
				// name: lang('LAB'),
				name: 'Nora Monitor',
				icon: 'pi pi-github',
				link: null,
				action: () => { window.open('http://192.168.68.26:8030') },
				children: null,
				condition: () => SERVER_LOCATION != 'google',
			},
			'exchange': {
				// name: lang('LAB'),
				name: 'Nora Testnet',
				icon: 'pi pi-github',
				link: null,
				action: () => { window.open('/admin/#/admin/testnet/view') },
				children: null,
				condition: () => SERVER_LOCATION != 'google',
			},
			'LAB': {
				// name: lang('LAB'),
				name: 'Nora Lab',
				icon: 'pi pi-github',
				link: null,
				action: () => { window.open('/lab/#/admin/dashboard/view') },
				children: null,
				condition: () => SERVER_LOCATION != 'google',
			},
			


		}


	}


	componentDidMount() {
		getUser().then((user) => {
			if (user) {
				this.setState({ user })
			}
		})

		var match = /#([\w\/]+).*/.exec(window.location.hash);

		if (match) {
			this.setActive(match[1]);
		}

		if (window.location.hash.includes('exchange')) {
			document.title = "Exchange Crypto";
		} else {
			document.title = "Testnet Crypto";
		}


	}
	renderSelectAccount() {


		if (window.location.hash.includes('exchange')) {
			return (
				<SelectAccount></SelectAccount>
			)
		} else {
			return (
				<SelectAccountTestnet></SelectAccountTestnet>
			)
		}
	}

	setActive(page) {
		this.setState({
			selected: page
		})
	}

	onClickHandle(key) {

		this.setState({ selected: key })

		if (App.Layout) App.Layout.setState({
			menu: App.Layout.loadDefault()
		})

		$(".modal-backdrop").remove();
	}


	drawMenu(item, key) {

		if (item.condition && !item.condition()) return { comp: '', isSelected: false };

		var isSelected = this.state.selected == key;
		var isChildSelected = false;

		if (item.children) {
			var children = [];
			Object.keys(item.children).map(id => {
				var result = this.drawMenu(item.children[id], id);
				children.push(result.comp);
				if (result.isSelected) isChildSelected = true;
			});
			var comp = <li key={key} className="menu_collapse">
				<div className={`menu_group_button menu_item ${isSelected ? 'menu_item_selected' : ''} ${isChildSelected ? 'expand' : ''}`} onClick={(event) => {
					mnf.toggleClass(event.currentTarget, 'expand', event)
				}}>
					<div><i className={item.icon}></i><span>{item.name}</span></div>
				</div>
				<ul className="menu_group">
					{children}
				</ul>
			</li>
			return { comp: comp, isSelected: isChildSelected };
		} else {
			var comp = '';
			if (item.link) {
				comp = <li key={key} className={`menu_item ${isSelected ? 'menu_item_selected' : ''}`} onClick={event => { this.onClickHandle(key) }}><Link to={item.link}><div><i className={item.icon}></i><span>{item.name}</span></div></Link></li>
			} else if (item.action) {
				comp = <li key={key} className={`menu_item ${isSelected ? 'menu_item_selected' : ''}`} onClick={event => { this.onClickHandle(key) }}><div onClick={event => item.action(event)}><i className={item.icon}></i><span>{item.name}</span></div></li>
			} else {
				comp = <li key={key} className={`menu_item ${isSelected ? 'menu_item_selected' : ''}`} onClick={event => { this.onClickHandle(key) }}><div><i className={item.icon}></i><span>{item.name}</span></div></li>
			}

			return { comp, isSelected }

		}
	}

	renderTopLeftLogo() {
		if (window.location.hash.includes('exchange')) {
			return (
				<div style={{ marginTop: '-2px' }}>

					<img width={'160px'} src={'/assets/img/Eexchange_logo.png'} ></img>
				</div>
			)
		} else {
			return (
				<div style={{ marginTop: '-2px' }}>

					<img width={'160px'} src={'/assets/img/ETestnet_logo.png'} ></img>

				</div>
			)
		}
	}


	render() {
		var stateMenu = this.props.layout.getMenuState();

		return (
			<>
				<div className='box_flex'>
					<div className={"topbar_left " + stateMenu}>
						<div className='box_flex topbar_left_logo'>
							{/* <img style={{height: '90%'}} src={require('./responsive/ecocloud-white.png')}></img> */}

							{/* {
									window.location.hash.includes('exchange') ? <div style={{ margin: 'auto 15px', fontSize: 20 }}>{APP_NAME}</div> : <div style={{ margin: 'auto 15px', fontSize: 20 }}>{APP_NAME}</div>
							} */}
							{/* <div style={{ margin: 'auto 15px', fontSize: 20 }}>{APP_NAME}</div> */}

							{/* <div style={{ margin: 'auto 15px', fontSize: 20 }}>{window.location.hash.includes('exchange') ?  'Nora Exchange': 'Nora Testnet' }</div> */}
							<div style={{ margin: 'auto 15px', fontSize: 20 }}>{this.renderTopLeftLogo()}</div>
						</div>
						<div className="button topbar_button" onClick={(event) => {
							if (stateMenu == '') {
								this.props.layout.setState({ menu: 'closed' })
							} else {
								this.props.layout.setState({ menu: '' })
							}
						}}><i style={{ fontSize: 32 }} className="fa fa-angle-left"></i>
						</div>
					</div>



					<div className="topbar_right">


						<div className='box_flex topbar_right_sel '  >
							{/* {this.state.selected == '/admin/testnet/view'
								? <SelectStrategy></SelectStrategy>
								: this.state.selected.includes('testnet') 
								? <SelectAccountTestnet></SelectAccountTestnet>
								: <SelectAccount></SelectAccount>
							} */}
							{/* {this.state.selected == this.state.selected.includes('testnet') 
								? <SelectAccountTestnet></SelectAccountTestnet>
								: <SelectAccount></SelectAccount>
							} */}
							{this.state.selected.includes('testnet')
								? <SelectAccountTestnet></SelectAccountTestnet>
								: <SelectAccount></SelectAccount>
							}

							{/* {this.renderSelectAccount()} */}
						</div>

						<div className="topbar_content">
							{/* <Syslog></Syslog> */}
						</div>




					</div>

				</div>


				<div className={`menu ${stateMenu} menu_closed_lg nano`} id={this.id}>


					<div className='nano-content'>
						<div className={`menu_frame `} >

							<div style={{ background: '#363a41' }}>
								<Namecard />
							</div>

							<ul className="menu_content">

								{
									window.location.hash.includes('exchange') ? Object.keys(this.structNoraExchange).map(key => this.drawMenu(this.structNoraExchange[key], key).comp) : Object.keys(this.struct).map(key => this.drawMenu(this.struct[key], key).comp)
								}

								{/* 
								{Object.keys(this.struct).map(key => this.drawMenu(this.struct[key], key).comp)} */}
							</ul>
						</div>
					</div>

				</div>




			</>
		);
	}
}
export default Menu
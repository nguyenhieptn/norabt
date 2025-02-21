import React, { Component } from 'react'
import(/* webpackMode: "eager" */'./responsive/menu.scss')
import Namecard from './Namecard'


import { Link } from 'react-router-dom';
import mnf from './menu_func';
import Syslog from './Syslog';
import SelectSymbol from '../admin/SelectSymbol';
import SelectStrategy from '../admin/SelectStrategy';
import SelectAccountLab from '../admin/SelectAccountTestnet';


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

			// '/admin/lab_account/view': {
			// 	name: lang(LAB_ACCOUNT_TABLE),
			// 	icon: 'fa fa-user',
			// 	link: App.link('/admin/lab_account/view'),
			// 	action: null,
			// 	children: null,
			// 	condition: null,
			// },
			'/admin/lab_account_group/view': {
				name: lang(LAB_ACCOUNT_TABLE),
				icon: 'fa fa-user',
				link: App.link('/admin/lab_account_group/view'),
				action: null,
				children: null,
				condition: null,
			},

			// '/admin/lab_strategies/view': {
			// 	name: lang(LAB_STRATEGIES_TABLE),
			// 	icon: 'fa fa-android',
			// 	link: App.link('/admin/lab_strategies/view'),
			// 	action: null,
			// 	children: null,
			// 	condition: null,
			// },

			'/admin/lab_strategies_group/view': {
				name: lang(LAB_STRATEGIES_TABLE),
				icon: 'fa fa-android',
				link: App.link('/admin/lab_strategies_group/view'),
				action: null,
				children: null,
				condition: null,
			},

			'/admin/dashboard/view': {
				name: lang('Dashboard'),
				icon: 'pi pi-home',
				link: App.link('/admin/dashboard/view'),
				action: null,
				children: null,
				condition: null,
			},
			'/admin/bot_ruin/view': {
				name: lang('RUIN'),
				icon: 'fa fa-calendar-check-o',
				link: App.link('/admin/bot_ruin/view'),
				action: null,
				children: null,
				condition: null,
			},

			'Lab': {
				name: lang('Lab'),
				icon: 'fa fa-flask',
				link: null,
				action: null,
				children: {
					
					'/admin/chart/view': {
						name: lang('Chart'),
						icon: 'pi pi-chart-line',
						link: App.link('/admin/chart/view'),
						action: null,
						children: null,
						condition: null,
					},
					'/admin/chart/flex': {
						name: lang('Chart Flex'),
						icon: 'pi pi-chart-line',
						link: App.link('/admin/chart/flex'),
						action: null,
						children: null,
						condition: null,
					},

					'/admin/lab_campaigns/view': {
						name: 'Campaign',
						icon: 'pi pi-thumbs-up',
						link: App.link('/admin/lab_campaigns/view'),
						action: null,
						children: null,
						condition: null,
					},
		
					'/admin/lab_results/view': {
						name: 'Result',
						icon: 'pi pi-heart',
						link: App.link('/admin/lab_results/view'),
						action: null,
						children: null,
						condition: null,
					},

					'/admin/lab_account_risk/view': {
						name: 'Account Risk',
						icon: 'pi pi-heart',
						link: App.link('/admin/lab_account_risk/view'),
						action: null,
						children: null,
						condition: null,
					},

					
					'/admin/lab_schedule/view': {
						name: lang('Schedule'),
						icon: 'fa fa-calendar-check-o',
						link: App.link('/admin/lab_schedule/view'),
						action: null,
						children: null,
						condition: null,
					},
		
	
		
					'setting': {
						name: lang('Database Setting'),
						icon: 'fa fa-cog',
						link: App.link('/control/control/view'),
						action: null,
						children: null,
						condition: null,
					},

				},

			},

			optimization: {
				name: lang('Optimization'),
				icon: 'fa fa-diamond',
				link: null,
				action: null,
				children: {

					'/admin/optimize/view': {
						name: lang('Optimization'),
						icon: 'pi pi-chart-line',
						link: App.link('/admin/optimize/view'),
						action: null,
						children: null,
						condition: null,
					},

					'/admin/opt_result/view': {
						name: lang('Result'),
						icon: 'pi pi-heart',
						link: App.link('/admin/opt_result/view'),
						action: null,
						children: null,
						condition: null,
					},

					'/admin/lab_opt_schedule/view': {
						name: lang(LAB_OPT_SCHEDULE_TABLE),
						icon: 'fa fa-calendar-check-o',
						link: App.link('/admin/lab_opt_schedule/view'),
						action: null,
						children: null,
						condition: null,
					},
					// '/admin/system_info/view': {
					// 	name: 'Hardware Management',
					// 	icon: 'fa fa-eye',
					// 	link: App.link('/admin/system_info/view'),
					// 	action: null,
					// 	children: null,
					// 	condition: null,
					// }     
				},

			},

			'Tool': {
				name: lang('Tool'),
				icon: 'fa fa-cubes',
				link: null,
				action: null,
				children: {
					'/admin/lab_node/view': {
						name: lang(LAB_NODE_TABLE),
						icon: 'fa fa-cloud',
						link: App.link('/admin/lab_node/view'),
						action: null,
						children: null,
						condition: null,
					},

					TopBTC: {

						name: lang('Top BTC'),
						icon: 'fa fa-rocket',
						link: null,
						action: null,
						children: {

							'/admin/top_btc/view': {
								name: lang('Top BTC'),
								icon: 'pi pi-inbox',
								link: App.link('/admin/top_btc/view'),
								action: null,
								children: null,
								condition: null,
							},
							'/admin/chart_btc/view': {
								name: lang('Chart BTC'),
								icon: 'pi pi-shield',
								link: App.link('/admin/chart_btc/view'),
								action: null,
								children: null,
								condition: null,
							},
							'/admin/top_sum/view': {
								name: lang('Top BTC Sum'),
								icon: 'pi pi-shield',
								link: App.link('/admin/top_sum/view'),
								action: null,
								children: null,
								condition: null,
							}
						},

					},

					'/admin/History/view': {
						name: lang('Coinmarket History'),
						icon: 'fa fa-history',
						link: App.link('/admin/rank_history/view'),
						action: null,
						children: null,
						condition: null,
					},

					analytics: {
						name: lang('Analytic'),
						icon: 'pi pi-directions',
						link: null,
						action: null,
						children: {

							'/admin/volume24h/view': {
								name: lang('Volume'),
								icon: 'pi pi-inbox',
								link: App.link('/admin/volume24h/view'),
								action: null,
								children: null,
								condition: null,
							},
							'/admin/fluctuation/view': {
								name: lang('Volatility'),
								icon: 'pi pi-shield',
								link: App.link('/admin/fluctuation/view'),
								action: null,
								children: null,
								condition: null,
							},
							'/admin/table_fluctuation/view': {
								name: lang('Fluctuation'),
								icon: 'pi pi-shield',
								link: App.link('/admin/table_fluctuation/view'),
								action: null,
								children: null,
								condition: null,
							}
						},

					},


				},

			},


			'/admin/sys_config/view': {
				name: lang('System Configuration'),
				icon: 'fa fa-cog',
				link: null,
				action: null,
				children: {
					'/admin/monitor/view': {
						name: lang('Monitor'),
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
						// link: null,
						action: null,
						children: null,
						condition: () => this.state.user[AUTHEN_GROUP] == 0
					},

					'/admin/system_alert/view': {
						name: 'Telegram Bot',
						icon: 'fa fa-telegram',
						// link: App.link('/admin/system_alert/view/exchange'),
						link: null,
						action: null,
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
						condition: null,
					},


					'/admin/crawler/view': {
						name: 'Crawler',
						icon: 'fa fa-snowflake-o',
						link: null,
						action: null,
						children: {
							'/admin/lab_watchlist/view': {
								name: lang(LAB_WATCHLIST_TABLE),
								icon: 'pi pi-eye',
								link: App.link('/admin/lab_watchlist/view'),
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



									'/admin/lab_candle_1m/view': {
										name: lang(LAB_CANDLE_1M_TABLE),
										icon: 'pi pi-minus-circle',
										link: App.link('/admin/lab_candle_1m/view'),
										action: null,
										children: null,
										condition: null,
									},

									'/admin/lab_candle_3m/view': {
										name: lang(LAB_CANDLE_3M_TABLE),
										icon: 'pi pi-minus-circle',
										link: App.link('/admin/lab_candle_3m/view'),
										action: null,
										children: null,
										condition: null,
									},
									'/admin/lab_candle_15m/view': {
										name: lang(LAB_CANDLE_15M_TABLE),
										icon: 'pi pi-minus-circle',
										link: App.link('/admin/lab_candle_15m/view'),
										action: null,
										children: null,
										condition: null,
									},
									'/admin/lab_candle_1h/view': {
										name: lang(LAB_CANDLE_1H_TABLE),
										icon: 'pi pi-minus-circle',
										link: App.link('/admin/lab_candle_1h/view'),
										action: null,
										children: null,
										condition: null,
									},
									'/admin/lab_candle_4h/view': {
										name: lang(LAB_CANDLE_4H_TABLE),
										icon: 'pi pi-minus-circle',
										link: App.link('/admin/lab_candle_4h/view'),
										action: null,
										children: null,
										condition: null,
									},
									'/admin/lab_candle_1d/view': {
										name: lang(LAB_CANDLE_1D_TABLE),
										icon: 'pi pi-minus-circle',
										link: App.link('/admin/lab_candle_1d/view'),
										action: null,
										children: null,
										condition: null,
									},
									'/admin/lab_candle_1w/view': {
										name: lang(LAB_CANDLE_1W_TABLE),
										icon: 'pi pi-minus-circle',
										link: App.link('/admin/lab_candle_1w/view'),
										action: null,
										children: null,
										condition: null,
									},



								},

							},


							'/admin/lab_event_logs/view': {
								name: lang(LAB_EVENT_LOGS_TABLE),
								icon: 'pi pi-key',
								link: App.link('/admin/lab_event_logs/view'),
								action: null,
								children: null,
								condition: null,
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
								// link: null,
								action: null,
								children: null,
								condition: null,
							},
							'/uploader/uploader_files/view': {
								name: lang(UPLOADER_FILES_TABLE),
								icon: 'fa fa-file-text-o',
								link: App.link('/uploader/uploader_files/view/exchange'),
								// link: null,
								action: null,
								children: null,
								condition: null,
							},


						}
					},



				},
				condition: null,
			},



			'EMonitor': {
				// name: lang('Phoenix System'),
				name: lang('Nora Monitor'),
				icon: 'pi pi-star-o',
				link: null,
				action: () => { window.open('http://192.168.68.26:8030') },
				children: null,
				condition: null,
			},


			'exchange': {
				// name: lang('Phoenix System'),
				name: lang('Nora Exchange'),
				icon: 'pi pi-star-o',
				link: null,
				action: () => { window.open('/admin/#/exchange/dashboard/view') },
				children: null,
				condition: ()=>App.user[AUTHEN_GROUP] == 0,
			},

			'phonix': {
				// name: lang('Phoenix System'),
				name: lang('Nora Testnet'),
				icon: 'pi pi-star-o',
				link: null,
				action: () => { window.open('/admin/#/admin/testnet/view') },
				children: null,
				condition: null,
			},

			'/admin/dashboard/lab/doc': {
				name: lang('Document'),
				icon: 'pi pi-star-o',
				link: App.link('/admin/lab_doc/view'),
				action: null,
				children: null,
				condition: null,
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


	render() {
		var stateMenu = this.props.layout.getMenuState();

		return (
			<>

				<div className={"topbar_left " + stateMenu}>
					<div className='box_flex topbar_left_logo'>
						{/* <img style={{height: '90%'}} src={require('./responsive/ecocloud-white.png')}></img> */}
						{/* <div style={{ margin: 'auto 15px', fontSize: 20 }}>{APP_NAME}</div> */}
						{/* <div style={{ margin: 'auto 15px', fontSize: 20 }}>Nora Lab</div> */}
						<div style={{ margin: 'auto 25px', fontSize: 20 }}><img width={'110px'} src={'/assets/img/elap_logo.png'} ></img></div>
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
						{this.state.selected == this.state.selected.includes('dashboard')
							? <SelectStrategy></SelectStrategy>
							: <SelectAccountLab></SelectAccountLab>
						}
					</div>

					<div className="topbar_content">
						{/* <Syslog></Syslog> */}
					</div>




				</div>


				<div className={`menu ${stateMenu} menu_closed_lg nano`} id={this.id}>


					<div className='nano-content'>
						<div className={`menu_frame `} >

							<div style={{ background: '#363a41' }}>
								<Namecard />
							</div>

							<ul className="menu_content">
								{Object.keys(this.struct).map(key => this.drawMenu(this.struct[key], key).comp)}
							</ul>
						</div>
					</div>

				</div>




			</>
		);
	}
}
export default Menu
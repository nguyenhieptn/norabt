
import React, { useState, useEffect, useRef, lazy, Suspense } from 'react';
import { classNames } from 'primereact/utils';
import { Route, useLocation, Redirect } from 'react-router-dom';

import AppTopbar from './AppTopbar';
import AppFooter from './AppFooter';
import AppConfig from './AppConfig';
import AppRightMenu from './AppRightMenu';
import AppMenu from './AppMenu';



import PrimeReact from 'primereact/api';
import { Tooltip } from 'primereact/tooltip';

import 'primereact/resources/primereact.min.css';
import 'primeicons/primeicons.css';
import 'primeflex/primeflex.css';
import './App.scss';

import NeedAuthen from './components/authen/NeedAuthen';
import { get } from './helpers/Default';
import Ploading from './components/common/Ploading';

global.App = {};
global.App.color = 'white';
global.App.pages = {};

var pageLoader = require.context('./pages/', true, /\.js$/, 'lazy');
pageLoader.keys().forEach((key) => {
    var match = /.*\/([^\/]+)\/([^\.]+)\.js/.exec(key);
    if (match) {
        var pageName = match[1] + match[2];
        global.App.pages[pageName.toLowerCase()] = lazy(() => { return import('./pages/' + match[1] + '/' + match[2]) });
    }
});



const App = (props) => {

    const [rightMenuActive, setRightMenuActive] = useState(get(window.localStorage.getItem('rightMenuActive') == 'true', false));
    const [configActive, setConfigActive] = useState(get(window.localStorage.getItem('configActive') == 'true', false));
    const [menuMode, setMenuMode] = useState(get(window.localStorage.getItem('menuMode'), 'sidebar'));
    const [overlayMenuActive, setOverlayMenuActive] = useState(get(window.localStorage.getItem('overlayMenuActive') == 'true', false));
    const [ripple, setRipple] = useState(get(window.localStorage.getItem('ripple') == 'true', true));
    const [sidebarStatic, setSidebarStatic] = useState(get(window.localStorage.getItem('sidebarStatic') == 'true', false));
    const [staticMenuDesktopInactive, setStaticMenuDesktopInactive] = useState(get(window.localStorage.getItem('staticMenuDesktopInactive') == 'true', false));
    const [staticMenuMobileActive, setStaticMenuMobileActive] = useState(get(window.localStorage.getItem('staticMenuMobileActive') == 'true', false));
    const [menuActive, setMenuActive] = useState(get(window.localStorage.getItem('menuActive') == 'true', false));
    const [searchActive, setSearchActive] = useState(get(window.localStorage.getItem('searchActive') == 'true', false));
    const [topbarMenuActive, setTopbarMenuActive] = useState(get(window.localStorage.getItem('topbarMenuActive') == 'true', false));
    const [sidebarActive, setSidebarActive] = useState(get(window.localStorage.getItem('sidebarActive') == 'true', false));
    const [pinActive, setPinActive] = useState(get(window.localStorage.getItem('pinActive') == 'true', false));
    const [activeInlineProfile, setActiveInlineProfile] = useState(get(window.localStorage.getItem('activeInlineProfile') == 'true', false));
    const [resetActiveIndex, setResetActiveIndex] = useState(get(window.localStorage.getItem('resetActiveIndex'), null));
    const copyTooltipRef = useRef();
    const location = useLocation();

    useEffect(() => {
        window.localStorage.setItem('rightMenuActive', rightMenuActive)
        window.localStorage.setItem('configActive', configActive)
        window.localStorage.setItem('menuMode', menuMode)
        window.localStorage.setItem('overlayMenuActive', overlayMenuActive)
        window.localStorage.setItem('ripple', ripple)
        window.localStorage.setItem('sidebarStatic', sidebarStatic)
        window.localStorage.setItem('staticMenuDesktopInactive', staticMenuDesktopInactive)
        window.localStorage.setItem('staticMenuMobileActive', staticMenuMobileActive)
        window.localStorage.setItem('menuActive', menuActive)
        window.localStorage.setItem('searchActive', searchActive)
        window.localStorage.setItem('topbarMenuActive', topbarMenuActive)
        window.localStorage.setItem('sidebarActive', sidebarActive)
        window.localStorage.setItem('pinActive', pinActive)
        window.localStorage.setItem('activeInlineProfile', activeInlineProfile)
        window.localStorage.setItem('resetActiveIndex', resetActiveIndex)
    }, [
        rightMenuActive,
        configActive,
        menuMode,
        overlayMenuActive,
        ripple,
        sidebarStatic,
        staticMenuDesktopInactive,
        staticMenuMobileActive,
        menuActive,
        searchActive,
        topbarMenuActive,
        sidebarActive,
        pinActive,
        activeInlineProfile,
        resetActiveIndex,
    ])

    PrimeReact.ripple = true;

    const menu = [
        {
            label: 'Scaper', icon: 'pi pi-server', to: '/admin/scraper/view'
        },
        {
            label: 'Monitor', icon: 'pi pi-chart-line',
            items: [
                { label: 'By Symbol', icon: 'pi pi-tag', to: '/admin/monitorsymbol/view' },
                { label: 'By Server', icon: 'pi pi-tags', to: '/admin/monitorserver/view' },
            ]
        },
        {
            label: 'System', icon: 'pi pi-cog', to: '/admin/sys/view'
        },
        {
            label: 'Process', icon: 'pi pi-desktop', to: '/admin/scraperprocess/view'
        },
        {
            label: 'Testnet', icon: 'pi pi-clock', to: '/admin/realtime/view'
        },
        {
            label: 'Backtest', icon: 'pi pi-clock', to: '/backtest/chart/view'
        },

        // {
        //     label: 'Favorites', icon: 'pi pi-home',
        //     items: [
        //         { label: 'Dashboard', icon: 'pi pi-home', to: '/' },
        //     ]
        // },
        // {
        //     label: 'UI Kit', icon: 'pi pi-star',
        //     items: [
        //         { label: 'Form Layout', icon: 'pi pi-id-card', to: '/formlayout' },
        //         { label: 'Input', icon: 'pi pi-check-square', to: '/input' },
        //         { label: 'Float Label', icon: 'pi pi-bookmark', to: '/floatlabel' },
        //         { label: 'Invalid State', icon: 'pi pi-exclamation-circle', to: '/invalidstate' },
        //         { label: 'Button', icon: 'pi pi-mobile', to: '/button', className: 'rotated-icon' },
        //         { label: 'Table', icon: 'pi pi-table', to: '/table' },
        //         { label: 'List', icon: 'pi pi-list', to: '/list' },
        //         { label: 'Tree', icon: 'pi pi-share-alt', to: '/tree' },
        //         { label: 'Panel', icon: 'pi pi-tablet', to: '/panel' },
        //         { label: 'Overlay', icon: 'pi pi-clone', to: '/overlay' },
        //         { label: 'Media', icon: "pi pi-image", to: '/media' },
        //         { label: 'Menu', icon: 'pi pi-bars', to: '/menu' },
        //         { label: 'Message', icon: 'pi pi-comment', to: '/message' },
        //         { label: 'File', icon: 'pi pi-file', to: '/file' },
        //         { label: 'Chart', icon: 'pi pi-chart-bar', to: '/chart' },
        //         { label: 'Misc', icon: 'pi pi-circle', to: '/misc' },
        //     ]
        // },
        // {
        //     label: "PrimeBlocks", icon: "pi pi-prime",
        //     items: [
        //         { label: "Free Blocks", icon: "pi pi-eye", to: "/blocks", badge: "NEW" },
        //         { label: "All Blocks", icon: "pi pi-globe", url: "https://www.primefaces.org/primeblocks-react", target: "_blank" }
        //     ]
        // },
        // {
        //     label: 'Utilities', icon: 'pi pi-compass',
        //     items: [
        //         { label: 'Icons', icon: 'pi pi-prime', to: '/icons' },
        //         { label: "PrimeFlex", icon: "pi pi-desktop", url: "https://www.primefaces.org/primeflex", target: "_blank" }
        //     ]
        // },
        // {
        //     label: 'Pages', icon: 'pi pi-briefcase',
        //     items: [
        //         { label: 'Crud', icon: 'pi pi-pencil', to: '/crud' },
        //         { label: 'Calendar', icon: 'pi pi-calendar-plus', to: '/calendar' },
        //         { label: 'Timeline', icon: 'pi pi-calendar', to: '/timeline' },
        //         { label: 'Landing', icon: 'pi pi-globe', url: 'assets/pages/landing.html', target: '_blank' },
        //         { label: 'Login', icon: 'pi pi-sign-in', to: '/login' },
        //         { label: 'Invoice', icon: 'pi pi-dollar', to: '/invoice' },
        //         { label: 'Help', icon: 'pi pi-question-circle', to: '/help' },
        //         { label: 'Error', icon: 'pi pi-times-circle', to: '/error' },
        //         { label: 'Not Found', icon: 'pi pi-exclamation-circle', to: '/notfound' },
        //         { label: 'Access Denied', icon: 'pi pi-lock', to: '/access' },
        //         { label: 'Empty Page', icon: 'pi pi-circle', to: '/empty' }
        //     ]
        // },
        // {
        //     label: 'Hierarchy', icon: 'pi pi-align-left',
        //     items: [
        //         {
        //             label: 'Submenu 1', icon: 'pi pi-align-left',
        //             items: [
        //                 {
        //                     label: 'Submenu 1.1', icon: 'pi pi-align-left',
        //                     items: [
        //                         { label: 'Submenu 1.1.1', icon: 'pi pi-align-left' },
        //                         { label: 'Submenu 1.1.2', icon: 'pi pi-align-left' },
        //                         { label: 'Submenu 1.1.3', icon: 'pi pi-align-left' },
        //                     ]
        //                 },
        //                 {
        //                     label: 'Submenu 1.2', icon: 'pi pi-align-left',
        //                     items: [
        //                         { label: 'Submenu 1.2.1', icon: 'pi pi-align-left' },
        //                         { label: 'Submenu 1.2.2', icon: 'pi pi-align-left' }
        //                     ]
        //                 },
        //             ]
        //         },
        //         {
        //             label: 'Submenu 2', icon: 'pi pi-align-left',
        //             items: [
        //                 {
        //                     label: 'Submenu 2.1', icon: 'pi pi-align-left',
        //                     items: [
        //                         { label: 'Submenu 2.1.1', icon: 'pi pi-align-left' },
        //                         { label: 'Submenu 2.1.2', icon: 'pi pi-align-left' },
        //                         { label: 'Submenu 2.1.3', icon: 'pi pi-align-left' },
        //                     ]
        //                 },
        //                 {
        //                     label: 'Submenu 2.2', icon: 'pi pi-align-left',
        //                     items: [
        //                         { label: 'Submenu 2.2.1', icon: 'pi pi-align-left' },
        //                         { label: 'Submenu 2.2.2', icon: 'pi pi-align-left' }
        //                     ]
        //                 },
        //             ]
        //         }
        //     ]
        // },
        // {
        //     label: 'Start', icon: 'pi pi-download',
        //     items: [
        //         { label: 'Documentation', icon: 'pi pi-question', to: '/documentation' },
        //         { label: 'Buy Now', icon: 'pi pi-shopping-cart', command: () => { window.location = "https://www.primefaces.org/store" } }
        //     ]
        // }
    ];

    const routes = [
        // { parent: 'Dashboard', label: 'Sales Dashboard' },
        // { parent: 'UI Kit', label: 'Form Layout' },
        // { parent: 'UI Kit', label: 'Input' },
        // { parent: 'UI Kit', label: 'Float Label' },
        // { parent: 'UI Kit', label: 'Invalid State' },
        // { parent: 'UI Kit', label: 'Button' },
        // { parent: 'UI Kit', label: 'Table' },
        // { parent: 'UI Kit', label: 'List' },
        // { parent: 'UI Kit', label: 'Panel' },
        // { parent: 'UI Kit', label: 'Tree' },
        // { parent: 'UI Kit', label: 'Overlay' },
        // { parent: 'UI Kit', label: 'Menu' },
        // { parent: 'UI Kit', label: 'Media' },
        // { parent: 'UI Kit', label: 'Message' },
        // { parent: 'UI Kit', label: 'File' },
        // { parent: 'UI Kit', label: 'Chart' },
        // { parent: 'UI Kit', label: 'Misc' },
        // { parent: 'UI Blocks', label: 'Blocks' },
        // { parent: 'Utilities', label: 'Icons' },
        // { parent: 'Pages', label: 'Crud' },
        // { parent: 'Pages', label: 'Calendar' },
        // { parent: 'Pages', label: 'Timeline' },
        // { parent: 'Pages', label: 'Invoice' },
        // { parent: 'Pages', label: 'Login' },
        // { parent: 'Pages', label: 'Help' },
        // { parent: 'Pages', label: 'Empty' },
        // { parent: 'Pages', label: 'Access' },
        // { parent: 'Start', label: 'Documentation' }
    ];

    let rightMenuClick;
    let configClick;
    let menuClick;
    let searchClick = false;
    let topbarItemClick;

    useEffect(() => {
        copyTooltipRef && copyTooltipRef.current && copyTooltipRef.current.updateTargetEvents();
    }, [location]);

    useEffect(() => {
        setResetActiveIndex(true)
        setMenuActive(false)
    }, [menuMode])

    const onDocumentClick = () => {
        if (!searchClick && searchActive) {
            onSearchHide();
        }

        if (!topbarItemClick) {
            setTopbarMenuActive(false)
        }

        if (!menuClick) {
            if (isHorizontal() || isSlim()) {
                setMenuActive(false)
                setResetActiveIndex(true)
            }

            if (overlayMenuActive || staticMenuMobileActive) {
                setOverlayMenuActive(false);
                setStaticMenuMobileActive(false)
            }

            hideOverlayMenu();
            unblockBodyScroll();
        }

        if (!rightMenuClick) {
            setRightMenuActive(false)
        }

        if (configActive && !configClick) {
            setConfigActive(false);
        }

        topbarItemClick = false;
        menuClick = false;
        configClick = false;
        rightMenuClick = false;
        searchClick = false;
    }

    const onSearchHide = () => {
        setSearchActive(false);
        searchClick = false;
    }

    const onMenuModeChange = (menuMode) => {
        setMenuMode(menuMode);
        setOverlayMenuActive(false);
    }

    const onRightMenuButtonClick = () => {
        rightMenuClick = true;
        setRightMenuActive(true)
    }

    const onRightMenuClick = () => {
        rightMenuClick = true;
    }

    const onRightMenuActiveChange = (active) => {
        setRightMenuActive(active);
    }

    const onConfigClick = () => {
        configClick = true;
    }

    const onConfigButtonClick = (event) => {
        setConfigActive(prevState => !prevState)
        configClick = true;
        event.preventDefault();
    }

    const onRippleChange = (e) => {
        PrimeReact.ripple = e.value;
        setRipple(e.value);
    }

    const onMenuButtonClick = (event) => {
        menuClick = true;

        if (isOverlay()) {
            setOverlayMenuActive(prevState => !prevState)
        }

        if (isDesktop()) {
            setStaticMenuDesktopInactive(prevState => !prevState)
        } else {
            setStaticMenuMobileActive(prevState => !prevState)
        }

        event.preventDefault();
    }

    const hideOverlayMenu = () => {
        setOverlayMenuActive(false)
        setStaticMenuMobileActive(false)
    }

    const onTopbarItemClick = (event) => {
        topbarItemClick = true;
        setTopbarMenuActive(prevState => !prevState)
        hideOverlayMenu();
        event.preventDefault();
    }

    const onToggleMenu = (event) => {
        menuClick = true;

        if (overlayMenuActive) {
            setOverlayMenuActive(false)
        }

        if (sidebarActive) {
            setSidebarStatic(prevState => !prevState)
        }

        event.preventDefault();
    }

    const onSidebarMouseOver = () => {
        if (menuMode === 'sidebar' && !sidebarStatic) {
            setSidebarActive(isDesktop());
            setTimeout(() => {
                setPinActive(isDesktop())
            }, 200);
        }
    }

    const onSidebarMouseLeave = () => {
        if (menuMode === 'sidebar' && !sidebarStatic) {
            setTimeout(() => {
                setSidebarActive(false);
                setPinActive(false);
            }, 250);
        }
    }

    const onMenuClick = () => {
        menuClick = true;
    }

    const onChangeActiveInlineMenu = (event) => {
        setActiveInlineProfile(prevState => !prevState);
        event.preventDefault();
    }

    const onRootMenuItemClick = () => {
        setMenuActive(prevState => !prevState)
    }

    const onMenuItemClick = (event) => {
        if (!event.item.items) {
            hideOverlayMenu();
            setResetActiveIndex(true);
        }

        if (!event.item.items && (isHorizontal() || isSlim())) {
            setMenuActive(false);
        }
    }

    const isHorizontal = () => {
        return menuMode === 'horizontal';
    }

    const isSlim = () => {
        return menuMode === 'slim';
    }

    const isOverlay = () => {
        return menuMode === 'overlay';
    }

    const isDesktop = () => {
        return window.innerWidth > 991;
    }


    const onInputClick = () => {
        searchClick = true
    }

    const breadcrumbClick = () => {
        searchClick = true;
        setSearchActive(true);
    }

    const unblockBodyScroll = () => {
        if (document.body.classList) {
            document.body.classList.remove('blocked-scroll');
        } else {
            document.body.className = document.body.className.replace(new RegExp('(^|\\b)' +
                'blocked-scroll'.split(' ').join('|') + '(\\b|$)', 'gi'), ' ');
        }
    }

    const layoutClassName = classNames('layout-wrapper', {
        'layout-static': menuMode === 'static',
        'layout-overlay': menuMode === 'overlay',
        'layout-overlay-active': overlayMenuActive,
        'layout-slim': menuMode === 'slim',
        'layout-horizontal': menuMode === 'horizontal',
        'layout-active': menuActive,
        'layout-mobile-active': staticMenuMobileActive,
        'layout-sidebar': menuMode === 'sidebar',
        'layout-sidebar-static': menuMode === 'sidebar' && sidebarStatic,
        'layout-static-inactive': staticMenuDesktopInactive && menuMode === 'static',
        'p-ripple-disabled': !ripple
    });

    return (
        <div className={layoutClassName} onClick={onDocumentClick}>

            <Tooltip ref={copyTooltipRef} target=".block-action-copy" position="bottom" content="Copied to clipboard" event="focus" />

            <div className="layout-main">
                <AppTopbar items={menu} menuMode={menuMode} colorScheme={props.colorScheme} menuActive={menuActive}
                    topbarMenuActive={topbarMenuActive} activeInlineProfile={activeInlineProfile} onTopbarItemClick={onTopbarItemClick} onMenuButtonClick={onMenuButtonClick}
                    onSidebarMouseOver={onSidebarMouseOver} onSidebarMouseLeave={onSidebarMouseLeave} onToggleMenu={onToggleMenu}
                    onChangeActiveInlineMenu={onChangeActiveInlineMenu} onMenuClick={onMenuClick} onMenuItemClick={onMenuItemClick}
                    onRootMenuItemClick={onRootMenuItemClick} resetActiveIndex={resetActiveIndex} />

                <AppMenu model={menu} onRootMenuItemClick={onRootMenuItemClick} onMenuItemClick={onMenuItemClick} onToggleMenu={onToggleMenu} onMenuClick={onMenuClick} menuMode={menuMode}
                    colorScheme={props.colorScheme} menuActive={menuActive}
                    sidebarActive={sidebarActive} sidebarStatic={sidebarStatic} pinActive={pinActive}
                    onSidebarMouseLeave={onSidebarMouseLeave} onSidebarMouseOver={onSidebarMouseOver}
                    activeInlineProfile={activeInlineProfile} onChangeActiveInlineMenu={onChangeActiveInlineMenu} resetActiveIndex={resetActiveIndex} />

                {/* <AppBreadcrumb routes={routes} onMenuButtonClick={onMenuButtonClick} menuMode={menuMode}
                    onRightMenuButtonClick={onRightMenuButtonClick} onInputClick={onInputClick}
                    searchActive={searchActive} breadcrumbClick={breadcrumbClick} /> */}
                <NeedAuthen>
                    <div className="layout-main-content">
                        <Suspense fallback={<div>Loading...</div>}>
                            {/* <Route path="/" exact >
                            <Redirect to="/diff-sum/chartView" />
                        </Route> */}
                            {/* <Route path="/admin/scraper/view" component={ScraperView}></Route> */}
                            <Route

                                render={(props) => {

                                    var hash = window.location.hash;
                                    var match = /.*#\/(\w+)\/(\w+)\/(\w+).*/.exec(hash);
                                    if (match) {
                                        var folder = match[1];
                                        var page = match[2];
                                        var func = match[3];
                                    } else {
                                        window.location.href = '#/admin/scraper/view';
                                    }

                                    var pageIndex = folder + page + func;
                                    var Page = global.App.pages[pageIndex];

                                    if (Page) {
                                        return <Page key={`${pageIndex}`} />
                                    } else {
                                        return <></>
                                    }


                                }} />

                        </Suspense>
                    </div>
                </NeedAuthen>

                <AppFooter colorScheme={props.colorScheme} />

            </div>

            <AppRightMenu rightMenuActive={rightMenuActive} onRightMenuClick={onRightMenuClick} onRightMenuActiveChange={onRightMenuActiveChange} />

            <AppConfig configActive={configActive} onConfigButtonClick={onConfigButtonClick} onConfigClick={onConfigClick} menuMode={menuMode} changeMenuMode={onMenuModeChange}
                colorScheme={props.colorScheme} changeColorScheme={props.onColorSchemeChange} theme={props.theme} changeTheme={props.onMenuThemeChange}
                componentTheme={props.componentTheme} changeComponentTheme={props.onComponentThemeChange}
                ripple={ripple} onRippleChange={onRippleChange} />

            <Ploading ref = {c => global.App.loading = c}></Ploading>

        </div>
    );

}

export default App;

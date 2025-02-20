import React, { Component } from 'react';
import { TabView, TabPanel } from 'primereact/tabview';
import { Calendar } from 'primereact/calendar';
import { Dropdown } from 'primereact/dropdown';
import moment from 'moment'
import ScraperSystem from '../../models/admin/ScraperSystem';
import Scraper from '../../models/admin/Scraper';

import '../../assets/css/cus_css.scss'
import CanvasJSReact from '../../lib/canvasjs.react';
import { ThemeContext } from '../../AppWrapper';

var CanvasJSChart = CanvasJSReact.CanvasJSChart;

class SysView extends Component {
    constructor(props) {
        super(props);

        this.state = {
            dateSel: moment().toDate(),
            activeIndex: 0,
            name: [
                { name: 'cmc', code: 'cmc' },
                { name: 'lv3', code: 'lv3' },
            ],
            nameSel: { name: 'lv3', code: 'lv3' },
            options: {

            },

            chartData: []
        }



    }

    contentFormatter = (e, color) => {
        let tooltip = `<div style="font-size: 14px; color : ${color} ; ">`
        if (e.entries) {
            if (e.entries.length) {
                const time = moment(new Date(e.entries[0].dataPoint.x)).format(
                    'HH:mm:ss'
                )
                const divX =
                    `<div class='time-tooltip' style="padding-right: 5px; display: inline-block; font-weigth: bold">` +
                    time +
                    '</div>'
                tooltip = tooltip.concat(divX)
            }
            for (var i = 0; i < e.entries.length; i++) {
                if (e.entries[i].dataPoint) {
                    if (e.entries[i].dataSeries.visible) {
                        const isPremium =
                            e.entries[i].dataSeries.legendText === 'Premium'
                        if (!e.entries[i].dataSeries.color) {
                            e.entries[i].dataSeries.color = '#4661EE'
                        }
                        let label
                        if (
                            e.entries[i].dataPoint &&
                            typeof e.entries[i].dataPoint.y !== 'undefined'
                        )
                            label = e.entries[i].dataPoint.y + '%'

                        if (e.entries[i].dataPoint.name) {
                            label = e.entries[i].dataPoint.name
                        }


                        let div =
                            '<div style="padding-right: 5px; display: inline-block; color:' +
                            '#3cdd96' +
                            '">' +
                            label +
                            '</div>'
                        tooltip = tooltip.concat(div)
                    }
                }
            }
        }
        return tooltip.concat('</div>')
    }

    changeTabIndex(index) {
        this.setState({
            activeIndex: index
        }, () => this.getData());
    }

    getServername() {
        let ScraperModel = new Scraper()
        ScraperModel.read().then(res => {
            if (res['result']) {
                let optionsServer = []
                res = res['data']
                res.map(item => {
                    optionsServer.push({
                        name: item['scraper_name'],
                        code: item['scraper_name']
                    })

                })

                this.setState({
                    name: optionsServer
                });
            }
        })
    }
    getData() {

        let type;
        if (this.state.activeIndex == 0) {
            type = 'scraper_sys_cpu';
        }
        if (this.state.activeIndex == 1) {
            type = 'scraper_sys_ram'
        }
        if (this.state.activeIndex == 2) {
            type = 'scraper_sys_disk'
        }
        let startDate = moment(this.state.dateSel).subtract(1, 'days').startOf('day').format('X')
        let endDate = moment(this.state.dateSel).endOf('day').format('X')
        let model = new ScraperSystem()

        model.read({
            filter: {
                'scraper_sys_time__gte': Number(startDate),
                'scraper_sys_time__lte': Number(endDate),
                'scraper_sys_name': this.state.nameSel.code

            },
            order_by: 'scraper_sys_time'

        }).then(res => {
            if (res['result']) {
                res = res['data'];
                let result = []

                res.map(item => {
                    result.push({
                        x: moment(item['scraper_sys_time'], 'X').toDate(),
                        y: Number(item[type].toFixed(5))
                    })
                })

                this.setState({
                    chartData: [{
                        color: '#3cdd96',
                        markerSize: 0,
                        type: "line",
                        axisYType: "secondary",
                        dataPoints: result,
                        lineThickness: 1,
                    }]
                    // }
                });

            }
        })
    }

    changeName(e) {
        this.setState({
            nameSel: e.value
        }, () => this.getData());
    }

    renderOptions(backgroundColor, color) {
        return (
            {
                height: 600,
                zoomEnabled: true,
                backgroundColor: backgroundColor,
                toolTip: {
                    content: '{y}',
                    fontSize: 11,
                    fontFamily: 'Roboto,sans-serif',
                    fontWeight: 'bold',
                    animationEnabled: false,
                    backgroundColor: 'transparent',
                    borderThickness: 0,
                    shared: true,
                    contentFormatter: (e) => this.contentFormatter(e, color),
                },
                axisX: {
                    crosshair: {
                        enabled: true,
                        color: color
                    },
                    lineColor: color,
                    labelFontColor: color,
                    labelFontSize: 12,
                    gridThickness: 0.1,
                    gridColor: color,
                    labelFormatter: function (e) {
                        return moment(e.value).format('H:m')
                    }
                },
                axisY2: {
                    crosshair: {
                        enabled: true,
                        color: color
                    },
                    lineColor: color,
                    labelFontColor: color,
                    labelFontSize: 12,
                    gridThickness: 0.1,
                    gridColor: color
                },
                data: []
            }
        )
    }


    componentDidMount() {
        this.getServername();
        this.getData('scraper_sys_cpu')

        this.clearInterval = setInterval(() => this.getData(), 60000)

    }
    componentWillUnmount() {
        if (this.clearInterval) {
            clearInterval(this.clearInterval)
        }
    }
    render() {

        let theme = this.context;
        // console.log(theme)
        let backgroundColor = theme == 'dark' ? '#2a2d3b' : '#f4f7fb'
        let color = theme == 'dark' ? '#63656c' : '#44486D'

        let option = this.renderOptions(backgroundColor, color)
        option = Object.assign({}, option)
        option.data = this.state.chartData

        return (
            <div>
                <div style={{ display: 'flex', justifyContent: 'flex-end' }} >
                    <Dropdown className='mr-2' optionLabel="name" value={this.state.nameSel} options={this.state.name} onChange={(e) => this.changeName(e)} />
                    <Calendar id="icon" value={this.state.dateSel} onChange={(e) => this.setState({ dateSel: e.value }, () => this.getData())} showIcon />
                </div>



                <TabView activeIndex={this.state.activeIndex} onTabChange={(e) => { this.changeTabIndex(e.index) }}>
                    <TabPanel header="CPU">
                        <div className='chart_cus'>
                            <CanvasJSChart options={option} onRef={ref => this.chart = ref} />
                        </div>
                    </TabPanel>
                    <TabPanel header="RAM">
                        <div className='chart_cus'>
                            <CanvasJSChart options={option} />
                        </div>
                    </TabPanel>
                    <TabPanel header="DISK">
                        <div className='chart_cus'>
                            <CanvasJSChart options={option} />
                        </div>
                    </TabPanel>
                </TabView>

            </div>


        );
    }
}

SysView.contextType = ThemeContext;

export default SysView;
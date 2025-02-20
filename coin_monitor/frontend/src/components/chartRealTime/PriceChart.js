import React, { Component } from 'react';
import CanvasJSReact from '../../lib/canvasjs.react';
import moment from 'moment'
import { ThemeContext } from '../../AppWrapper';
var CanvasJSChart = CanvasJSReact.CanvasJSChart;

class PriceChart extends Component {

    componentDidMount() {
        this.getData()
    }

    getData() {

        return {
            'a': this.props.dateSel,
            'b': this.props.symbol
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
                            label = e.entries[i].dataPoint.y

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
    renderOptions(backgroundColor, color) {
        return (
            {
                height: 200,
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
                    // labelFormatter: function (e) {
                    //     return moment(e.value).format('H:m')
                    // }
                },
                axisY2: {
                    title: "Price",
                    titleFontColor: color,
                    titleFontSize: 16,
                    crosshair: {
                        enabled: true,
                        color: color
                    },
                    lineColor: color,
                    labelFontColor: color,
                    labelFontSize: 12,
                    gridThickness: 0.1,
                    gridColor: color,

                },
                data: [
                    {
                        // color: '#3cdd96',
                        markerSize: 0,
                        type: "line",
                        axisYType: "secondary",
                        lineThickness: 1,
                        type: "line",
                        dataPoints: [
                            { x: new Date("2018-3-01"), y: 85.3 },
                            { x: new Date("2018-3-02"), y: 83.97 },
                            { x: new Date("2018-3-05"), y: 83.49 },
                            { x: new Date("2018-3-06"), y: 84.16 },
                            { x: new Date("2018-3-07"), y: 84.86 },
                            { x: new Date("2018-3-08"), y: 84.97 },
                            { x: new Date("2018-3-09"), y: 85.13 },
                            { x: new Date("2018-3-12"), y: 85.71 },
                            { x: new Date("2018-3-13"), y: 84.63 },
                            { x: new Date("2018-3-14"), y: 84.17 },
                        ]
                    }
                ]

                // title:{
                //     text: "My First Chart in CanvasJS"              
                // },
                // data: [              
                // {
                //     // Change type to "doughnut", "line", "splineArea", etc.
                //     type: "column",
                //     dataPoints: [
                //         { label: "apple",  y: 10  },
                //         { label: "orange", y: 15  },
                //         { label: "banana", y: 25  },
                //         { label: "mango",  y: 30  },
                //         { label: "grape",  y: 28  }
                //     ]
                // }
                // ]

            }
        )
    }
    render() {
        let a = this.getData()

        let theme = this.context;
        console.log(theme)
        let backgroundColor = theme == 'dark' ? '#2a2d3b' : '#f4f7fb'
        let color = theme == 'dark' ? '#63656c' : '#44486D'

        let option = this.renderOptions(backgroundColor, color)
        option = Object.assign({}, option)
        // console.log(option)
        // option.data 
        return (
            <>
                <CanvasJSChart options={option} />
            </>
        );
    }
}
PriceChart.contextType = ThemeContext;
export default PriceChart;
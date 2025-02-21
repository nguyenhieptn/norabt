import React, { Component } from 'react';
import Highcharts from 'highcharts';
import HighchartsReact from 'highcharts-react-official'


import Lab from '../../model/admin/Lab'

class ChartLSProfitPerDay extends Component {
    constructor(props) {
        super(props);
        this.state = {
            ALL: true,
            coin: [],
            selected: [],
            temponary: [],
            Options: {
                chart: {}

                ,
                title: {
                    text: '<b>TOTAL LONG SHORT PER DAY</b>',
                },
                xAxis: {

                },
                yAxis: [
                    {
                        title: {
                            text: '<b></b>'
                        }
                    }
                ],

                chart: {
                    height: (8 / 16 * 73) + '%'

                },
                legend: {
                    enabled: false,

                },
                plotOptions: {
                    series: {
                        dataLabels: {
                            enabled: true
                        },
                    },

                },
                tooltip: {
                    style: {
                        fontSize: '9px'
                    },
                    pointFormat: '<div>{series.name} : <b>{point.y}</b></div>'

                },
                series: [{
                    type: 'column',
                    data: [],

                }]
            }
        }
        this.updateChartWidth = this.updateChartWidth.bind(this);

    }
    componentDidMount() {

        if (App.watchlist == undefined) return;
        if (App.lab == undefined) return;
        var coin = [];
        var selected = [];
        Object.values(App.watchlist).map(item => {
            var color = this.getRandomColor();
            coin.push({ name: item.wl_symbol, color: color });
            selected.push(item.wl_symbol);
        })
        this.setState({ coin, selected, temponary: selected }, () => this.getData(true))

        this.updateChartWidth();
        this.resize_ob = new ResizeObserver((entries) => {
            this.updateChartWidth()
        });
        this.resize_ob.observe(this.chartContainer);
    }
    componentWillUnmount() {
        if (this.resize_ob) this.resize_ob.unobserve(this.chartContainer);
    }
    updateChartWidth() {
        if (this.updateWidthTimeout) clearTimeout(this.updateWidthTimeout);
        this.updateWidthTimeout = setTimeout(() => {

            this.setState({
                Options: {
                    ...this.setState.Options,
                    chart: {
                        width: typeof (this.chartContainer) !== null && this.chartContainer.clientWidth,
                    }

                }
            })
        }, 500);
    }
    getRandomColor() {
        var letters = '0123456789ABCDEF';
        var color = '#';
        for (var i = 0; i < 6; i++) {
            color += letters[Math.floor(Math.random() * 16)];
        }
        return color;
    }
    render() {
        return (
            <>
                <div className='p-col-12 p-md-12 cushide' >
                    <div className='box_shadow ' ref={c => this.chartContainer = c} style={{ position: 'relative' }}>
                        <div style={{ display: 'flex', alignItems: 'center', position: 'absolute', top: 5, left: 5, zIndex: 100 }}>
                            <div className='button btn' style={{ border: 'solid thin darkgray', borderRadius: 5, padding: '2px 5px', fontWeight: 'bold', background: (this.state.ALL ? '#28a745' : 'none') }} onClick={() => {
                                if (this.state.ALL) {
                                    this.setState({ ALL: !this.state.ALL, selected: [] },
                                        () => this.getData()
                                    );
                                } else {
                                    this.setState({ ALL: !this.state.ALL, selected: this.state.temponary },
                                        () => this.getData()
                                    );
                                }

                            }}>ALL</div>
                        </div>
                        <HighchartsReact
                            highcharts={Highcharts}
                            options={this.state.Options}
                        />
                        <div style={{ display: 'flex', flexWrap: 'wrap', width: '90%', margin: 'auto', paddingBottom: '10px' }}>
                            {this.state.coin.map(item => {

                                return (
                                    <div key={item.name} style={{ width: '125px', cursor: 'pointer', marginBottom: '5px' }} onClick={() => {
                                        var index = this.state.selected.indexOf(item.name);
                                        if (index > -1) {
                                            var temponary = this.state.selected;
                                            temponary.splice(index, 1);

                                            this.setState({ selected: temponary },
                                                () => this.getData(false)

                                            );
                                        } else {
                                            this.setState({ selected: [...this.state.selected, item.name] },
                                                () => this.getData(false)

                                            );
                                        }

                                    }}>
                                        <div style={{ borderRadius: '50%', backgroundColor: (this.state.selected.indexOf(item.name) > -1 ? item.color : 'rgb(204, 204, 204)'), width: '10px', height: '10px', display: 'inline-block', marginRight: '5px' }}></div>
                                        <span style={{ color: (this.state.selected.indexOf(item.name) > -1 ? 'black' : 'rgb(204, 204, 204)') }}> {item.name.toUpperCase()}</span>
                                    </div>
                                )
                            })}
                        </div>

                    </div>

                </div>
            </>
        );
    }
    async getData(loading) {
        var series = [];
        var seriesParams = [];
        var seriesParamsnhohon = [];



        var categories = [];
        for (var i = 0; i <= 14; i++) {
            var temponary = moment().subtract(i, 'days').format("DD/MM/YYYY");
            categories.unshift(temponary);


            var total = 0;
            var total1 = 0;
            var ls = 0;
            Object.values(App.lab[i]).map(data => {
                var index = this.state.selected.indexOf(data.lab_symbol);
                if (index > -1) {
                    ls++;
                    if (data[LAB_PARAMS] == null) return;
                    if (data[LAB_PARAMS].includes('Profit >=')) {
                        total++;

                    }
                    if (data[LAB_PARAMS].includes('Profit <=')) {
                        total1++;

                    }
                }

            })

            series.unshift(ls);
            seriesParams.unshift(total);
            seriesParamsnhohon.unshift(total1);

        }

        this.setState({
            Options: {
                series: [
                    {
                        name: 'L/S',
                        data: series,
                        color: '#007bff'
                    }, {
                        name: 'Profit >= 0',
                        type: 'column',
                        data: seriesParams,
                        color: '#28a745'
                    },
                    , {
                        name: 'Profit <= 0',
                        type: 'column',
                        data: seriesParamsnhohon,
                        color: 'red'
                    }
                ],
                xAxis: {
                    categories
                }

            }
        })

    }
}

export default ChartLSProfitPerDay;
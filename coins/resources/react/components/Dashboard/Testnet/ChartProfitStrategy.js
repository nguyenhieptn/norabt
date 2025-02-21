import React, { Component } from 'react';
import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official'
import Watchlist from '../../../model/admin/Watchlist';
import Testnet_results from '../../../model/admin/Testnet_results';
import Strategies from '../../../model/admin/Strategies';

class ChartProfitStrategy extends Component {
    constructor(props) {
        super(props);
        this.state = {

            ALL: true,

            Options: {

            
                title: {
                    text: '<b>STRATEGY PROFIT</b>',
                },
                xAxis: {
                    type: 'category',
                   
                    scrollbar: {
                        enabled: true
                    },
                    tickLength: 0
                },

                yAxis: [
                    {
                        title: {
                            text: ''
                        },
                        lineWidth : 1,
                        opposite : true,
                    }
                ],

                chart: {
                    height: 500,
                },
                legend: {
                    enabled: true,

                },
                plotOptions: {
                    series: {
                        dataLabels: {
                            enabled: true,
                            format: "{point.y:.2f}"
                        }
                        
                    },
                    column: {
                        // zones: [{
                        //     value: 0,
                        //     color: 'red'
                        // }, {
                        //     color: '#007bff'
                        // }]
                    },
                    

                },
                tooltip: {
                
                },
                series: []
            }
        }
        this.updateChartWidth = this.updateChartWidth.bind(this);

        this.colors = {};

    }
    componentDidMount() {

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
    getRandomColor(item) {
        if (isset(this.colors[item])) return this.colors[item];
        var letters = '0123456789ABCDEF';
        var color = '#';
        for (var i = 0; i < 6; i++) {
            color += letters[Math.floor(Math.random() * 16)];
        }
        this.colors[item] = color;
        return this.colors[item];
    }

    render() {
        return (
            <>

                <div className='p-col-12 p-md-12 cushide' >

                    <div className='box_shadow ' ref={c => this.chartContainer = c} style={{ position: 'relative' }}>
                        <div style={{ display: 'flex', alignItems: 'center', position: 'absolute', top: 5, left: 5, zIndex: 100 }}>
                            <div className='button btn' style={{  borderRadius: 0, padding: '2px 5px', fontWeight: (this.state.ALL == true ? 'bold' : '100'), background: (this.state.ALL == true ? 'rgb(230, 235, 245)' : '#f7f7f7') }} onClick={() => {
                                var series = this.chart.chart.userOptions.series;
                                if (this.state.ALL) {
                                    for(let i in series){
                                        series[i].visible = false;
                                    }
                                    this.setState({ ALL: !this.state.ALL, Options: {series}});
                                } else {
                                    for(let i in series){
                                        series[i].visible = true;
                                    }
                                    this.setState({ ALL: !this.state.ALL, Options: {series}});
                                }
                                

                            }}>ALL</div>
                        </div>
                        <HighchartsReact
                            ref={c => this.chart = c}
                            highcharts={Highcharts}
                            options={this.state.Options}
                        />

                    </div>

                </div>
            </>
        );
    }

    async getData() {


        var resultModel = new Testnet_results();
        var straModel = new Strategies();

        var strategyNames = await straModel.read([]);
        if (!strategyNames['result']) return;
        strategyNames = strategyNames['data'];
      
        var strategyIndex = {};
        strategyNames.map(item => strategyIndex[item[STRATEGY_ID]] = item);

        // var testnetResult = await resultModel.readAll();
        var testnetResult = await resultModel.getByAccountTestnet();
        if (!testnetResult['result']) return;
        testnetResult = testnetResult['data'];

      


        var limitTime = Number(moment().startOf('day').format('x'));

        var serialObject = {};
        var categories = [moment(limitTime, 'x').format("DD/MM/YYYY")];

        for (let i in strategyNames) {
            serialObject[strategyNames[i][STRATEGY_ID]] = {
                name: strategyNames[i][STRATEGY_NAME],
                data: [0],
                type: 'column',
                color: this.getRandomColor(strategyNames[i][STRATEGY_ID])
            }
        }

   


        for (let i in testnetResult) {

            var straItem = testnetResult[i];

            if (straItem[TESTNET_RESULT_PENDING] == 1 || straItem[TESTNET_RESULT_STATUS] == TESTNET_RESULT_STATUS_CANCLE) continue;

            var strategy = straItem[TESTNET_RESULT_STRATEGY];

            if (!isset(serialObject[strategy])) continue;



            var tempTime = Number(straItem[TESTNET_RESULT_SELL_TIME])

            if (tempTime >= limitTime) {
                var xvalue = moment(limitTime, 'x').format("DD/MM/YYYY");

                if (!isset(serialObject[strategy])) continue;
                serialObject[strategy]['data'][0] += Number(straItem[TESTNET_RESULT_REAL_PROFIT]);

            } else {
                while (tempTime < limitTime) {
                    limitTime -= 86400 * 1000;
                }
                var xvalue = moment(limitTime, 'x').format("DD/MM/YYYY");

                categories.unshift(xvalue);

                for (let id in serialObject) {
                    if (id == strategy) {
                        serialObject[id]['data'].unshift(Number(straItem[TESTNET_RESULT_REAL_PROFIT]));
                    } else {
                        serialObject[id]['data'].unshift(0);
                    }
                }
            }

        }

        this.setState({

            Options: {

                series: Object.values(serialObject),
                xAxis: {
                    categories,
                    max: categories.length - 1,
                    min: categories.length > 5 ? categories.length - 5 : 0
                }

            }
        })
    }



    // for (var i = 0; i <= 14; i++) {
    //     var temponary = moment().subtract(i, 'days').format("DD/MM/YYYY");
    //     categories.unshift(temponary);

    //     var totalProfit = 0;

    //     Object.values(App.lab[i]).map(data => {
    //         var index = this.state.selected.indexOf(data.lab_symbol);
    //         if (index > -1) {
    //             if (data[LAB_PENDING] == 0) {
    //                 totalProfit += Number(data[LAB_PROFIT]) - 0.08;
    //             }
    //         }

    //     })

    //     series.unshift(Number(totalProfit.toFixed(4)));

    // }


}

export default ChartProfitStrategy;
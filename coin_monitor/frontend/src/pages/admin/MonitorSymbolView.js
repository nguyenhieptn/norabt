import React from "react";
import '../../assets/css/cus_css.scss'
import ScraperCoin from '../../models/admin/ScraperCoin';
import moment from 'moment'
import { Column } from 'primereact/column';
import { DataTable } from 'primereact/datatable';
import { Tooltip } from 'primereact/tooltip';
import { Button } from 'primereact/button';
class MonitorSymbolView extends React.Component {

    constructor(props) {
        super(props)
        this.state = {
            cols: [],
            data: [],
            loading: false,
        }

        this.ScraperModel = new ScraperCoin()
    }
    componentDidMount() {
        this.getData()
        this.clearInterval = setInterval(() => this.getData() , 60000)
    }

    componentWillUnmount(){
        if(this.clearInterval){
            clearInterval(this.clearInterval)
        }
    }
    getData() {
        this.setState({ loading: true });
        this.ScraperModel.read().then(res => {
            if (res['result']) {
                res = res.data

                let result = {}
                let cols = []

                res.map((item, index) => {

                    var symbol = item['scraper_coin_symbol']
                    var type = item['scraper_coin_type']
                    var name = item['scraper_coin_name']
                    var time = item['scraper_coin_time']
                    var host = item['scraper_coin_type'] + 'Hosts'
                    var active = item['scraper_coin_type'] + 'Active'
                    var status = item['scraper_coin_status']

                    if(moment().format('x') - time > 3 *60 * 1000){
                        status = 0
                    }


                    if (result[symbol]) {
                        if (result[symbol][type]) {
                            result[symbol][type] += 1
                            result[symbol][host].push({
                                'name': name,
                                'active': status,
                                'time' : time
                            })


                        } else {
                            result[symbol][type] = 1
                            result[symbol][host] = [{
                                'name': name,
                                'active': status,
                                'time' : time
                            }]


                        }

                        if (time > result[symbol][time]) {
                            result[symbol][time] = time
                        }

                    } else {

                        result[symbol] = {
                            'symbol': symbol,
                            'time': time
                        }

                        result[symbol][type] = 1
                        result[symbol][host] = [{
                            'name': name,
                            'active': status,
                            'time' : time
                        }]


                    }

                    if (!cols.includes(type)) {
                        cols.push(type)
                    }

                    if (!cols.includes(host)) {
                        cols.push(host)
                    }


                })

                cols.unshift('symbol')
                cols.push('time')

                this.setState({
                    data: Object.values(result),
                    cols: cols,
                });
            }
            this.setState({
                loading: false
            });

        })

    }
    representativeTemplate = (data, props) => {
        if (props.field == "time") {
            return (
                <span style={{whiteSpace: "nowrap"}}>{moment(data[props.field], 'x').format('DD-MM-YYYY HH:mm:ss')}</span>
            )

        } else if (props.field.includes('Hosts')) {
            let result = data[props.field]
            if (result) {
        
                return<div style={{display:'flex'}}>
                    {result.map((item, index) => {
                        return <Button key={index} label={item['name']} className= {item['active'] == 1 ? 'p-button-text p-button-success' : 'p-button-text p-button-danger '} tooltip={moment(item['time'], 'x').format('DD-MM-YYYY HH:mm:ss')} tooltipOptions={{position: 'top'}} />
                    })}
                </div> 

            }

        }
        else {
            return data[props.field]
        }

    }
    render() {
        return (
            <div className="p-col-12 p-md-12">
                <div className="card widget-table">
                    <DataTable

                        className="p-datatable-customers" value={this.state.data}
                        dataKey="id1111111" rowHover
                        loading={this.state.loading}
                        responsiveLayout="scroll"

                    >

                        {
                            this.state.cols.map(item =>
                                <Column key={item} field={item} header={item} sortable style={{ textAlign: 'center' }} body={(data, props) => this.representativeTemplate(data, props)}   ></Column>
                            )
                        }


                    </DataTable>

                </div>
            </div>

        )
    }
}

export default MonitorSymbolView
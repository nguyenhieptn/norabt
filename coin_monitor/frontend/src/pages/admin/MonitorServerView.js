import React from "react";
import '../../assets/css/cus_css.scss'
import ScraperCoin from '../../models/admin/ScraperCoin';
import moment from 'moment'
import { Column } from 'primereact/column';
import { DataTable } from 'primereact/datatable';
class MonitorServerView extends React.Component {

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


                    if (result[name]) {
                        if (result[name][type]) {
                            result[name][type] += 1
                            result[name][host].push({
                                'symbol': symbol,
                                'active': status
                            })


                        } else {
                            result[name][type] = 1
                            result[name][host] = [{
                                'symbol': symbol,
                                'active': status
                            }]

                        }

                        if (time > result[name][time]) {
                            result[name][time] = time
                        }

                    } else {

                        result[name] = {
                            'name': name,
                            'time': time
                        }

                        result[name][type] = 1
                        result[name][host] = [{
                            'symbol': symbol,
                            'active': status
                        }]



                    }

                    if (!cols.includes(type)) {
                        cols.push(type)
                    }

                    if (!cols.includes(host)) {
                        cols.push(host)
                    }


                })

                cols.unshift('name')
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
                <span>{moment(data[props.field], 'x').format('DD-MM-YYYY HH:mm:ss')}</span>
            )

        } else if (props.field.includes('Hosts')) {
            let result = data[props.field]
            if (result) {
                result.sort((a, b) => a.symbol.localeCompare(b.symbol))
                return result.map((item, index) => {
                    if (index == result.length - 1) {
                        return <span style={item['active'] == 1 ? { color: 'limegreen' } : { color: 'red' }}> {item['symbol']}</span>
                    } else {
                        return <span style={item['active'] == 1 ? { color: 'limegreen' } : { color: 'red' }}> {item['symbol']} ,</span>
                    }

                })

            }

        }
        else {
            return <div style={{ textAlign: 'center' }}>{data[props.field]}</div>
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
                                <Column key={item} field={item} header={item} sortable body={(data, props) => this.representativeTemplate(data, props)}   ></Column>
                            )
                        }


                    </DataTable>

                </div>
            </div>

        )
    }
}

export default MonitorServerView
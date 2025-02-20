import React from 'react';
import Scraper from '../../models/admin/Scraper';
import { Dropdown } from 'primereact/dropdown';
import { Column } from 'primereact/column';
import { DataTable } from 'primereact/datatable';
import axios from 'axios';
import { ProgressBar } from 'primereact/progressbar';
import '../../assets/css/cus_css.scss'
import { InputText } from 'primereact/inputtext';
class ScraperView extends React.Component {

  constructor(props) {
    super(props)
    this.state = {
      data: [],
      loading: false,
      totalRecords: 0,
      skip: 0,
      limit: 25,
      sortField: '',
      sortOrder: -1,
      filters: {
        'scraper_name__icontains': ''
      },
      page: 1,
    }

    this.timeout =  0;
    this.ScraperModel = new Scraper()
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

  onSort(event) {
    console.log(event)
    this.setState({
      sortField: event.sortField,
      sortOrder: event.sortOrder
    }, () => this.getData());
  }
  onFilter(event) {
    console.log(event);
  }

  onPage(event) {
    console.log(event)
    // this.setState({
    //   first: event.first,
    //   rows: event.rows,
    //   page: Number(event.page) + 1

    // }, () => this.getData());

    this.setState({
      skip: event.first,
      // limit:event.rows
    }, () => this.getData());

  }

  getData() {
    this.setState({ loading: true });
    let filters = {...this.state.filters};
  
    Object.keys(filters).map(key => {
      if(filters[key] == ''){
        delete filters[key]
      }
    })
    var filter = {
      filter: filters,
      skip: this.state.skip,
      limit: this.state.limit

    }

    if (this.state.sortField != '') {
      filter['order_by'] = this.state.sortOrder == 1 ? this.state.sortField : `-${this.state.sortField}`
    }
    this.ScraperModel.filter(filter).then(res => {
      if (res['result']) {

        this.setState({
          data: res.data.data,
          totalRecords: res.data['total'],
        });
      }
      this.setState({
        loading: false
      });

    })

  }

  representativeTemplate = (data, props) => {

    if (props.field == "_id") {

      return (
        <span>{props.rowIndex + 1}</span>
      )
    }
    if (props.field == "scraper_ram") {
      var process = data[props.field];
      var total = Math.round((data['scraper_ram_total'] / 1073741824) * 10) / 10;
      var background = 'limegreen';
      if (process > 50) background = 'orange'
      if (process > 80) background = 'red'

      let renderProcess = () => {

        return <span style={{}}>
          {process} % / {total} G
        </span>
      }
      return (
        <ProgressBar value={process} color={background} displayValueTemplate={renderProcess} />
      )
    }
    if (props.field == "scraper_cpu") {
      var process = data[props.field];
      var total = data['scraper_cpu_total'];
      var background = 'limegreen';
      if (process > 50) background = 'orange'
      if (process > 80) background = 'red'

      let renderProcess = () => {
        var result = `${process} % / ${total} Core`
        return result
      }
      return (
        <ProgressBar value={process} color={background} displayValueTemplate={renderProcess} />
      )
    }
    if (props.field == "scraper_disk") {
      var process = (data[props.field]).toFixed(2);
      var total = Math.round((data['scraper_disk_total'] / 1073741824) * 10) / 10;
      var background = 'limegreen';
      if (process > 50) background = 'orange'
      if (process > 80) background = 'red'

      let renderProcess = () => {
        var result = `${process} % / ${total} G`
        return result
      }
      return (
        <ProgressBar value={process} color={background} displayValueTemplate={renderProcess} />
      )
    }
    if (props.field == "scraper_status") {
      let result = data[props.field];
      return (<span style={result == 'CONNECTED' ? { color: 'limegreen' } : { color: 'red' }}>{result}</span>)
    }
  }

  change(e, type, col, filterkey) {
    var filter = this.state.filters;
    if (type == 'text') {
      filter[col] = e.target.value
    }


    clearTimeout(this.timeout)
    this.setState({
      filters : filter
    });

    this.timeout = setTimeout(() => this.getData() , 500)


    


  }

  renderFilterName() {

    return (
      <InputText className="p-column-filter"  placeholder="Search by name" value={this.state.filters.scraper_name__icontains} onChange={(e) => this.change(e, 'text', 'scraper_name__icontains')}  />
    )
  }

  render() {
    return (
      <div className="p-col-12 p-md-12">
        <div className="card widget-table">
          <DataTable

            className="p-datatable-customers" value={this.state.data}
            dataKey="id1111111" rowHover
            rows={this.state.limit}
            first={this.state.skip} totalRecords={this.state.totalRecords}
            paginator rowsPerPageOptions={[25]}
            paginatorTemplate="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
            emptyMessage="No customers found."
            lazy loading={this.state.loading}
            onPage={(event) => this.onPage(event)}
            onSort={(event) => this.onSort(event)}
            sortField={this.state.sortField} sortOrder={this.state.sortOrder}
            onFilter={(event) => this.onFilter(event)} filters={this.state.filters}
            filterDisplay="row"
            responsiveLayout="scroll"
          >

            <Column field="_id" header="No." style={{ textAlign: 'center' }} body={(data, props) => this.representativeTemplate(data, props)}   ></Column>
            <Column field="scraper_name" filter filterElement={(() => { return this.renderFilterName() })()} style={{ textAlign: 'center' }} header="Name" sortable  ></Column>
            <Column field="scraper_cpu" header="CPU" sortable style={{ minWidth: '150px', textAlign: 'center' }} body={(data, props) => this.representativeTemplate(data, props)}></Column>
            <Column field="scraper_ram" header="RAM" sortable style={{ minWidth: '150px', textAlign: 'center' }} body={(data, props) => this.representativeTemplate(data, props)}></Column>
            <Column field="scraper_disk" header="Disk" sortable style={{ minWidth: '150px', textAlign: 'center' }} body={(data, props) => this.representativeTemplate(data, props)}></Column>
            <Column field="scraper_status" header="Socket" sortable style={{ textAlign: 'center' }} body={(data, props) => this.representativeTemplate(data, props)}  ></Column>
            <Column field="scraper_ip" header="IP" sortable style={{ textAlign: 'center' }}    ></Column>
            <Column field="scraper_port" header="Port" sortable style={{ textAlign: 'center' }}  ></Column>
            <Column field="scraper_sid" header="Socket Id" sortable style={{ textAlign: 'center' }}   ></Column>
            <Column field="scraper_note" header="Note"   ></Column>


          


          </DataTable>

        </div>
      </div>
    )
  }
}

export default ScraperView
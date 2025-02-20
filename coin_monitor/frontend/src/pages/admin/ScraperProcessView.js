import React, {Component} from 'react';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { InputText } from 'primereact/inputtext';
import { FilterMatchMode } from 'primereact/api';
import { Button } from 'primereact/button';
import { SplitButton } from 'primereact/splitbutton';
// import '../../assets/css/cus_css.scss'
import moment from 'moment'

import ScraperProcess from '../../models/admin/ScraperProcess';

class ScraperProcessView extends Component {

  constructor(props) {
    super(props)
    this.state = {
      data: [],
      loading: false,
      totalRecords: 0,
      skip: 0,
      limit: 25,
      sortField: 'scraper_process_status',
      sortOrder: -1,
      filters: {
        scraper_process_name: { value: '', matchMode: FilterMatchMode.CONTAINS },
        scraper_process_symbol: { value: '', matchMode: FilterMatchMode.CONTAINS },
        scraper_process_script: { value: '', matchMode: FilterMatchMode.CONTAINS },
      },
      page: 1,
      selectedRows:null
    }
    this.timeout =  0;
    this.ScraperProcessModel = new ScraperProcess()
  }

  componentDidMount() {
    this.getData()
  }

  onSort(event) {
    this.setState({
      sortField: event.sortField,
      sortOrder: event.sortOrder
    }, () => this.getData());
  }
  onFilter(event) {
    let filters = event.filters
    Object.keys(filters).map(key => {
      console.log(filters[key].value)
      document.getElementById(key+'-filter').value = filters[key].value
    })
    this.setState({
      filters:event.filters
    })
  }

  onPage(event) {
    this.setState({
      skip: event.first,
    }, () => this.getData());

  }

  getData() {
    this.setState({ loading: true });
    let filters = {...this.state.filters};
    let requestFilter = {}
    Object.keys(filters).map(key => {
      let data = filters[key]
      if(data.value != '')
        switch(data.matchMode){
          case FilterMatchMode.CONTAINS:
            requestFilter[key+'__icontains'] = data.value
            break
          case FilterMatchMode.STARTS_WITH:
            requestFilter[key+'__istartswith'] = data.value       
            break
          case FilterMatchMode.ENDS_WITH:
            requestFilter[key+'__iendswith'] = data.value       
            break
          case FilterMatchMode.EQUALS:
            requestFilter[key+'__iexact'] = data.value       
            break
        }
    })
    // console.log(requestFilter)
    var filter = {
      filter: requestFilter,
      skip: this.state.skip,
      limit: this.state.limit

    }

    if (this.state.sortField != '') {
      filter['order_by'] = this.state.sortOrder == 1 ? this.state.sortField : `-${this.state.sortField}`
    }
    this.ScraperProcessModel.filter(filter).then(res => {
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
    if (props.field == "scraper_process_symbol") {
      return (
        <span>{data.scraper_process_symbol.join(' ')}</span>
      )
    }
    if (props.field == "scraper_process_ram" || props.field == "scraper_process_cpu") {
      return (
        <span>{data[props.field].toFixed(3)} %</span>
      )
    }
    if (props.field == "scraper_process_start" || props.field == "scraper_process_check_time") {
      return (
        <span>{moment(data[props.field] * 1000 , 'x').format('DD-MM-YYYY HH:mm:ss')}</span>
      )
      // return (
      //   <span>{new Date(data[props.field] * 1000).toLocaleString('vi-VN')}</span>
      // )
    }
    if (props.field == "scraper_process_time") {
      let time = data[props.field]
      let hour = Math.floor(time/60)
      let minute = Math.round(time % 60)
      return (        
        <span>{hour}:{minute}</span>
      )
    }
    if (props.field == "scraper_process_status") {
      let stt = data[props.field] == 1? 'Active' : 'Disable'
      return (
        <span style={stt == 'Active' ? { color: 'limegreen' } : { color: 'red' }}>{stt}</span>
      )
    }
  }

  change(e, type, col, filterkey) {
    var filter = this.state.filters;
    if (type == 'text') {
      filter[col].value = e.target.value
    }

    clearTimeout(this.timeout)
    this.setState({
      filters : filter
    });
    this.timeout = setTimeout(() => this.getData() , 500)
  }

  renderFilterName() {

    return (
      <InputText className="p-column-filter" id='scraper_process_name-filter'  placeholder="Search by name" value={this.state.filters.scraper_process_name.value} onChange={(e) => this.change(e, 'text', 'scraper_process_name')}  />
    )
  }
  renderFilterScript() {

    return (
      <InputText className="p-column-filter" id='scraper_process_script-filter'  placeholder="Search by script" value={this.state.filters.scraper_process_script.value} onChange={(e) => this.change(e, 'text', 'scraper_process_script')}  />
    )
  }
  renderFilterSymbol() {

    return (
      <InputText className="p-column-filter" id='scraper_process_symbol-filter'  placeholder="Search by symbol" value={this.state.filters.scraper_process_symbol.value} onChange={(e) => this.change(e, 'text', 'scraper_process_symbol')}  />
    )
  }
  
  actionBodyTemplate() {
    
    const items = [
      {
        label: 'Kill',
        icon: 'pi pi-stop-circle',
        // command: () => {
          
        // }
      },
      {
        label: 'Start',
        icon: 'pi pi-step-forward',
        // command: () => {
          
        // }
      },
      {
        label: 'Delete',
        icon: 'pi pi-times-circle',
        // command: () => {
          
        // }
      },
    ];
    return (
      <SplitButton icon='pi pi-cog' model={items} className="p-button-secondary"></SplitButton>
    )
  }

  render() {
    let filterMatchModeOptions = [
      {
        value: FilterMatchMode.CONTAINS,
        label: 'Contains'
      },{
        value: FilterMatchMode.EQUALS,
        label: 'Equals'
      },{
        value: FilterMatchMode.STARTS_WITH,
        label: 'Starts with'
      },{
        value: FilterMatchMode.ENDS_WITH,
        label: 'Ends with'
      }
    ]
    const header = (
      <div className="table-header">
          <Button tooltip='Refresh' tooltipOptions={{className: 'green-500', position:'top'}} icon="pi pi-refresh" className='p-button-success mr-2 mb-2'/>
          <Button tooltip='Kill' tooltipOptions={{className: 'red-500', position:'top'}} icon="pi pi-stop-circle" className='p-button-danger mr-2 mb-2'/>
          <Button tooltip='Start' tooltipOptions={{className: 'blue-500', position:'top'}} icon="pi pi-step-forward" className='mr-2 mb-2'/>
          <Button tooltip='Delete' tooltipOptions={{className: 'yellow-500', position:'top'}} icon="pi pi-times-circle" className='p-button-warning mr-2 mb-2'/>
      </div>
    );
    return (
      <div className="p-col-12 p-md-12">
        <div className="card widget-table">
          <DataTable
            value={this.state.data} header={header}
            dataKey="_id" rowHover
            rows={this.state.limit}
            first={this.state.skip} totalRecords={this.state.totalRecords}
            paginator rowsPerPageOptions={[25, 50]}
            paginatorTemplate="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
            emptyMessage="No records found."
            lazy loading={this.state.loading}
            onPage={(event) => this.onPage(event)}
            onSort={(event) => this.onSort(event)}
            sortField={this.state.sortField} sortOrder={this.state.sortOrder}
            onFilter={(event) => this.onFilter(event)} filters={this.state.filters}
            filterDisplay="row"
            responsiveLayout="scroll"
            selection={this.state.selectedRows} onSelectionChange={e => this.setState({ selectedRows: e.value })}
            resizableColumns 
          >
            <Column selectionMode="multiple" headerStyle={{ width: '3em' }}></Column>
            <Column headerStyle={{ width: '4rem', textAlign: 'center' }} bodyStyle={{ textAlign: 'center', overflow: 'visible' }} body={this.actionBodyTemplate} />
            <Column field="_id" header="No." style={{ textAlign: 'center' }} body={(data, props) => this.representativeTemplate(data, props)}   ></Column>
            <Column field="scraper_process_pid" style={{ textAlign: 'center' }} header="PID" sortable  ></Column>
            <Column field="scraper_process_name" header="Name" style={{ maxWidth: '180px', textAlign: 'center' }} filter filterMatchModeOptions={filterMatchModeOptions} filterElement={(() => { return this.renderFilterName() })()} sortable  ></Column>
            <Column field="scraper_process_script" header="Script" style={{ maxWidth: '180px', textAlign: 'center' }}   filter filterMatchModeOptions={filterMatchModeOptions} filterElement={(() => { return this.renderFilterScript() })()} sortable ></Column>
            <Column field="scraper_process_symbol" header="Symbol" style={{ maxWidth: '180px', textAlign: 'center' }} filter filterMatchModeOptions={filterMatchModeOptions} filterElement={(() => { return this.renderFilterSymbol() })()}></Column>
            <Column field="scraper_process_user" header="User" style={{ textAlign: 'center' }} sortable></Column>
            <Column field="scraper_process_ram" header="RAM" style={{ textAlign: 'center' }} sortable body={(data, props) => this.representativeTemplate(data, props)}></Column>
            <Column field="scraper_process_cpu" header="CPU" style={{ textAlign: 'center' }} sortable body={(data, props) => this.representativeTemplate(data, props)} ></Column>
            <Column field="scraper_process_start" header="Create time" style={{ textAlign: 'center' }} body={(data, props) => this.representativeTemplate(data, props)} sortable  ></Column>
            <Column field="scraper_process_time" header="Time" style={{ textAlign: 'center' }} body={(data, props) => this.representativeTemplate(data, props)} sortable></Column>
            <Column field="scraper_process_check_time" header="Check At" style={{ textAlign: 'center' }} body={(data, props) => this.representativeTemplate(data, props)} sortable></Column>
            <Column field="scraper_process_status" header="Status" style={{ textAlign: 'center' }} body={(data, props) => this.representativeTemplate(data, props)} sortable></Column>
          </DataTable>

        </div>
      </div>
    )
  }
}

export default ScraperProcessView
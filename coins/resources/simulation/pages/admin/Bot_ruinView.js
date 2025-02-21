import React, { Component } from 'react'
import Table from '../../components/table/Table'
import MainTable from '../../components/table/MainTable'
import Pagination from '../../components/table/Pagination'
import FuncBar from '../../components/table/FuncBar'

import FuncEditRow from '../../components/table/FuncEditRow'
import FuncAdd from '../../components/table/FuncAdd'
import FuncHideCol from '../../components/table/FuncHideCol'
import FuncDel from '../../components/table/FuncDel'
import FuncClear from '../../components/table/FuncClear'
import FuncRefresh from '../../components/table/FuncRefresh'
import FuncExport from '../../components/table/FuncExport'

import Bot_ruin from '../../model/admin/Bot_ruin'
import StrategyModal from '../../components/admin/Opt_result/StrategyModal'
class Bot_ruinView extends Component {

    constructor(props) {
        super(props);

        this.bot_ruin_struct = {};
        this.bot_ruin_struct[STRUCT_FILTERS] = {}
        this.bot_ruin_struct[STRUCT_COLUMNS] = {

            [BOT_RUIN_ID]: {
                [COL_NAME]: lang(BOT_RUIN_ID),
                [COL_SORT]: true,

            },
            'Action': {
                [COL_NAME]: 'Action',
                [COL_STYLE]: { maxWidth: 500, textAlign: 'center' },
                [COL_DECORATOR_IN]: (col, row, data) => {
                    var rowData = data[row];
                    var is_excel = rowData['file_excel']
                    return (
                        <>
                            <div className='button btn btn-sm btn-primary' style={{ fontSize: 12 }} onClick={e => {

                                this.OnRun(rowData)

                            }}>Start</div>
                            <div className='button btn btn-sm btn-primary' style={{ fontSize: 12 }} onClick={e => {

                                this.OnStop(rowData)

                            }}>Stop</div>

                            <div className={is_excel ? 'button btn btn-sm btn-primary' : 'button btn btn-sm btn-danger disabled'} style={{ fontSize: 12 }} onClick={e => {
                                if (is_excel) {
                                    this.getExcel(rowData)
                                }


                            }}>Excel</div>
                        </>

                    )
                },


            },
            [BOT_RUIN_NAME]: {
                [COL_NAME]: lang(BOT_RUIN_NAME),
                [COL_SORT]: true,

            },
            [BOT_RUIN_CONFIG]: {
                [COL_NAME]: lang(BOT_RUIN_CONFIG),
                [COL_SORT]: false,
                [COL_STYLE]: { textAlign: 'center' },
                [COL_DECORATOR_IN]: data => {
                    try {
                        var data = JSON.parse(data);
                        return <button type="button" className="btn btn-info" onClick={() => {

                            this.StrategyModal.modal();
                            this.StrategyModal.setValue(JSON.stringify(data), 'Result');
                        }}>Info</button>;
                    } catch (error) {
                        console.log(error)
                    }




                }

            },
            [BOT_RUIN_USER]: {
                [COL_NAME]: lang(BOT_RUIN_USER),
                [COL_SORT]: true,

            },



        }
        this.bot_ruin_struct[STRUCT_FILTERS] = {

            [BOT_RUIN_ID]: {
                [FILTER_NAME]: lang(BOT_RUIN_ID),
                [FILTER_TYPE]: 'text',
            },
            [BOT_RUIN_NAME]: {
                [FILTER_NAME]: lang(BOT_RUIN_NAME),
                [FILTER_TYPE]: 'text',
            },

            [BOT_RUIN_USER]: {
                [FILTER_NAME]: lang(BOT_RUIN_USER),
                [FILTER_TYPE]: 'text',
            },


        }

        this.bot_ruin_struct[STRUCT_EDIT] = {

            [BOT_RUIN_NAME]: {
                [EDIT_NAME]: lang(BOT_RUIN_NAME),
                [EDIT_TYPE]: 'text',

            },
            [BOT_RUIN_CONFIG]: {
                [EDIT_NAME]: lang(BOT_RUIN_CONFIG),
                [EDIT_TYPE]: 'ace',

            },


        }

        this.bot_ruin_struct[STRUCT_ROWS] = {
            [ROW_FUNCS]: (rowData) => {
                return <div className='box_flex' style={{ justifyContent: 'center' }}>
                    <FuncEditRow rowData={rowData} />
                </div>
            }
        };
        this.bot_ruin_struct[STRUCT_TABLE] = {
            [DATA_TABLE_ID]: BOT_RUIN_TABLE,
            [DATA_FILTERS]: {},
            [DATA_HIDDEN_COL]: {},
            [DATA_PERMIT_COL]: this.permissionBot_ruinView(),
            [DATA_KEY]: [BOT_RUIN_ID],
            [DATA_SORT]: { [BOT_RUIN_ID]: 'desc' },
            [FLAG_FILTER]: true,
            [FLAG_FILTER_CHANGE]: true,
            [FLAG_MULTI_SORT]: false,
            [FLAG_RESIZABLE]: true,
            [FLAG_SELECT_ROWS]: true,
            [FLAG_SETTING_ROWS]: true,
            [FLAG_EXPAND_ROWS]: false,
            [FLAG_HEAD_ROW]: true,

            model: new Bot_ruin()

        };


    }

    permissionBot_ruinView() {
        return Object.assign(
            ...Object.keys(this.bot_ruin_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
            ...Object.keys(this.bot_ruin_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
        )
    }


    OnRun(row) {
		var lab_opt_scheduleModel = new Bot_ruin();
		lab_opt_scheduleModel.run_ruin({
			'id': row[BOT_RUIN_ID],
		}).then(res => {
			showLog('Run Success', 'success')
		})

	}

	OnStop(row) {
		var lab_opt_scheduleModel = new Bot_ruin();
		lab_opt_scheduleModel.stop_ruin({
			'id': row[BOT_RUIN_ID],
		}).then(res => {
			showLog('Stop Success', 'success')
		})

	}

	getExcel(row) {
		makeQuestion('Do you want get excel').then(res => {
			if (res) {
				var lab_opt_scheduleModel = new Bot_ruin();
				lab_opt_scheduleModel.get_excel({
					'id': row[BOT_RUIN_ID],
				}).then(res => {
					if (res['result']) {
						if (res['message'] == 'excel') {
							const base64Content = res['data'];
							let binaryContent = atob(base64Content);

							let byteArray = new Uint8Array(binaryContent.length);
							for (let i = 0; i < binaryContent.length; i++) {
								byteArray[i] = binaryContent.charCodeAt(i);
							}

							// Create a Blob from the Uint8Array
							let blob = new Blob([byteArray], { type: 'text/csv' });

							// Create a temporary download link
							let downloadLink = document.createElement('a');
							downloadLink.href = window.URL.createObjectURL(blob);
							downloadLink.download = `data_ruin_${row[BOT_RUIN_ID]}.csv`;
							// Append the link to the document and trigger a click, then remove the link
							document.body.appendChild(downloadLink);
							downloadLink.click();
							document.body.removeChild(downloadLink);
						} else {

							showLog('Excel ', 'success')
						}


					} else {
						showLog(res['data'], 'error')
					}
				})
			}
		})


	}

    render() {
        return (
            <div>
                <Table ref={c => this.table = c} table={this.bot_ruin_struct} autoload={true}>
                    <FuncBar
                        left={<FuncHideCol />}
                        right={<><FuncAdd /><FuncDel /><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
                    <MainTable className='table table-bordered table-striped table-resizable'></MainTable>
                    <Pagination></Pagination>

                </Table>
                <StrategyModal ref={c => this.StrategyModal = c}></StrategyModal>

            </div>
        );
    }
}

export default Bot_ruinView
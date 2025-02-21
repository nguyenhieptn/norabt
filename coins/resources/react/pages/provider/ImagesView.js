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

import Images from '../../model/provider/Images'

class ImagesView extends Component {

	constructor(props) {
		super(props);

		this.images_struct = {};
		this.images_struct[STRUCT_FILTERS] = {}
		this.images_struct[STRUCT_COLUMNS] = {

			[IMAGE_NAME]: {
				[COL_NAME]: lang(IMAGE_NAME),
				[COL_SORT]: true,

			},
			[IMAGE_TYPE]: {
				[COL_NAME]: lang(IMAGE_TYPE),
				[COL_SORT]: true,

			},
			[IMAGE_LINK]: {
				[COL_NAME]: lang(IMAGE_LINK),
				[COL_SORT]: false,

			},
			[IMAGE_LINK_TYPE]: {
				[COL_NAME]: lang(IMAGE_LINK_TYPE),
				[COL_SORT]: true,

			},
			[IMAGE_SIZE]: {
				[COL_NAME]: lang(IMAGE_SIZE),
				[COL_SORT]: true,
				[COL_DECORATOR_IN]: data => `${data}MB`

			},
			[IMAGE_PUBLIC]: {
				[COL_NAME]: lang(IMAGE_PUBLIC),
				[COL_SORT]: true,

			},
			[IMAGE_STATUS]: {
				[COL_NAME]: lang(IMAGE_STATUS),
				[COL_SORT]: true,

			},
			[IMAGE_CHECK]: {
				[COL_NAME]: lang(IMAGE_CHECK),
				[COL_SORT]: true,
				[COL_DES]: 'System will check published link automatically. If link died this image will be marked as Fail'
			},
			
			[IMAGE_DOWNLOAD]: {
				[COL_NAME]: lang(IMAGE_DOWNLOAD),
				[COL_SORT]: true,
				[COL_DES]: 'Number of downloaded times from user'
			},

			[IMAGE_DES]: {
				[COL_NAME]: lang(IMAGE_DES),
				[COL_SORT]: false,
			},



		}
		this.images_struct[STRUCT_FILTERS] = {

			[IMAGE_NAME]: {
				[FILTER_NAME]: lang(IMAGE_NAME),
				[FILTER_TYPE]: 'text',
			},
			[IMAGE_TYPE]: {
				[FILTER_NAME]: lang(IMAGE_TYPE),
				[FILTER_TYPE]: 'select',
			},
			[IMAGE_LINK_TYPE]: {
				[FILTER_NAME]: lang(IMAGE_LINK_TYPE),
				[FILTER_TYPE]: 'select',
			},
			[IMAGE_PUBLIC]: {
				[FILTER_NAME]: lang(IMAGE_PUBLIC),
				[FILTER_TYPE]: 'select',
			},
			[IMAGE_STATUS]: {
				[FILTER_NAME]: lang(IMAGE_STATUS),
				[FILTER_TYPE]: 'select',
			},
			[IMAGE_CHECK]: {
				[FILTER_NAME]: lang(IMAGE_CHECK),
				[FILTER_TYPE]: 'select',
			},


		}

		this.images_struct[STRUCT_EDIT] = {

			[IMAGE_NAME]: {
				[EDIT_NAME]: lang(IMAGE_NAME),
				[EDIT_TYPE]: 'text',
				[EDIT_NULL]: false,
				[EDIT_DES]: 'The name of this image. User will search and download on this name. In case images have the same Name, system will auto loadbalancing'

			},
			[IMAGE_TYPE]: {
				[EDIT_NAME]: lang(IMAGE_TYPE),
				[EDIT_TYPE]: 'select',
				[EDIT_NULL]: false,
				[EDIT_DEFAULT]: 'qemu',

			},
			[IMAGE_LINK]: {
				[EDIT_NAME]: lang(IMAGE_LINK),
				[EDIT_TYPE]: 'textarea',
				[EDIT_NULL]: false,
				[EDIT_DES]: 'Published link of this image. You can get this link by upload to third party and share it as Public'

			},
			[IMAGE_LINK_TYPE]: {
				[EDIT_NAME]: lang(IMAGE_LINK_TYPE),
				[EDIT_TYPE]: 'select',
				[EDIT_NULL]: false,
				[EDIT_DEFAULT]: 'google',
				[EDIT_DES]: 'Third party uploader store name'

			},
			[IMAGE_SIZE]: {
				[EDIT_NAME]: lang(IMAGE_SIZE),
				[EDIT_TYPE]: 'Number',
				[EDIT_NULL]: false,
				[EDIT_DES]: 'Size of image after deployed in MB. Please estimate this field'

			},
			[IMAGE_PUBLIC]: {
				[EDIT_NAME]: lang(IMAGE_PUBLIC),
				[EDIT_TYPE]: 'select',
				[EDIT_DEFAULT]: 1,
				[EDIT_DES]: <div><b>Disabled:</b> Does not allow users to download. <b> Published: </b> Allows user to find images with Search command and download <b> Private: </b> Hide images from search commands result, but can still be downloaded</div>
			},

			[IMAGE_DES]: {
				[EDIT_NAME]: lang(IMAGE_DES),
				[EDIT_TYPE]: 'textarea',
				[EDIT_DES]: 'Show to user when they pull this image. Please fill this field to make it more clear with user. eg. default username/password of image.'
			},


		}

		this.images_struct[STRUCT_ROWS] = {
			[ROW_FUNCS]: (rowData) => {
				return <div className='box_flex'>
					<FuncEditRow rowData={rowData} />
				</div>
			}
		};
		this.images_struct[STRUCT_TABLE] = {
			[DATA_TABLE_ID]: IMAGES_TABLE,
			[DATA_FILTERS]: {},
			[DATA_HIDDEN_COL]: {},
			[DATA_PERMIT_COL]: this.permissionImagesView(),
			[DATA_KEY]: [IMAGE_ID],
			[DATA_SORT]: { [IMAGE_ID]: 'desc' },
			[FLAG_FILTER]: true,
			[FLAG_FILTER_CHANGE]: true,
			[FLAG_MULTI_SORT]: false,
			[FLAG_RESIZABLE]: true,
			[FLAG_SELECT_ROWS]: true,
			[FLAG_SETTING_ROWS]: true,
			[FLAG_EXPAND_ROWS]: false,
			[FLAG_HEAD_ROW]: true,

			model: new Images()

		};


	}

	permissionImagesView() {
		return Object.assign(
			...Object.keys(this.images_struct[STRUCT_COLUMNS]).map((k, i) => ({ [k]: 'Read' })),
			...Object.keys(this.images_struct[STRUCT_EDIT]).map((k, i) => ({ [k]: 'Write' })),
		)
	}

	render() {
		return (
			<div>
				<Table ref={c => this.table = c} table={this.images_struct} autoload={true}>
					<FuncBar
						left={<FuncHideCol />}
						right={<><FuncAdd /><FuncDel /><FuncClear /><FuncRefresh /><FuncExport /></>}></FuncBar>
					<MainTable className='table table-bordered table-striped table-resizable'></MainTable>
					<Pagination></Pagination>

				</Table>


			</div>
		);
	}
}

export default ImagesView
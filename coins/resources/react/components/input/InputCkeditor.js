import React, { Component } from 'react'
import { CKEditor } from '@ckeditor/ckeditor5-react';
import ClassicEditor from '@ckeditor/ckeditor5-build-classic';


class InputCkeditor extends Component {

	constructor(props) {
		super(props);

		this.initial();

		this.state = {
			value: get(this.props.value, '')
		}

		
	}

	initial() {
		var { id, value, decoratorOut, decoratorIn, onChange, ...rent } = this.props;
		this.id = get(id, '');
		this.onChange = get(onChange, () => { })
		this.decoratorOut = get(decoratorOut, function (data) { return (data) });
		this.decoratorIn = get(decoratorIn, function (data) { return (data) });
		this.rent = rent;
	}

	setValue(value) {
		if (isset(this.decoratorIn)) value = this.decoratorIn(value);
		if (value == null) value = '';
		this.setState({ value })
		if (this.input) this.input.setData(value);
	}

	getValue() {
		var value = '';
		if (this.input) value = this.input.getData();
		if (isset(this.decoratorOut)) value = this.decoratorOut(value);
		return value;
	}

	revertValue(value) {
		if (isset(this.decoratorOut)) value = this.decoratorOut(value);
		return value;
	}

	getInput() {
		return this;
	}


	render() {
		this.initial();
		return (
			<CKEditor
				editor={ClassicEditor}
				data=""
				config={{
					toolbar: {
						items: [
							'heading',
							'|',
							'bold',
							'italic',
							'link',
							'bulletedList',
							'numberedList',
							'|',
							'imageUpload',
							'blockQuote',
							'insertTable',
							'mediaEmbed',
							'undo',
							'redo'
						]
					},
					language: 'en',
					table: {
						contentToolbar: [
							'tableColumn',
							'tableRow',
							'mergeTableCells'
						]
					},
					image: {
						toolbar: [
							'imageTextAlternative',
							'imageStyle:inline',
							'imageStyle:block',
							'imageStyle:side'
						]
					},
					// extraPlugins: [ 'Base64UploadAdapter' ]
				}}

				onReady={editor => {
					console.log('Editor is ready to use!', editor);
					editor.setData(this.state.value);
					this.input = editor;
					
				}}
				onChange={(event, editor) => {
					const data = editor.getData();
					this.onChange(editor, data);
				}}
				{...this.rent}
			/>

		)
	}

	componentDidMount() {
		if (isset(this.props.value)) {
			this.setValue(this.props.value);
		}
	}
}



export default InputCkeditor;
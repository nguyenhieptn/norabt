import React, { Component } from 'react'
import Style from './Style'

class DragSort extends Component {

	constructor(props, context) {
		super(props);
		this.state = {
			dragover: '',
			dragging: ''
		}
		this.id = makeId();



	}


	onDragStart(event) {
		this.setState({ dragging: 'dragging' });
		event.dataTransfer.setData('src_id', this.props.src_id);
		global.src_weight = this.props.src_weight;
	}
	onDragEnd(event) {
		this.setState({ dragging: '' });
	}

	onDrop(event) {
		event.preventDefault();
		var src_id = event.dataTransfer.getData("src_id");
		if (this.props.changeOrder && src_id != this.props.src_id) {
			this.props.changeOrder(src_id, this.props.src_id);
		}
		this.setState({ dragover: '' });
		delete (global.src_weight);
	}

	onDragEnter(event) {

		event.preventDefault();
		var src_weight = global.src_weight;
		if (Number(src_weight) > Number(this.props.src_weight)) {
			this.setState({ dragover: 'dragover down' });
		} else if (Number(src_weight) < Number(this.props.src_weight)) {
			this.setState({ dragover: 'dragover up' });
		}

	}

	onDragLeave(event) {
		event.preventDefault();
		this.setState({ dragover: '' });
	}

	render() {

		const {className, changeOrder, src_id, src_weight, icon, children, ...rent} = this.props;
		return (
			<>
				<Style id='drag_sort_css'>{`
					  .dragsort_item.dragover.up::after{
							content:'';
							width: 100%;
							height: 0px;
							border-radius: 5px;
							border: dashed thin orange;
							display: block;
				  	  }
					  .dragsort_item.dragover.down::before{
							content:'';
							width: 100%;
							height: 0px;
							border-radius: 5px;
							border: dashed thin orange;
							display: block;
							
				  	  }
					  .dragsort_item {
						  padding: 5px 0px;
						  position: relative;
						  cursor: move;
					  }
					  .dragsort_item.dragging{
						  border:solid thin orange;
					  }
					  .dragsort_item.dragging * {
					      pointer-events: none;
					  }
					  .dragsort_item.dragover *{
						pointer-events: none;
					  }
					  
				  `}</Style>

				<div draggable={true} className={`dragsort_item ${get(this.props.className, '')} ${this.state.dragover} ${this.state.dragging}`}
					onDragStart={(event) => { this.onDragStart(event) }}
					onDragEnd={(event) => { this.onDragEnd(event) }}
					onDrop={(event) => { this.onDrop(event) }}
					onDragOver={(event) => { event.preventDefault() }}
					onDragEnter={(event) => { console.log('enter'); this.onDragEnter(event) }}
					onDragLeave={(event) => { console.log('leave'); this.onDragLeave(event) }}
					{...rent}
				>
					{this.props.icon ? <i className="fa fa-arrows" style={{ pointerEvents: 'none'}}></i> : ""}
					{this.props.children}

				</div>
			</>
		)
	}
}

export default DragSort

import React, { Component } from 'react'
import FormEditor from './FormEditor' 

class FuncExport extends Component {
	
	constructor(props, context) {
	    super(props, context);
	    this.table = this.context;
	   
	}
	s2ab(s) {
		var buf = new ArrayBuffer(s.length);
		var view = new Uint8Array(buf);
		for (var i=0; i!=s.length; ++i) view[i] = s.charCodeAt(i) & 0xFF;
		return buf;
	}
	
	// excel_export(tableID)
	// {
	//     var tab_text="\uFEFF<table border='2px'>";
	//     var textRange; var j=0;
	//     var tab = document.getElementById(tableID); // id of table
	    
	//     tab_text=tab_text+tab.innerHTML;
	//     tab_text=tab_text+"</table>";
	//     //tab_text= tab_text.replace(/<A[^>]*>|<\/A>/g, "");//remove if u want links in your table
	//     tab_text= tab_text.replace(/<img[^>]*>/gi,""); // remove if u want images in your table
	//     tab_text= tab_text.replace(/<input[^>]*>|<\/input>/gi, ""); // reomves input params
	//     tab_text= tab_text.replace(/<select[^>]*>|<\/select>/gi, ""); // reomves input params
	//     tab_text= tab_text.replace(/<checkbox[^>]*>|<\/checkbox>/gi, ""); // reomves input params
	//     tab_text= tab_text.replace(/>(0[^<]+)</gm, ">&nbsp;$1<"); 
	    
	//     var ua = window.navigator.userAgent;
	//     var msie = ua.indexOf("MSIE "); 

	//     if (msie > 0 || !!navigator.userAgent.match(/Trident.*rv\:11\./))      // If Internet Explorer
	//     {
	//         txtArea1.document.open("txt/html","replace");
	//         txtArea1.document.write(tab_text);
	//         txtArea1.document.close();
	//         txtArea1.focus(); 
	//         var sa=txtArea1.document.execCommand("SaveAs",true,"Say Thanks to Sumit.xls");
	//     }  
	//     else {
	    	   
	//     	    var blob = new Blob([tab_text], {type: 'application/vnd.ms-excel;charset=utf-8;'});
	//     	    var a = document.createElement('a'); 
	//     	    a.download = tableID+'.xls';   
	//     	    a.href = URL.createObjectURL(blob); 
	//     	    a.click();
	    
	//     }
	   
	// }
	excel_export(tableID) {
 
		// Variable to store the final csv data
		var csv_data = [];
	 
		// Get each row data
		var rows = document.getElementById(tableID).getElementsByTagName('tr')
		for (var i = 0; i < rows.length; i++) {
	 
			// Get each column data
			var cols = rows[i].querySelectorAll('td,th');
	 
			// Stores each csv row data
			var csvrow = [];
			for (var j = 0; j < cols.length; j++) {
	 
				// Get the text data of each cell of
				// a row and push it to csvrow
				csvrow.push('"'+cols[j].innerText + '"');
			}
	 
			// Combine each column value with comma
			csv_data.push(csvrow.join(","));
		}
		// combine each row data with new line character
		csv_data = csv_data.join('\n');

		var blob = new Blob([csv_data], {type: 'text/csv'});
		var a = document.createElement('a'); 
		a.download = tableID+'.csv';   
		a.href = URL.createObjectURL(blob); 
		a.click();
	 
		/* We will use this function later to download
		the data in a csv file downloadCSVFile(csv_data);
		*/
	}
	
	render () {
		  return(
			<div className="table_function">
				<div className="button function_button" onClick={()=>{this.excel_export(this.table[STRUCT_TABLE][DATA_TABLE_ID])}}> 
				    <span><i className="fa fa-save"></i></span>
				    <span>&nbsp;{lang('Export')}</span>
				</div>
			</div>
		)  
	}
}

FuncExport.contextType = TableContext;
export default FuncExport
	  
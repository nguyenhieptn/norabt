global.error_handle = (response, callback=null)=>{
	try {
		console.log(response);
		if(response['result']) return;
		if(typeof(callback)=='function'){
			var conti = callback(response);
			if(conti === false) return;
		}
		if(response['message'] == 'ERROR_AUTHEN'){
			window.location = `${APP_AUTHEN}/login?link=${encodeURIComponent(window.location.href)}&error=${response['data']}` 
			return;
		}
		if(response.response && response.response.status == 419){
			window.location = `${APP_AUTHEN}/login?link=${encodeURIComponent(window.location.href)}&error=${response['data']}` 
			return;
		}
		Swal(lang('Error'), lang(response['message'], response['data']), 'error' );
		
	}catch(err) {
		console.log(err);
		Swal('Lỗi', 'Unknow error. Please contact administrator', 'error');
	}
	 
	 
}

global.showLog = (message, level='error')=>{
	swal('', lang(message), level );
}

global.makeQuestion = (question, confirmButtonText = 'Yes', cancelButtonText='No', level='warning')=>{
    if(typeof Swal == 'undefined') {
        return Promise.resolve(confirm(question));
    }
    return Swal({
        title: '',
        text: question,
        type: level,
        showCancelButton: true,
        confirmButtonColor: '#3085d6',
        cancelButtonColor: '#d33',
        confirmButtonText: confirmButtonText,
        cancelButtonText: cancelButtonText
    }).then((result) => {
        return result.value;
    })
}
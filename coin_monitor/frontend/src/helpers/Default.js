

export const isset = (obj) => {
	if(typeof(obj) == 'undefined' || obj == null ){
		return false;
	}
	return true;
}

export const get = (obj, def) => {
	if(isset(obj)){
		return obj;
	}else{
		return def;
	}
}


export const HtmlEncode = (text)  => {
	  var map = {
	    '&': '&amp;',
	    '<': '&lt;',
	    '>': '&gt;',
	    '"': '&quot;',
	    "'": '&#039;',
    	'“': '&quot;',
    	'”': '&quot;',
	  };

	  return text.replace(/[&<>"']/g, function(m) { return map[m]; });
	}


export const output_secure = (string) => {
	if(!string) return '';
	return string.replace('/<\/?script>?/gmi','');
}

export const str_limit = (string, limit) => {
	if(string.length > (Number(limit)+3)) string = string.substring(0,limit)+'...';
	return string;
}

export const clean_string = (input)  => {
    var output = "";
    for (var i=0; i<input.length; i++) {
    	output += input.charCodeAt(i) <= 127 ? input.charAt(i) : '' 
    }
    return output;
}









export const create_key = (alias)  => {
    var str = alias.trim();
    str = str.toLowerCase();
    str = str.replace(/à|á|ạ|ả|ã|â|ầ|ấ|ậ|ẩ|ẫ|ă|ằ|ắ|ặ|ẳ|ẵ/g,"a"); 
    str = str.replace(/è|é|ẹ|ẻ|ẽ|ê|ề|ế|ệ|ể|ễ/g,"e"); 
    str = str.replace(/ì|í|ị|ỉ|ĩ/g,"i"); 
    str = str.replace(/ò|ó|ọ|ỏ|õ|ô|ồ|ố|ộ|ổ|ỗ|ơ|ờ|ớ|ợ|ở|ỡ/g,"o"); 
    str = str.replace(/ù|ú|ụ|ủ|ũ|ư|ừ|ứ|ự|ử|ữ/g,"u"); 
    str = str.replace(/ỳ|ý|ỵ|ỷ|ỹ/g,"y"); 
    str = str.replace(/đ/g,"d");
    str = str.replace(/!|@|%|\^|\*|\(|\ |\)|\+|\=|\<|\>|\?|\/|,|\.|\:|\;|\'|\"|\&|\#|\[|\]|~|\$|_|`|{|}|\||\\/g,"-");
    str = str.replace(/---|--/g,"-");
    str = str.trim(); 
    return str;
}

export const count = (obj) => {
	return Object.keys(obj).length;
}

export const sleep = (min, max) => {  
    let random =Math.floor(Math.random() * (+max - +min)) + +min;
	return new Promise(resolve => setTimeout(resolve, random));
}


export const clearNumber = (string) => {
	if(!string) return 0;
	return string.toString().replace(/[^\d\-\.]/g,'');
}

export const formatNumber = (num)  => {
	  if(!num) return 0;
	  num = clearNumber(num);
	  return num.toString().replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1,')
}

export const makeId = (max=null, min=null) => {
	if(max === null) max = 1000;
	if(min === null) min = 100;
	return Date.now()+''+Math.floor(Math.random()*max + min);  
}


export const file_public = (path) => {
	if(!path) return '';
	return path.replace(/(https?:\/\/[^\/]+)/, `$1/api/uploader/uploader/public?file=$1`);
} 
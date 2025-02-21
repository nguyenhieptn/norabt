global.basename = (path)=>{
    if (!path) return '';
    return path.replace(/.*\//, '');
}

global.showSize = (size)=>{
    if (size < 1000000) return Math.round(size / 1000) + 'KB';
    return Math.round(size / 10000000) / 10 + 'MB';
}

global.publicFile = (path)=>{
	if(!path) return '';
	return path.replace(/(https?:\/\/[^\/]+)/, `$1/api/uploader/uploader/public?file=$1`);
} 
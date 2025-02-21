global.clearColumn = async (table, column, symbol) => {

    var confirm = await makeQuestion(`Do you want to clean column ${column} of ${table}`);
    if (confirm) {
        var link = `/admin/${table}/clearColumn`
        return axios.request({
            url: link,
            method: 'post',
            data: {
                column,
                symbol
            }
        })
            .then(response => {
                response = response['data'];
                return response;
            })

            .catch((error) => {
                error_handle(error)
            })
    }
    return false;

}

global.objectDiff = ($oldObject, $newObject)=>{
    let diff = {};
    for(let i in $newObject){
        if(typeof($oldObject[i]) == 'undefined'){
            diff[i] = $newObject[i];
        }else{
            if($oldObject[i] == $newObject[i]){
                continue;
            }else{
                diff[i] = $newObject[i];
            }
        }
        
    }
    if(Object.keys(diff).length > 0){
        return diff;
    }
    return null;
}

global.timeInterval = (data)=>{
    data = Math.round(data / 1000);
    var d = Math.floor(data / (3600 * 24));
    var h = Math.floor(data % (3600 * 24) / 3600);
    var m = Math.floor(data % 3600 / 60);

    var dDisplay = d > 0 ? d + 'd ' : "";
    var hDisplay = h > 0 ? h + 'h ' : "";
    var mDisplay = m > 0 ? m + 'm' : 0;
    var color = '';
    if(h > 0 || d >0) color = 'red'
    var date = dDisplay + hDisplay + mDisplay;
    return date
}


global.flowStrategy = (res) => {
    let flowOut = [];
    for (let i in res) {
        var flow = res[i][LAB_RESULT_FLOW]
        var index = flowOut.indexOf(flow);
        if(index < 0){
            
            flowOut.push(flow)
        }

    }
    for (let i in flowOut) {
        flowOut[i] = flowOut[i].split("").reverse().join("");

    }
    flowOut.sort()
    for (let i in flowOut) {
        flowOut[i] = flowOut[i].split("").reverse().join("");

    }
    return flowOut
    // flowOut.sort();


}

global.interval2second = (str)=>{
    const s = 1;
    const m = s * 60;
    const h = m * 60;
    const d = h * 24;
    const w = d * 7;
    const y = d * 365.25;
    if (str.length > 100) {
        throw new Error('Value exceeds the maximum length of 100 characters.');
      }
      const match =
        /^(?<value>-?(?:\d+)?\.?\d+) *(?<type>milliseconds?|msecs?|ms|seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h|days?|d|weeks?|w|years?|yrs?|y)?$/i.exec(
          str,
        );
      
      const groups = match?.groups
      if (!groups) {
        return NaN;
      }
      const n = parseFloat(groups.value);
      const type = (groups.type || 'ms').toLowerCase() ;
      switch (type) {
        case 'years':
        case 'year':
        case 'yrs':
        case 'yr':
        case 'y':
          return n * y;
        case 'weeks':
        case 'week':
        case 'w':
          return n * w;
        case 'days':
        case 'day':
        case 'd':
          return n * d;
        case 'hours':
        case 'hour':
        case 'hrs':
        case 'hr':
        case 'h':
          return n * h;
        case 'minutes':
        case 'minute':
        case 'mins':
        case 'min':
        case 'm':
          return n * m;
        case 'seconds':
        case 'second':
        case 'secs':
        case 'sec':
        case 's':
          return n * s;
        case 'milliseconds':
        case 'millisecond':
        case 'msecs':
        case 'msec':
        case 'ms':
          return n;
        default:
          // This should never occur.
          throw new Error(
            `The unit was matched, but no matching case exists.`,
          );
      }
}

global.copyToClipboard = (text) => {
    const textarea = document.createElement('textarea');
    document.body.appendChild(textarea);
    textarea.value = text;
    textarea.select();
    textarea.setSelectionRange(0, 99999);
    document.execCommand('copy');
    document.body.removeChild(textarea);
  };

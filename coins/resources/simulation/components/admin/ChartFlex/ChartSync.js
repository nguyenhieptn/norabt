

export default class ChartSync {

    constructor() {
		this.charts = {}
    }

    register(id, obj){
        this.charts[id] = obj
    }

    unregister(id){
        delete(this.charts[id])
    }

    updateXaxis(){

    }

    updateHover(oid, xval){
        for(let id in this.charts){
            let obj = this.charts[id]
            if(id == oid){
                obj.hover(null)
            }else{
                obj.hover(xval)
            }
        }

    }

    updateScale(oid, data){

        if (data['xaxis.autorange'] == undefined && data['xaxis.range[0]'] !== undefined) {
            let obj = this.charts[oid]
            let startIndex = Math.floor(data['xaxis.range[0]'])
            let stopIndex = Math.ceil(data['xaxis.range[1]'])
            let xData = obj.plot.data[0]['x']
            var startValue = xData[startIndex]
            var stopValue = xData[stopIndex]
        }
        
        for(let id in this.charts){
            
            if(id == oid) continue
            let obj = this.charts[id]
            let layout = JSON.parse(JSON.stringify(obj.config.layout))

            if(data === null){
                layout.xaxis.autorange = true
                Plotly.relayout(obj.plot, {xaxis: layout.xaxis});
                return;
            }
            
            if (data['xaxis.autorange'] !== undefined) {
                layout.xaxis.autorange = true
                Plotly.relayout(obj.plot, {xaxis: layout.xaxis});
            }
            if (data['xaxis.range[0]'] !== undefined) {
                let xData = obj.plot.data[0]['x']
                let startRange = 0
                let stopRange = xData.length
                for(let i in xData){
                    if(startRange == 0 && xData[i] > startValue){
                        startRange = i == 0 ? 0 : i - 1
                    }
                    if(stopRange == xData.length && xData[i] > stopValue){
                        stopRange = i
                        break
                    }
                }
                let xRange = [startRange, stopRange];
                layout.xaxis.autorange = false
                layout.xaxis.range = xRange
                
                Plotly.relayout(obj.plot, {xaxis:layout.xaxis});
            }
        }
          
    }

}
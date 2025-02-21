import model from "../model";

class Liquidation extends model{
    constructor(){
        super();
        this.links = {
          
            read: {
                link: '/admin/liquidation/read',
                method: 'POST'
            },
           
        }
    }


}

export default Liquidation;
import { result } from "lodash";
import model from "../model";

class Binance_track_balance extends model{
    constructor(){
        super();
        this.links = {
            read: {
                link: '/admin/binance_track_balance/read',
                method: 'POST'
            },
        
        }
    }

    
 

   
}

export default Binance_track_balance;
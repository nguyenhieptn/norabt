import { result } from "lodash";
import model from "../model";

class Testnet_track_balance extends model{
    constructor(){
        super();
        this.links = {
            read: {
                link: '/admin/testnet_track_balance/read',
                method: 'POST'
            },
        
        }
    }

    
 

   
}

export default Testnet_track_balance;
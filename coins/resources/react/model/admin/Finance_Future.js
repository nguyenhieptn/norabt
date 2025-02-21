import model from "../model";

class Finance_Future extends model{
    constructor(){
        super();
        this.links = {
         
            read: {
                link: '/admin/finance_Future/read',
                method: 'POST'
            },

            get: {
                link: '/admin/finance_Future/get',
                method: 'POST'
            },
           
         
        }
    }




   

}

export default Finance_Future;
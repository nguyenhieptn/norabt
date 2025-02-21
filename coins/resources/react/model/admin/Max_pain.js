import model from "../model";

class Max_pain extends model{
    constructor(){
        super();
        this.links = {
          
            read: {
                link: '/admin/max_pain/read',
                method: 'POST'
            },
           
        }
    }


}

export default Max_pain;
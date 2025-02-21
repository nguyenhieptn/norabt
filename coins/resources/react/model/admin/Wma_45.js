import model from "../model";

class Wma_45 extends model{
    constructor(){
        super();
        this.links = {
            read: {
                link: '/admin/wma_45/read',
                method: 'POST'
            },

            filter: {
                link: '/admin/wma_45/filter',
                method: 'POST'
            },
        }
    }
}

export default Wma_45;
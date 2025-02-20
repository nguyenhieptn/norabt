<?php
namespace App\Http\Controllers\Admin;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

use App\Helpers\Auth\Role;
use App\Helpers\DB\Edge;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use App\Helpers\Uploader\FileFunc;
use App\Helpers\Token\JWToken;
use App\Http\Controllers\Controller;


class Wma_45Controller  extends Controller  
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

        $this->mainModel = Models::get('Crawler/WMA45');
        $this->tableName = WMA_45_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[WMA45_TIME] = true;

        if(!Role::checkMonitor()) Reply::finish(false, ERROR_PERMISSION, ['data'=>'Please login by other account']); 
        
    }

   

    public function read(Request $request)
    {
        $datas = $request->all();
        $orderBy = get($datas['orderBy'], null);
        $sort = get($datas['sort'], 'asc');
        $limit = get($datas['limit'], null);
        $skip = get($datas['skip'], null);
        $select = get($datas['select'], null);
        $datas = array_diff_key($datas, array_flip(['orderBy', 'sort', 'limit', 'skip', 'select']));
        
        $datas = $this->mainModel->keyToCondition($datas);
        $readResult = $this->mainModel->read([$datas], function($db) use($orderBy, $sort, $limit, $skip){
            if(!is_null($orderBy)) $db->orderBy($orderBy, $sort);
            if(!is_null($limit)) $db->limit($limit);
            if(!is_null($skip)) $db->skip($skip);
        }, false, $select);
        Reply::finish($readResult);
    }


    public function filter(Request $request)
    {
        $datas = $request->all();
        $datas[FLAG_FILTER_LOGIC] = 'and';
        $responseData = $this->mainModel->filter($datas);
        if(!$responseData['result']) Reply::finish($responseData);
        Reply::finish($responseData);
    }


    
   
   
    
}
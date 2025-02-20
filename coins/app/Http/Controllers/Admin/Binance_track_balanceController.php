<?php

namespace App\Http\Controllers\Admin;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

use App\Helpers\Auth\Role;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use App\Helpers\Uploader\FileFunc;
use App\Helpers\Token\JWToken;
use App\Http\Controllers\Controller;


class Binance_track_balanceController extends Controller
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

        $this->mainModel = Models::get('Admin/Binance_track_balance');
        $this->tableName = BINANCE_TRACK_BALANCE_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[BINANCE_TRACK_BL_ID] = true;

        if (!Role::checkRoot()) Reply::finish(false, ERROR_PERMISSION, '');
    }

    public function read(Request $request)
    {

        $datas = $request->all();
        
        $orderBy = get($datas['orderBy'], null);
        $sort = get($datas['sort'], 'asc');
        $limit = get($datas['limit'], null);
        $datas = array_diff_key($datas, array_flip(['orderBy', 'sort', 'limit']));
        
        $datas = $this->mainModel->keyToCondition($datas);
        $readResult = $this->mainModel->read([$datas], function($db) use($orderBy, $sort, $limit){
            if(!is_null($orderBy)) $db->orderBy($orderBy, $sort);
            if(!is_null($limit)) $db->limit($limit);
        });
        Reply::finish($readResult);
    }

  

  

}

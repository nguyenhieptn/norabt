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


class FinanceController extends Controller  
{

    function __construct()
    {
        parent::__construct();

        $this->mainModel = Models::get('Admin/Finance');
        $this->tableName = FINANCE_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[FINANCE_ID] = true;

        if(!Role::checkMonitor()) Reply::finish(false, ERROR_PERMISSION, ['data'=>'Please login by other account']); 
        
    }

    public function read(Request $request)
    {
        $datas = $request->all();
        $datas = $this->mainModel->keyToCondition($datas);
        $readResult = $this->mainModel->read([$datas]);
        Reply::finish($readResult);
    }

    public function getStock()
    {
        $this->symbol = ['NASDAQ', 'DJIA', 'NIKKEI', 'GOLD'];

        $result = [];

        foreach ($this->symbol as $symbol) {

            $lastRow = $this->mainModel->read([[ [FINANCE_NAME, '=', $symbol]]], function ($db){
                $db->orderBy(FINANCE_CLOSE_TIME, 'DESC')->limit(1);
            });
        
            if (!$lastRow['result']) continue;

            if (isset($lastRow['data'][0])) {
                $lastRow = $lastRow['data'][0];
                $result[] = (array)$lastRow;
            }
        }

     

        return Reply::make(true, 'success', $result );
    }


    public function get(Request $request){
        $data = $request->input('data', []);
        $limit = $request->input('limit', null);
        $skip = $request->input('skip', null);
        $orderBy = $request->input('orderBy', null);
        $orderAsc = $request->input('asc', true);


        $result = $this->mainModel->read($data, function($db) use($limit, $skip, $orderBy, $orderAsc){
            if($orderBy !== null) $db->orderBy($orderBy, $orderAsc ? 'ASC' : 'DESC');
            if($skip !== null) $db->skip($skip);
            if($limit !== null) $db->limit($limit);
        }, false);

        return $result;
    }

  
   
    
}
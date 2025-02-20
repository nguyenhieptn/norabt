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
use App\Helpers\Admin\Services;
use Illuminate\Support\Facades\DB;
class Rank_historyController extends Controller  
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

        $this->mainModel = Models::get('Crawler/Rank_history');
        $this->tableName = RANK_HISTORY_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[RANK_HIS_ID] = true;

        if(!Role::checkRoot()) Reply::finish(false, ERROR_PERMISSION, ''); 
        
    }

    

    public function getByRank(Request $request)
    {
        $rank = $request->input('rank', 100);
        $year = $request->input('year', 2021);

        $startTime = mktime(0, 0, 0, 1, 1, $year);
        $stopTime = mktime(0, 0, 0, 1, 1, $year + 1) - 1;

        $executeTime = $startTime;

        $returnData = [];
        
        while($executeTime < $stopTime){

            $timeData = $this->getData($executeTime, $rank);
            $executeTime += 86400;
            if(!$timeData['result']) return $timeData;
            $timeData = $timeData['data'];
            if(count($timeData) == 0) continue;

            if(count($returnData) == 0){
                $returnData = $timeData;
            }else{
                $returnData = array_intersect($returnData, $timeData);
            }
            
        }

        $out = [];
        $Candle1mModel = Models::get('Admin/Lab_candle_1m');
       
        foreach($returnData as $value){
            $value = $value . 'USDT';
            $in = [
                'symbol' => $value,
                'service' => Services::isActive('lab_candle@'.$value. '*')
            ];
            $Candle1mModel->query_builder = DB::connection('coin_future')->table('lab_candle_1m');
            $data = $Candle1mModel->is_exist([[[LAB_CANDLE_1M_SYMBOL , '=' , $value]]]);
            $in['coin_future'] = $data;
            $Candle1mModel->query_builder = DB::connection('coin_spot')->table('lab_candle_1m');
            $data = $Candle1mModel->is_exist([[[LAB_CANDLE_1M_SYMBOL , '=' , $value]]]);
            $in['coin_spot'] = $data;

            $out[] = $in;

        }
    
        return Reply::make(true, 'success', $out);

    }


    private function getData($time, $top){
        $rankData = $this->mainModel->read([[[RANK_HIS_TIME, '=', $time]]], function($db)use($top){
            $db->orderBy(RANK_HIS_VALUE, 'ASC')->limit($top);
        });
        if(!$rankData['result']) return $rankData;
        $rankData = $rankData['data'];
        $returnData = [];
        foreach($rankData as $data){
            $returnData[] = $data->{RANK_HIS_SYMBOL};
        }

        return Reply::make(true, 'success', $returnData);
    }


    //
    
    //
    
   
   
    
}
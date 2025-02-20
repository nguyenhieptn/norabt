<?php
namespace App\Http\Controllers\Admin;

use App\Helpers\Admin\Services;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

use App\Helpers\Auth\Role;
use App\Helpers\DB\Edge;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use App\Helpers\Uploader\FileFunc;
use App\Helpers\Token\JWToken;
use App\Http\Controllers\Controller;


class Testnet_resultsController extends Controller  
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

        $this->mainModel = Models::get('Admin/Testnet_results');
        $this->tableName = TESTNET_RESULTS_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[TESTNET_RESULT_ID] = true;

        if(!Role::checkAdmin()) Reply::finish(false, ERROR_PERMISSION, ['data'=>'Please login by other account']);  
        
    }

    public function add(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas = array_diff_key($datas, $this->dependCols);
        $result = $this->mainModel->add([$datas]);
        if(!$result['result']) Reply::finish($result);
        Reply::finish(true, 'success', $datas);
    }

    public function addGetId(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas = array_diff_key($datas, $this->dependCols);
        $datas[TESTNET_RESULT_ID] = uniqid();
        $result = $this->mainModel->add([$datas]);
        if(!$result['result']) Reply::finish($result);
        Reply::finish(true, 'success', $datas); 
    }

    public function adds(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        foreach ($datas as $key=>$val){
            $datas[$key] = array_diff_key($datas[$key], $this->dependCols);
        }
        Reply::finish($this->mainModel->add($datas)); 
    }

    public function addGetIds(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        foreach ($datas as $key=>$val){
            $datas[$key] = array_diff_key($datas[$key], $this->dependCols);
            $datas[$key][TESTNET_RESULT_ID] = uniqid();
        }
        $result = $this->mainModel->add($datas);
        if(!$result['result']) Reply::finish($result);
        Reply::finish(true, 'success', $datas);
    }

    public function drop(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas =  $this->mainModel->keyToCondition($datas);
        $dropDatas = $this->mainModel->read([$datas]);
        if(!$dropDatas['result']) return $dropDatas;
        $dropDatas = $dropDatas['data'];
        $dropResult = $this->mainModel->drop([$datas]);
        if(!$dropResult['result']) return $dropResult;

        $reloaded = [];
        foreach($dropDatas as $dt){
            $accountId = $dt->{TESTNET_RESULT_ACCOUNT};
            if(!isset($reloaded[$accountId])){
                $reloaded[$accountId] = true;
                Services::restartTestnet($accountId);
            }
            
        }
        Reply::finish($dropResult);
    }

    public function drops(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        foreach ($datas as $key=>$data){
            $datas[$key] =  $this->mainModel->keyToCondition($data);
        }
        $dropDatas = $this->mainModel->read($datas);
        if(!$dropDatas['result']) return $dropDatas;
        $dropDatas = $dropDatas['data'];
        $result = $this->mainModel->drop($datas);
        if(!$result['result']) return $result;

        $reloaded = [];
        foreach($dropDatas as $dt){
            $accountId = $dt->{TESTNET_RESULT_ACCOUNT};
            if(!isset($reloaded[$accountId])){
                $reloaded[$accountId] = true;
                Services::restartTestnet($accountId);
            }
            
        }

        Reply::finish($result);
    }

    public function edit(Request $request)
    {
        $datas = $request->all();
        $datas[DATA_KEY] =  array($this->mainModel->keyToCondition($datas[DATA_KEY]));

        $editDatas = $this->mainModel->read($datas[DATA_KEY]);
        if(!$editDatas['result']) return $editDatas;
        $editDatas = $editDatas['data'];

        $datas[DATA_EDITOR] = array_diff_key($datas[DATA_EDITOR], $this->dependCols);
        $editResult = $this->mainModel->edit($datas);
        if(!$editResult['result']) return $editResult;
        
        $reloaded = [];
        foreach($editDatas as $dt){
            $accountId = $dt->{TESTNET_RESULT_ACCOUNT};
            if(!isset($reloaded[$accountId])){
                $reloaded[$accountId] = true;
                Services::restartTestnet($accountId);
            }
            
        }

        Reply::finish($editResult);
    }

    public function edits(Request $request)
    {
        $datas = $request->all();
        foreach ($datas[DATA_KEY] as $key=>$data){
            $datas[DATA_KEY][$key] =  $this->mainModel->keyToCondition($data);
        }
        $editDatas = $this->mainModel->read($datas[DATA_KEY]);
        if(!$editDatas['result']) return $editDatas;
        $editDatas = $editDatas['data'];

        $datas[DATA_EDITOR] = array_diff_key($datas[DATA_EDITOR], $this->dependCols);
        $editResult = $this->mainModel->edit($datas);

        if(!$editResult['result']) return $editResult;

        $reloaded = [];
        foreach($editDatas as $dt){
            $accountId = $dt->{TESTNET_RESULT_ACCOUNT};
            if(!isset($reloaded[$accountId])){
                $reloaded[$accountId] = true;
                Services::restartTestnet($accountId);
            }
            
        }

        Reply::finish($editResult);
    }

    public function read(Request $request)
    {
        $datas = $request->all();
        $datas = $this->mainModel->keyToCondition($datas);
        $readResult = $this->mainModel->read([$datas]);
        Reply::finish($readResult);
    }

    public function mapping(){
        $mapData = [];
        $mapData[TESTNET_RESULT_SYMBOL] = Edge::mapping(Models::get('Admin/Watchlist'), null, WL_SYMBOL, WL_SYMBOL, null, function ($db) {
            $db->orderBy(WL_SYMBOL, 'DESC');
        });
        $mapData[TESTNET_RESULT_CAMPAIGN] = Edge::mapping(Models::get('Admin/Testnet_campaign'), null, TESTNET_ID, TESTNET_NAME, null, function ($db) {
            $db->orderBy(TESTNET_NAME, 'DESC');
        });
        $mapData[TESTNET_RESULT_STRATEGY] = Edge::mapping(Models::get('Admin/Strategies'), null, STRATEGY_ID, STRATEGY_NAME, null, function ($db) {
            $db->orderBy(STRATEGY_NAME, 'DESC');
        });
        $mapData[TESTNET_RESULT_CONTAINER] = $mapData[TESTNET_RESULT_STRATEGY];
        $mapData[TESTNET_RESULT_FLOW] = Edge::mapping($this->mainModel, null, TESTNET_RESULT_FLOW, TESTNET_RESULT_FLOW, null, function($db){
            $db->distinct();
        });
        $mapData[TESTNET_RESULT_ACCOUNT] = Edge::mapping(Models::get('Admin/Testnet_account'), null, TESTNET_ACCOUNT_ID, TESTNET_ACCOUNT_NAME, null , function($db){

            if(!Role::checkRoot()){
                $db->where(TESTNET_ACCOUNT_USER, '=', Auth::user()->{AUTHEN_ID});
            } 
           
        });

        $mapData[TESTNET_RESULT_TYPE] = (object)[TESTNET_RESULT_TYPE_LONG => 'Long', TESTNET_RESULT_TYPE_SHORT => 'Short'];
        $mapData[TESTNET_RESULT_STATUS] = (object)[
            TESTNET_RESULT_STATUS_PENDING => 'Pending', 
            TESTNET_RESULT_STATUS_MATCHED => 'Matched', 
            TESTNET_RESULT_STATUS_STOPLOSS=>'Stop Loss', 
            TESTNET_RESULT_STATUS_TAKEPROFIT => 'Take Profit', 
            TESTNET_RESULT_STATUS_CANCLE => 'Cancle',
            TESTNET_RESULT_STATUS_PHASE_PENDING => 'Pharse Pending',
            TESTNET_RESULT_STATUS_MATCHED_PART => 'Matched Part',
            TESTNET_RESULT_STATUS_ENTER_WAITTING => 'Waitting',
        ];
        $mapData[TESTNET_RESULT_PENDING] = (object)[0 => 'Finished', 1 => 'Opening'];
        $mapData[TESTNET_RESULT_PHASE] = [0 => 0, 1=> 1, 2=> 2, 3 => 3, 4=>4 , 5=> 5, 6=>6, 7=>7, 8=>8, 9=>9, 10=>10];
        Reply::finish(true, 'Success', $mapData);
    }

    public function suggest(Request $request)
    {
        $datas = $request->input('search', '');
        $suggestData = $this->mainModel->read([[[TESTNET_RESULT_CAMPAIGN, 'contain', $datas]]], function($builder){$builder->limit(20);});
        $suggest = [];
        if($suggestData['result']){
             
            $suggest = $suggestData['data']->mapWithKeys(function ($item){
                return [$item->{TESTNET_RESULT_ID} => $item->{TESTNET_RESULT_CAMPAIGN}];
            });
        }
        Reply::finish(true, '', $suggest);
    }

    public function filter(Request $request)
    {
        $datas = $request->all();
        $datas[FLAG_FILTER_LOGIC] = 'and';
        $isUpdate = get($datas['update'], false);
        $responseData = $this->mainModel->filter($datas);
        if(!$responseData['result']) Reply::finish($responseData);
        Reply::finish($responseData);
    }

    public function updateData(Request $request)
    {
        $responseData = $this->mainModel->read([[[TESTNET_RESULT_PENDING, '=', 1]]], null, false, [
            TESTNET_RESULT_ID,
            TESTNET_RESULT_HIGH,
            TESTNET_RESULT_LOW,
            TESTNET_RESULT_MATCHED_EMA5,
            TESTNET_RESULT_STATUS,
            TESTNET_RESULT_MATCHED_PRICE,
            TESTNET_RESULT_MATCHED_TIME,
            TESTNET_RESULT_PROFIT,
            TESTNET_RESULT_BASEPROFIT,
            TESTNET_RESULT_PHASE,
            TESTNET_RESULT_NEXTPHASE_NOTE,
            TESTNET_RESULT_PHASE_NOTE,
            TESTNET_RESULT_EVENT_PROFIT,
            TESTNET_RESULT_LAST_PRICE,
            TESTNET_RESULT_FIRST_PRICE

        ]);
        if(!$responseData['result']) Reply::finish($responseData);
        Reply::finish($responseData);
    }

    public function get(Request $request){
        $data = $request->input('data', []);
        $limit = $request->input('limit', null);
        $skip = $request->input('skip', null);
        $orderBy = $request->input('orderBy', null);
        $orderAsc = $request->input('asc', true);

        $selectColumn = array_keys($this->mainModel->struct);

        $result = $this->mainModel->read($data, function($db) use($limit, $skip, $orderBy, $orderAsc){
            if($orderBy !== null) $db->orderBy($orderBy, $orderAsc ? 'ASC' : 'DESC');
            if($skip !== null) $db->skip($skip);
            if($limit !== null) $db->limit($limit);
        }, false, [
            TESTNET_RESULT_ID,
            TESTNET_RESULT_ENTER_TIME,
            TESTNET_RESULT_TYPE,
            TESTNET_RESULT_PROFIT,
            TESTNET_RESULT_REAL_PROFIT,
            TESTNET_RESULT_STATUS,
            TESTNET_RESULT_SYMBOL,
            TESTNET_RESULT_PENDING,
            TESTNET_RESULT_PARAMS,
            TESTNET_RESULT_STRATEGY,
            TESTNET_RESULT_SELL_TIME,
            TESTNET_RESULT_COMMIT,
            TESTNET_RESULT_CHART,
            TESTNET_RESULT_FLOW,
            TESTNET_RESULT_PHASE,
            TESTNET_RESULT_REAL_PNL,
            TESTNET_RESULT_ORDER_TIME,
            TESTNET_RESULT_ACCOUNT,
            TESTNET_RESULT_EVENT_PROFIT
        ]);

        return $result;
    }


    public function closePosition(Request $request){
        $id = $request->input('id', null);
        if($id == null) Reply::finish(false, 'No ID');
        $action = $this->mainModel->read([[[TESTNET_RESULT_ID, '=', $id]]]);
        
        if(!$action['result'] || !isset($action['data'][0])) Reply::finish(false, 'Can not find any Action');
        $action = $action['data'][0];
        
        $symbol = $action->{TESTNET_RESULT_SYMBOL};
        $accountId = $action->{TESTNET_RESULT_ACCOUNT};

        if($action->{TESTNET_RESULT_STATUS} == TESTNET_RESULT_STATUS_ENTER_WAITTING){
            $this->mainModel->edit([
                DATA_KEY => [[[TESTNET_RESULT_ID, '=', $id] ]],
                DATA_EDITOR => [
                    TESTNET_RESULT_STATUS => TESTNET_RESULT_STATUS_CANCLE,
                    TESTNET_RESULT_PENDING => 0
                ]
            ]);
        }
        
        if($action->{TESTNET_RESULT_STATUS} ==  TESTNET_RESULT_STATUS_PENDING){
            $this->mainModel->edit([
                DATA_KEY => [[[TESTNET_RESULT_ID, '=', $id] ]],
                DATA_EDITOR => [
                    TESTNET_RESULT_STATUS => TESTNET_RESULT_STATUS_CANCLE,
                    TESTNET_RESULT_PENDING => 0
                ]
            ]);
        }
        
        if($action->{TESTNET_RESULT_MATCHED_QTY} > 0){
            $this->mainModel->edit([
                DATA_KEY => [[[TESTNET_RESULT_ID, '=', $id] ]],
                DATA_EDITOR => [
                    TESTNET_RESULT_STATUS => TESTNET_RESULT_STATUS_STOP_PENDING,
                    TESTNET_RESULT_PENDING => 1
                ]
            ]);
        }
        
        $result = Services::restartTestnet($accountId);

        return Reply::finish(true, 'success', $result);

    }


    //
    
    //
    
   
   
    
}
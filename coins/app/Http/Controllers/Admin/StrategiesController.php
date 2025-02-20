<?php
namespace App\Http\Controllers\Admin;

use App\Helpers\Admin\Services;
use App\Helpers\Admin\Telegram;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

use App\Helpers\Auth\Role;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use App\Helpers\Uploader\FileFunc;
use App\Helpers\Token\JWToken;
use App\Http\Controllers\Controller;
use App\Helpers\DB\Edge;
use Illuminate\Support\Facades\DB;

class StrategiesController extends Controller  
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

        $this->mainModel = Models::get('Admin/Strategies');
        $this->tableName = STRATEGIES_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[STRATEGY_ID] = true;

        if(!Role::checkAdmin()) Reply::finish(false, ERROR_PERMISSION, ['data'=>'Please login by other account']);  
        
    }

    public function add(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas = array_diff_key($datas, $this->dependCols);
        $id = intval($this->mainModel->db()->max(STRATEGY_ID)) + 1;
        $datas[STRATEGY_ID] = $id;
        $datas[STRATEGY_USER] = Auth::user()->{AUTHEN_ID} ;
        $result = $this->mainModel->add([$datas]);
        if(!$result['result']) Reply::finish($result);

        $children = get($variables['children'], null);
        if($children){
            $straConModel = Models::get('Admin/Strategy_container');
            $addData = [];
            foreach($children as $child){
                unset($child[STRA_CON_ID]);
                if($child[STRA_CON_CHILD] == '') continue;
                $child[STRA_CON_CONTAINER] = $id;
                $addData[] = $child;
            }

            $straConModel->add($addData);
        }

        Reply::finish(true, 'success', $datas);
    }

    // public function addGetId(Request $request)
    // {
    //     $variables = $request->all();
    //     $datas = get($variables['data'], []);
    //     $datas = array_diff_key($datas, $this->dependCols);
    //     $datas[STRATEGY_ID] = uniqid();
    //     $result = $this->mainModel->add([$datas]);
    //     if(!$result['result']) Reply::finish($result);
    //     Reply::finish(true, 'success', $datas); 
    // }

    // public function adds(Request $request)
    // {
    //     $variables = $request->all();
    //     $datas = get($variables['data'], []);
    //     foreach ($datas as $key=>$val){
    //         $datas[$key] = array_diff_key($datas[$key], $this->dependCols);
    //     }
    //     Reply::finish($this->mainModel->add($datas)); 
    // }

    // public function addGetIds(Request $request)
    // {
    //     $variables = $request->all();
    //     $datas = get($variables['data'], []);
    //     foreach ($datas as $key=>$val){
    //         $datas[$key] = array_diff_key($datas[$key], $this->dependCols);
    //         $datas[$key][STRATEGY_ID] = uniqid();
    //     }
    //     $result = $this->mainModel->add($datas);
    //     if(!$result['result']) Reply::finish($result);
    //     Reply::finish(true, 'success', $datas);
    // }

    public function drop(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas =  $this->mainModel->keyToCondition($datas);

        $delData = $this->mainModel->read([$datas]);
        if(!$delData['result']) return $delData;
        $straName = [];
        foreach($delData['data'] as $key=>$val){
            $straName[] = $val->{STRATEGY_NAME};
        }

        Telegram::send(TELE_ICON_WARNING . "Strategy [".implode(', ', $straName)."] deleted by " . Auth::user()->{AUTHEN_USERNAME}, TELE_REAL_ERROR);

        $dropResult = $this->mainModel->drop([$datas]);
        Reply::finish($dropResult);
    }

    public function drops(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        foreach ($datas as $key=>$data){
            $datas[$key] =  $this->mainModel->keyToCondition($data);
        }

        $delData = $this->mainModel->read($datas);
        if(!$delData['result']) return $delData;
        $straName = [];
        foreach($delData['data'] as $key=>$val){
            $straName[] = $val->{STRATEGY_NAME};
        }

        Telegram::send(TELE_ICON_WARNING . "Strategy [".implode(', ', $straName)."] deleted by " . Auth::user()->{AUTHEN_USERNAME}, TELE_REAL_ERROR);

        $result = $this->mainModel->drop($datas);
        Reply::finish($result);
    }

    public function edit(Request $request)
    {
        $datas = $request->all();
        $datakey = $datas[DATA_KEY];
        $datas[DATA_KEY] =  array($this->mainModel->keyToCondition($datas[DATA_KEY]));
        $datas[DATA_EDITOR] = array_diff_key($datas[DATA_EDITOR], $this->dependCols);

        $editData = $this->mainModel->read($datas[DATA_KEY]);
        if(!$editData['result']) return $editData;
        $straName = [];
        foreach($editData['data'] as $key=>$val){
            $straName[] = $val->{STRATEGY_NAME};
        }

        Telegram::send(TELE_ICON_WARNING . "Strategy [".implode(', ', $straName)."] edited by " . Auth::user()->{AUTHEN_USERNAME}, TELE_REAL_ERROR);

        $editResult = $this->mainModel->edit($datas);

        if(!$editData['result']) return $editData;

        $id = $datakey[STRATEGY_ID];

        $children = get($datas['children'], null);
        if($children){
           
            $straConModel = Models::get('Admin/Strategy_container');
            $addData = [];
            foreach($children as $child){
                unset($child[STRA_CON_ID]);
                if($child[STRA_CON_CHILD] == '') continue;
                $child[STRA_CON_CONTAINER] = $id;
                $addData[] = $child;
            }
            $straConModel->drop([[[STRA_CON_CONTAINER, '=', $id]]]);
            $straConModel->add($addData);
        }

        if(isset($datas['apply']) && $datas['apply'] == 1){
            $this->restartStrategy($id);
        }

        Reply::finish($editResult);
    }

    private function restartStrategy($id){
        $tradeModel = Models::get('Admin/Trades');
            $trades = $tradeModel->read([[[TRADE_STRATEGY, '=', $id]]]);
            
            if(!$trades['result']) return $trades;

            foreach($trades['data'] as $trade){
                if(Services::isActive('binance_event@'.$trade->{TRADE_SYMBOL}.'_'.$trade->{TRADE_ACCOUNT})){
                    $result = exec('sudo systemctl restart binance_event@'.$trade->{TRADE_SYMBOL}.'_'.$trade->{TRADE_ACCOUNT});
                    $tradeModel->edit([
                        DATA_KEY => [[[TRADE_ACCOUNT, '=', $trade->{TRADE_ACCOUNT}],[TRADE_SYMBOL, '=', $trade->{TRADE_SYMBOL}] ]],
                        DATA_EDITOR => [TRADE_START_TIME => time(), TRADE_STOP_TIME => null],
                    ]);

                }
            }

            $testnetModel = Models::get('Admin/Testnet_campaign');
            $testnets = $testnetModel->read([[[TESTNET_STRATEGY, '=', $id ]]]);
            if(!$testnets['result']) return $testnets;

            $accounts = [];
            foreach($testnets['data'] as $testnet){
                if(!isset($accounts[$testnet->{TESTNET_ACCOUNT}])){
                    $accounts[$testnet->{TESTNET_ACCOUNT}] = true;
                }
                // if(Services::isActive('testnet_start@'.$testnet->{TESTNET_ID})){
                //     $campaign = $testnet->{TESTNET_ID};
                //     $result = exec('sudo systemctl restart testnet_start@'.$campaign);
                //     $testnetModel->edit([
                //         DATA_KEY => [[[TESTNET_ID, '=', $campaign]]],
                //         DATA_EDITOR => [TESTNET_START_TIME => time(), TESTNET_STOP_TIME => null],
                //     ]);
                // }
            }

            foreach($accounts as $accountId => $val){
                if(Services::isActive('testnet_account@'.$accountId)){
                    $result = exec('sudo systemctl restart testnet_account@'.$accountId);
                }
            }

            $parents = Models::get('Admin/Strategy_container')->read([[[STRA_CON_CHILD, '=', $id]]]);
            if(!$parents['result']) return $parents;
            $parents = $parents['data'];
            foreach($parents as $parent){
                $this->restartStrategy($parent->{STRA_CON_CONTAINER});
            }
    }

    public function edits(Request $request)
    {
        $datas = $request->all();
        foreach ($datas[DATA_KEY] as $key=>$data){
            $datas[DATA_KEY][$key] =  $this->mainModel->keyToCondition($data);
        }
        $datas[DATA_EDITOR] = array_diff_key($datas[DATA_EDITOR], $this->dependCols);

        $editData = $this->mainModel->read($datas[DATA_KEY]);
        if(!$editData['result']) return $editData;
        $straName = [];
        foreach($editData['data'] as $key=>$val){
            $straName[] = $val->{STRATEGY_NAME};
        }

        Telegram::send(TELE_ICON_WARNING . "Strategy [".implode(', ', $straName)."] edited by " . Auth::user()->{AUTHEN_USERNAME}, TELE_REAL_ERROR);

        $editResult = $this->mainModel->edit($datas);

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
        $mapData[STRATEGY_BASEPROFIT_BASEON] = ['close' => 'Close Price', 'ema5_1m' => 'EMA5 1M', 'ema5_3m' => 'EMA5 3M', 'ema5_15m' => 'EMA5 15M'];
        $mapData[STRATEGY_USER] = Edge::mapping(Models::get('Auth/Authentication'), null, AUTHEN_ID, AUTHEN_USERNAME , null , function($db){

            if(!Role::checkRoot()){
                $db->where(AUTHEN_ID, '=', Auth::user()->{AUTHEN_ID});
            } 
           
        });
        $mapData[STRATEGY_CONTENT] = $this->getStrategyOptions();
        Reply::finish(true, 'Success', $mapData);
    }

    public function suggest(Request $request)
    {
        $datas = $request->input('search', '');
        $suggestData = $this->mainModel->read([[[STRATEGY_NAME, 'contain', $datas]]], function($builder){$builder->limit(20);});
        $suggest = [];
        if($suggestData['result']){
             
            $suggest = $suggestData['data']->mapWithKeys(function ($item){
                return [$item->{STRATEGY_ID} => $item->{STRATEGY_NAME}];
            });
        }
        Reply::finish(true, '', $suggest);
    }

    public function filter(Request $request)
    {
        $datas = $request->all();
        $datas[FLAG_FILTER_LOGIC] = 'and';
        $responseData = $this->mainModel->filter($datas, function($db){

            if(!Role::checkRoot()){
                $db->where(STRATEGY_USER, '=', Auth::user()->{AUTHEN_ID});
            } 
           
        });
        if(!$responseData['result']) Reply::finish($responseData);
        Reply::finish($responseData);
    }

    public function count(){
        return $this->mainModel->count();
    }

    private function getStrategyOptions(){
        try {
            $database = 'realtime_data';
            $this->btModel = DB::connection($database);
            $returnData = [];
            foreach ($this->btModel->getMongoDB()->listCollections() as $coll){
                $source = $coll->getName();
                $lastRows = $this->btModel->collection($source)->orderBy('_id', 'DESC')->limit(1)->get();
                $fields = [];
                if($lastRows->count() > 0){
                    $lastRows = $lastRows[0];
                    unset($lastRows['_id']);
                    unset($lastRows['symbol']);
                    // $returnData += array_keys($lastRows);
                    foreach($lastRows as $key => $val){
                        $returnData[] = ['value' => $key, 'meta' => $source];
                    }
                }
            }

            $col = ['timelife','interval','takeprofit','stoploss','step_profit','back_profit','baseprofit','baseprofit_baseon','margin','allow_negative_price_rate',
                    'after_stoploss','enter_step','enter_package','baseprofit','stoploss','margin','enter_price'];
            foreach($col as $coll){
                $returnData[] = ['value' => $coll, 'meta' => 'param'];
            }
            return $returnData;
            
        } catch (\Exception $th) {
            return Reply::make(false, $th->getMessage());
        }
        
    }


    //
    
    //
    
   
   
    
}
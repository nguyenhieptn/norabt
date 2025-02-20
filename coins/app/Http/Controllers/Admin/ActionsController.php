<?php
namespace App\Http\Controllers\Admin;

use App\Event\Real\EventRun;
use App\Event\Real\EventRun_linhvhv;
use App\Helpers\Admin\Binancer;
use App\Helpers\Admin\Services;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

use App\Helpers\Auth\Role;
use App\Helpers\DB\Edge;
use App\Helpers\DB\Models;
use App\Helpers\Request\Checker;
use App\Helpers\Request\Reply;
use App\Helpers\Uploader\FileFunc;
use App\Helpers\Token\JWToken;
use App\Http\Controllers\Controller;


class ActionsController extends Controller  
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

        $this->mainModel = Models::get('Admin/Actions');
        $this->tableName = ACTIONS_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[ACTION_ID] = true;

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
        $datas[ACTION_ID] = uniqid();
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
            $datas[$key][ACTION_ID] = uniqid();
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
        $result = $this->mainModel->drop($datas);
        Reply::finish($result);
    }

    public function edit(Request $request)
    {
        $datas = $request->all();
        $datas[DATA_KEY] =  array($this->mainModel->keyToCondition($datas[DATA_KEY]));
        $datas[DATA_EDITOR] = array_diff_key($datas[DATA_EDITOR], $this->dependCols);
        $editResult = $this->mainModel->edit($datas);
        Reply::finish($editResult);
    }

    public function edits(Request $request)
    {
        $datas = $request->all();
        foreach ($datas[DATA_KEY] as $key=>$data){
            $datas[DATA_KEY][$key] =  $this->mainModel->keyToCondition($data);
        }
        $datas[DATA_EDITOR] = array_diff_key($datas[DATA_EDITOR], $this->dependCols);
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
        $mapData[ACTION_TYPE] = (object)[ACTION_TYPE_LONG => 'Long', ACTION_TYPE_SHORT => 'Short'];
        $mapData[ACTION_STATUS] = (object)[
            ACTION_STATUS_PENDING => 'Pending', 
            ACTION_STATUS_MATCHED => 'Matched', 
            ACTION_STATUS_MATCHED_PART => 'Matched Part', 
            ACTION_STATUS_STOPLOSS=>'Stop Loss', 
            ACTION_STATUS_TAKEPROFIT => 'Take Profit', 
            ACTION_STATUS_CANCLE => 'Cancle',
            ACTION_STATUS_ENTER_WAITTING => 'Waitting',
            ACTION_STATUS_STOP_PENDING => 'Stop Pending',
            ACTION_STATUS_PHASE_PENDING => 'Phase Pending',
            ACTION_STATUS_RELEASE_PENDING => 'Release Pending',
            ACTION_STATUS_RELEASE_WAITTING => 'Release Waitting'
        ];
        $mapData[ACTION_PENDING] = (object)[0 => 'Finished', 1 => 'Opening'];
        $mapData[ACTION_SYMBOL] = Edge::mapping(Models::get('Admin/Watchlist'), null, WL_SYMBOL, WL_SYMBOL, null, function($db){
            $db->orderBy(WL_SYMBOL, 'DESC');
        });
        $mapData[ACTION_ACCOUNT] = Edge::mapping(Models::get('Admin/Accounts'), null, ACCOUNT_ID, ACCOUNT_NAME);
        $mapData['strategy'] = Edge::mapping(Models::get('Admin/Strategies'), null, STRATEGY_ID, STRATEGY_NAME, null, function ($db) {
            $db->orderBy(STRATEGY_NAME, 'DESC');
        });
        $mapData[ACTION_FLOW] = Edge::mapping($this->mainModel, null, ACTION_FLOW, ACTION_FLOW, null, function($db){
            $db->distinct();
        });
        $mapData[ACTION_PHASE] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

        $mapData[ACTION_STRATEGY] = Edge::mapping(Models::get('Admin/Strategies'), null, STRATEGY_ID, STRATEGY_NAME, null, function ($db) {
            $db->orderBy(STRATEGY_NAME, 'DESC');
        });
        $mapData[ACTION_CONTAINER] = $mapData[ACTION_STRATEGY];

        Reply::finish(true, 'Success', $mapData);
    }

    public function suggest(Request $request)
    {
        $datas = $request->input('search', '');
        $suggestData = $this->mainModel->read([[[ACTION_SYMBOL, 'contain', $datas]]], function($builder){$builder->limit(20);});
        $suggest = [];
        if($suggestData['result']){
             
            $suggest = $suggestData['data']->mapWithKeys(function ($item){
                return [$item->{ACTION_ID} => $item->{ACTION_SYMBOL}];
            });
        }
        Reply::finish(true, '', $suggest);
    }

    public function filter(Request $request)
    {
        $datas = $request->all();
        $datas[FLAG_FILTER_LOGIC] = 'and';
        $responseData = $this->mainModel->filter($datas);
        if(!$responseData['result']) Reply::finish($responseData);

        // $trading = Models::get('Admin/Trades')->read([]);
        // if(!$trading['result']) return $trading;
        // $tradingIndex = [];
        // foreach($trading['data'] as $trade){
        //     $tradingIndex[$trade->{TRADE_ACCOUNT}.'_'.$trade->{TRADE_SYMBOL}] = $trade->{TRADE_STRATEGY};
        // }

        // foreach($responseData['data'][DATA_TABLE] as $key => $val){
        //     $responseData['data'][DATA_TABLE][$key]->{'strategy'} = get($tradingIndex[$val->{ACTION_ACCOUNT} . '_' . $val->{ACTION_SYMBOL}], null);
        //     // $responseData['data'][DATA_TABLE][$key]->{'lab_service'} = Services::isActive('check_event@'.$val->{WL_SYMBOL});
        // }

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
            ACTION_ID,
            ACTION_CHART,
            ACTION_TYPE,
            ACTION_PROFIT,
            ACTION_REALPROFIT,
            ACTION_PNL,
            ACTION_COMMIT,
            ACTION_STATUS,
            ACTION_SYMBOL,
            ACTION_PENDING,
            ACTION_STOP_REASON,
            ACTION_STRATEGY,
            ACTION_SELL_TIME,
            ACTION_SELL_PRICE,
            ACTION_PHASE,
            ACTION_MATCHED_QTY, 
            ACTION_MATCHED_PRICE,
            ACTION_TOTALPROFIT,
            ACTION_MARGIN,
            ACTION_LAST_PRICE,
            ACTION_EVENTPROFIT,
            ACTION_FIRST_PRICE
        ]);

        return $result;
    }

    public function updateData(Request $request)
    {
        $responseData = $this->mainModel->read([[[ACTION_PENDING, '=', 1]]], null, false, [
            ACTION_ID,
            ACTION_MATCHED_EMA5,
            ACTION_STATUS,
            ACTION_MATCHED_PRICE,
            ACTION_MATCHED_TIME,
            ACTION_PROFIT,
            ACTION_BASEPROFIT,
            ACTION_PHASE,
            ACTION_MATCHED_QTY,
            ACTION_MARGIN,
            ACTION_PENDING,
            ACTION_NEXTPHASE_NOTE,
            ACTION_PHASE_NOTE,
            ACTION_EVENTPROFIT,
            ACTION_LAST_PRICE,
            ACTION_FIRST_PRICE

        ]);
        if(!$responseData['result']) Reply::finish($responseData);
        Reply::finish($responseData);
    }

    public function closePosition(Request $request){
        $id = $request->input('id', null);
        if($id == null) Reply::finish(false, 'No ID');
        $action = $this->mainModel->read([[[ACTION_ID, '=', $id]]]);
        if(!$action['result'] || !isset($action['data'][0])) Reply::finish(false, 'Can not find any Action');
        $action = $action['data'][0];

        $symbol = $action->{ACTION_SYMBOL};
        $account = $action->{ACTION_ACCOUNT};

        if($action->{ACTION_STATUS} == ACTION_STATUS_ENTER_WAITTING){
            $this->mainModel->edit([
                DATA_KEY => [[[ACTION_ID, '=', $id] ]],
                DATA_EDITOR => [
                    ACTION_STATUS => ACTION_STATUS_CANCLE,
                    ACTION_PENDING => 0
                ]
            ]);
        }
        
        if($action->{ACTION_STATUS} ==  ACTION_STATUS_PENDING){
            $binancer = new Binancer($account);
            $result = $binancer->cancleAllOrder($symbol);
            if(!$result['result']) return $result;
            return $this->mainModel->edit([
                DATA_KEY => [[[ACTION_ID, '=', $id] ]],
                DATA_EDITOR => [
                    ACTION_STATUS => ACTION_STATUS_CANCLE,
                    ACTION_PENDING => 0
                ]
            ]);
        }
        
        if($action->{ACTION_MATCHED_QTY} > 0){
            $binancer = new Binancer($account);
            return $binancer->canclePosition($symbol);
        }

        return Reply::finish(true);

    }


    public function makeOrder(Request $request){
        ob_start();
        if(!Role::checkRoot()) Reply::finish(false, ERROR_PERMISSION, ['data'=>'Please login by other account']); 
        $account = $request->input('account', null);
        $symbol = $request->input('symbol', null);
        $type = $request->input('type', null);
        $flow = $request->input('flow', null);
        if($account == null || $symbol == null || $type == null || $flow == null) return Reply::make(false, 'Please define account, symbol, type and flow');
        if(!Checker::validate($account, 'Number')) return Reply::make(false, "Wrong format");
        if(!Checker::validate($symbol, 'Word')) return Reply::make(false, "Wrong format");

        if(!Services::isActive('binance_update@'.$account)){
            return Reply::make(false, 'Account does not connect to Binance');
        }
        if(!Services::isActive('binance_event@'.$symbol.'_'.$account)){
            return Reply::make(false, 'Account does not trading ' . $symbol);
        }
            
        if ($account == 6 || $account == 5) {
            $binancer = new EventRun_linhvhv($symbol, $account);
        } else {
            $binancer = new EventRun($symbol, $account);
        }

        $result = exec('sudo systemctl restart binance_event@'.$symbol . '_' .$account);

        $result = $binancer->makeAction($type, Auth::user()->{AUTHEN_USERNAME}, $flow);
        ob_end_clean();

        return $result;

    }

    public function gotoNextPhase(Request $request){
        ob_start();
        if(!Role::checkRoot()) Reply::finish(false, ERROR_PERMISSION, ['data'=>'Please login by other account']); 
        $id = $request->input('id', null);
        if($id == null) return Reply::make(false, 'Please define ID');

        $actionData = $this->mainModel->read([[[ACTION_ID, '=', $id]]]);
        if(!$actionData['result']) return $actionData;
        if(!isset($actionData['data'][0])) return Reply::make(false, 'No Action Data');

        $actionData = $actionData['data'][0];
        $account = $actionData->{ACTION_ACCOUNT};
        $symbol = $actionData->{ACTION_SYMBOL};
            
        if ($account == 6 || $account == 5) {
            $binancer = new EventRun_linhvhv($symbol, $account);
        } else {
            $binancer = new EventRun($symbol, $account);
        }

        $result = exec('sudo systemctl restart binance_event@'.$symbol . '_' .$account);
        $result = $binancer->gotoNextPhase(Auth::user()->{AUTHEN_USERNAME});
        ob_end_clean();

        return $result;

    }


    public function getFlows(Request $request){
        $account = $request->input('account', null);
        $type = $request->input('type', null);
        $symbol = $request->input('symbol', null);
        if($account == null || $type == null || $symbol == null) Reply::finish(false, "please define account, type, and symbol");

        $trade = Models::get('Admin/Trades')->read([[[TRADE_ACCOUNT, '=', $account], [TRADE_SYMBOL, '=', $symbol]]]);
        if(!$trade['result']) return $trade;
        if(!isset($trade['data'][0])) Reply::finish(false, 'This account does not trade ' . $symbol);
        $trade = $trade['data'][0];
        $strategy = Models::get('Admin/Strategies')->read([[[STRATEGY_ID, '=', $trade->{TRADE_STRATEGY}]]]);
        if(!$strategy['result']) return $strategy;
        if(!isset($strategy['data'][0])) Reply::finish('Can not find any strategy');
        $strategyContent = $strategy['data'][0]->{STRATEGY_CONTENT};
        $strategyContent = json_decode($strategyContent, true);
        $type = $type == ACTION_TYPE_LONG ? 'LONG' : 'SHORT';
        $flows = [];
        
        foreach($strategyContent as $flow => $flowData){
            if(isset($flowData['type']) && $flowData['type'] == $type){
                $flows[$flow] = $flow;
            }
        }
        Reply::finish(true, 'success', $flows);
    }


    public function syncPosition(Request $request){
        $id = $request->input('id');
        $action = $this->mainModel->read([[[ACTION_ID, '=', $id]]]);
        if(!$action['result']) return $action;
        if(!isset($action['data'][0])) return Reply::make(false, 'Can not find any action');
        $action = $action['data'][0];
        if($action->{ACTION_PENDING} !== 1) return Reply::make(false, 'This action is closed');
        $binancer = new Binancer($action->{ACTION_ACCOUNT});
        return $binancer->syncPosition($action);

    }

    //
    
    //
    
   
   
    
}
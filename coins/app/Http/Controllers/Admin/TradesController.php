<?php
namespace App\Http\Controllers\Admin;

use App\Helpers\Admin\Binancer;
use App\Helpers\Admin\Services;
use App\Helpers\Admin\Telegram;
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


class TradesController extends Controller  
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

        $this->mainModel = Models::get('Admin/Trades');
        $this->tableName = TRADES_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[TRADE_ID] = true;

        if(!Role::checkMonitor()) Reply::finish(false, ERROR_PERMISSION, ['data'=>'Please login by other account']);  
        
    }

    public function add(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas = array_diff_key($datas, $this->dependCols);
        // $datas[TRADE_MONEY] = $datas[TRADE_BUDGET];
        $result = $this->mainModel->add([$datas]);
        if(!$result['result']) Reply::finish($result);
        Reply::finish(true, 'success', $datas);
    }

    public function addGetId(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas = array_diff_key($datas, $this->dependCols);
        $datas[TRADE_ID] = uniqid();
        $result = $this->mainModel->add([$datas]);
        if(!$result['result']) Reply::finish($result);
        Reply::finish(true, 'success', $datas); 
    }

    public function adds(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        foreach ($datas as $key=>$val){
            $datas[$key][TRADE_MONEY] = $datas[$key][TRADE_BUDGET];
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
            $datas[$key][TRADE_ID] = uniqid();
        }
        $result = $this->mainModel->add($datas);
        if(!$result['result']) Reply::finish($result);
        Reply::finish(true, 'success', $datas);
    }

    public function drop(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $serviceName = 'binance_event@'.$datas[TRADE_SYMBOL] . '_' .$datas[TRADE_ACCOUNT];
        if(Services::isActive($serviceName)) Reply::finish(false, "Service is running");
        Telegram::send(TELE_ICON_WARNING . "[".$datas[TRADE_SYMBOL]."-".$datas[TRADE_ACCOUNT]."] Trading is deleted " . Auth::user()->{AUTHEN_USERNAME}, TELE_REAL_ERROR);
        $datas =  $this->mainModel->keyToCondition($datas);
        $dropResult = $this->mainModel->drop([$datas]);
        Reply::finish($dropResult);
    }

    public function drops(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $symbols = [];
        foreach ($datas as $key=>$data){
            $symbols[] = $data[TRADE_SYMBOL] . '_' .$data[TRADE_ACCOUNT];
            $serviceName = 'binance_event@'.$data[TRADE_SYMBOL] . '_' .$data[TRADE_ACCOUNT];
            if(Services::isActive($serviceName)) Reply::finish(false, "Service ".$serviceName." is running");
            $datas[$key] =  $this->mainModel->keyToCondition($data);
        }
        Telegram::send(TELE_ICON_WARNING . "[".implode(', ', $symbols)."] Trading deleted by " . Auth::user()->{AUTHEN_USERNAME}, TELE_REAL_ERROR);
        $result = $this->mainModel->drop($datas);
        Reply::finish($result);
    }

    public function edit(Request $request)
    {
        $datas = $request->all();
        $datakey = $datas[DATA_KEY];
        $datas[DATA_KEY] =  array($this->mainModel->keyToCondition($datas[DATA_KEY]));
        $datas[DATA_EDITOR] = array_diff_key($datas[DATA_EDITOR], $this->dependCols);

        // $datas[DATA_EDITOR][TRADE_MONEY] = $datas[DATA_EDITOR][TRADE_BUDGET];

        if(isset($datas[DATA_EDITOR][TRADE_SYMBOL]) || isset($datas[DATA_EDITOR][TRADE_ACCOUNT])){
            $serviceName = 'binance_event@'.$datakey[TRADE_SYMBOL] . '_' .$datakey[TRADE_ACCOUNT];
            if(Services::isActive($serviceName)) Reply::finish(false, "Service is running");
        }
        
        Telegram::send(TELE_ICON_WARNING . "[".$datakey[TRADE_SYMBOL]."-".$datakey[TRADE_ACCOUNT]."] Trading is edited by " . Auth::user()->{AUTHEN_USERNAME}, TELE_REAL_ERROR);
        
        $editResult = $this->mainModel->edit($datas);
        Reply::finish($editResult);
    }

    public function edits(Request $request)
    {
        $datas = $request->all();
        $symbol = [];
        foreach ($datas[DATA_KEY] as $key=>$data){
            $symbol[] = $data[TRADE_SYMBOL]."-".$data[TRADE_ACCOUNT];

            if(isset($datas[DATA_EDITOR][TRADE_SYMBOL]) || isset($datas[DATA_EDITOR][TRADE_ACCOUNT])){
                $serviceName = 'binance_event@'.$data[TRADE_SYMBOL] . '_' .$data[TRADE_ACCOUNT];
                if(Services::isActive($serviceName)) Reply::finish(false, "Service ".$serviceName." is running");
            }
            
            $datas[DATA_KEY][$key] =  $this->mainModel->keyToCondition($data);
        }
        $datas[DATA_EDITOR] = array_diff_key($datas[DATA_EDITOR], $this->dependCols);
        // if(isset($datas[DATA_EDITOR][TRADE_BUDGET])) $datas[DATA_EDITOR][TRADE_MONEY] = $datas[DATA_EDITOR][TRADE_BUDGET];

        Telegram::send(TELE_ICON_WARNING . "[".implode(', ', $symbol)."] Trading edited by " . Auth::user()->{AUTHEN_USERNAME}, TELE_REAL_ERROR);

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
        $mapData[TRADE_ACCOUNT] = Edge::mapping(Models::get('Admin/Accounts'), null, ACCOUNT_ID, ACCOUNT_NAME);
        $mapData[TRADE_SYMBOL] = Edge::mapping(Models::get('Admin/Watchlist'), null, WL_SYMBOL, WL_SYMBOL);
        $mapData[TRADE_STRATEGY] = Edge::mapping(Models::get('Admin/Strategies'), null, STRATEGY_ID, STRATEGY_NAME);
        $mapData[TRADE_SIDE] = ['BOTH' => 'BOTH', 'LONG' => 'LONG', 'SHORT' => 'SHORT', 'NONE' => 'NONE'];
        $mapData[TRADE_COMPOUND] = ['1'=> 'Enable', '0'=>'Disable'];
        Reply::finish(true, 'Success', $mapData);
    }

    public function suggest(Request $request)
    {
        $datas = $request->input('search', '');
        $suggestData = $this->mainModel->read([[[TRADE_SYMBOL, 'contain', $datas]]], function($builder){$builder->limit(20);});
        $suggest = [];
        if($suggestData['result']){
             
            $suggest = $suggestData['data']->mapWithKeys(function ($item){
                return [$item->{TRADE_ID} => $item->{TRADE_SYMBOL}];
            });
        }
        Reply::finish(true, '', $suggest);
    }

    public function filter(Request $request)
    {
        $datas = $request->all();
        $datas[FLAG_FILTER_LOGIC] = 'and';
        $responseData = $this->mainModel->filter($datas);

        $trading = Models::get('Admin/Actions')->read([[[ACTION_PENDING, '=', 1]]]);
        if(!$trading['result']) return $trading;
        $trading = $trading['data'];
        $tradingIndex = [];
        foreach($trading as $trade){
            $tradingIndex[$trade->{ACTION_SYMBOL} . "_". $trade->{ACTION_ACCOUNT}] = true;
        }

        if(!$responseData['result']) Reply::finish($responseData);
        foreach($responseData['data'][DATA_TABLE] as $key => $val){
            $responseData['data'][DATA_TABLE][$key]->{'trade_service'} = Services::isActive('binance_event@'.$val->{TRADE_SYMBOL}.'_'.$val->{TRADE_ACCOUNT});
            $responseData['data'][DATA_TABLE][$key]->{'update_service'} = Services::isActive('binance_update@'.$val->{TRADE_ACCOUNT});
            $responseData['data'][DATA_TABLE][$key]->{'isTrading'} = isset($tradingIndex[$val->{TRADE_SYMBOL}.'_'.$val->{TRADE_ACCOUNT}]);
        }
        Reply::finish($responseData);
    }

    public function startService(Request $request){
        $id = $request->input('id', '');
        $symbol = $request->input('symbol', '');
        if(!Checker::validate($id, 'Number')) return Reply::make(false, 'Wrong format');
        if(!Checker::validate($symbol, 'Word')) return Reply::make(false, 'Wrong format');
        if($id == '' || $symbol == '') Reply::finish(false, 'No Id or Symbol');
        Telegram::send(TELE_ICON_WARNING . "[".$symbol."-".$id."] Trading is Started/Restarted by " . Auth::user()->{AUTHEN_USERNAME}, TELE_REAL_ERROR);
        $result = exec('sudo systemctl restart binance_event@'.$symbol . '_' .$id);
        $this->mainModel->edit([
            DATA_KEY => [[[TRADE_ACCOUNT, '=', $id],[TRADE_SYMBOL, '=', $symbol] ]],
            DATA_EDITOR => [TRADE_START_TIME => time(), TRADE_STOP_TIME => null],
        ]);
        return Reply::make(true, 'success', $result);

    }

    public function stopService(Request $request){
        ob_start();
        $id = $request->input('id', '');
        $symbol = $request->input('symbol', '');
        if(!Checker::validate($id, 'Number')) return Reply::make(false, 'Wrong format');
        if(!Checker::validate($symbol, 'Word')) return Reply::make(false, 'Wrong format');
        
        if($id == '' || $symbol == '') Reply::finish(false, 'No Id or Symbol');

        Telegram::send(TELE_ICON_WARNING . "[".$symbol."-".$id."] Trading is stopped by " . Auth::user()->{AUTHEN_USERNAME}, TELE_REAL_ERROR);

        $result = exec('sudo systemctl stop binance_event@'.$symbol . '_' .$id);

        // $binancer = new Binancer($id);

        // $result = $binancer->canclePosition($symbol);
        // if(!$result['result']) return $result;

        // sleep(3);

        $this->mainModel->edit([
            DATA_KEY => [[[TRADE_ACCOUNT, '=', $id],[TRADE_SYMBOL, '=', $symbol] ]],
            DATA_EDITOR => [TRADE_STOP_TIME => time()],
        ]);
        
        Models::get('Admin/Actions')->edit([
            DATA_KEY => [[[ACTION_ACCOUNT, '=', $id], [ACTION_SYMBOL, '=', $symbol], [ACTION_STATUS, '=', ACTION_STATUS_ENTER_WAITTING] ]],
            DATA_EDITOR => [
                ACTION_STATUS => ACTION_STATUS_CANCLE,
                ACTION_PENDING => 0
            ]
        ]);

        ob_end_clean();
        return Reply::make(true, 'success', $result);

    }


    //
    
    //
    
   
   
    
}
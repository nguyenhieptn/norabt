<?php

namespace App\Http\Controllers\Admin;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

use App\Helpers\Auth\Role;
use App\Helpers\Control\Ctrl;
use App\Helpers\DB\Edge;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use App\Helpers\Uploader\FileFunc;
use App\Helpers\Token\JWToken;
use App\Http\Controllers\Controller;
use Illuminate\Support\Facades\DB;

class Lab_resultsController extends Controller
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

        $this->mainModel = Models::get('Admin/Lab_results');
        $this->tableName = LAB_RESULTS_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[LAB_RESULT_ID] = true;

        if (!Role::checkAdmin()) Reply::finish(false, ERROR_PERMISSION, ['data' => 'Please login by other account']);
    }

    public function add(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas = array_diff_key($datas, $this->dependCols);
        $result = $this->mainModel->add([$datas]);
        if (!$result['result']) Reply::finish($result);
        Reply::finish(true, 'success', $datas);
    }

    public function addGetId(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas = array_diff_key($datas, $this->dependCols);
        $datas[LAB_RESULT_ID] = uniqid();
        $result = $this->mainModel->add([$datas]);
        if (!$result['result']) Reply::finish($result);
        Reply::finish(true, 'success', $datas);
    }

    public function adds(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        foreach ($datas as $key => $val) {
            $datas[$key] = array_diff_key($datas[$key], $this->dependCols);
        }
        Reply::finish($this->mainModel->add($datas));
    }

    public function addGetIds(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        foreach ($datas as $key => $val) {
            $datas[$key] = array_diff_key($datas[$key], $this->dependCols);
            $datas[$key][LAB_RESULT_ID] = uniqid();
        }
        $result = $this->mainModel->add($datas);
        if (!$result['result']) Reply::finish($result);
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
        foreach ($datas as $key => $data) {
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
        foreach ($datas[DATA_KEY] as $key => $data) {
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

    public function mapping()
    {
        $mapData = [];
        $mapData[LAB_RESULT_SYMBOL] =  Edge::mapping(Models::get('Admin/Lab_watchlist'), null, LAB_WL_SYMBOL, LAB_WL_SYMBOL, null, function ($db) {
            $db->orderBy(LAB_WL_SYMBOL, 'DESC');
        });
        $mapData[LAB_RESULT_CAMPAIGN] = Edge::mapping(Models::get('Admin/Lab_campaigns'), null, LAB_CAMPAIGN_ID, LAB_CAMPAIGN_NAME);
        $mapData[LAB_RESULT_ACCOUNT] = Edge::mapping(Models::get('Admin/Lab_account'), null, LAB_ACCOUNT_ID, LAB_ACCOUNT_NAME,null, function($db){
            if(!Role::checkRoot()){
                $db->where(LAB_ACCOUNT_USER, '=', Auth::user()->{AUTHEN_ID});
            } 
        });
        $mapData[LAB_RESULT_STRATEGY] = Edge::mapping(Models::get('Admin/Lab_strategies'), null, LAB_STRATEGY_ID, LAB_STRATEGY_NAME, null, function ($db) {
            $db->orderBy(LAB_STRATEGY_NAME, 'DESC');
        });
        $mapData[LAB_RESULT_CONTAINER] = $mapData[LAB_RESULT_STRATEGY];
        $mapData[LAB_RESULT_FLOW] = Edge::mapping(Models::get('Admin/Lab_results'), null, LAB_RESULT_FLOW, LAB_RESULT_FLOW, null, function ($db) {
            $db->distinct();
        });
        $mapData[LAB_RESULT_TYPE] = (object)[LAB_RESULT_TYPE_LONG => 'Long', LAB_RESULT_TYPE_SHORT => 'Short'];
        $mapData[LAB_RESULT_STATUS] = (object)[
            LAB_RESULT_STATUS_PENDING => 'Pending',
            LAB_RESULT_STATUS_MATCHED => 'Matched',
            LAB_RESULT_STATUS_STOPLOSS => 'Stop Loss',
            LAB_RESULT_STATUS_TAKEPROFIT => 'Take Profit',
            LAB_RESULT_STATUS_CANCLE => 'Cancel',
            LAB_RESULT_STATUS_MATCHED_PART => 'Matched Part',
            LAB_RESULT_STATUS_STOP_PENDING => 'Stop Pending',
            LAB_RESULT_STATUS_ENTER_WAITTING => 'Waiting',
            LAB_RESULT_STATUS_PHASE_PENDING => 'Waiting Pharse',
        ];
        $mapData[LAB_RESULT_PENDING] = (object)[0 => 'Finished', 1 => 'Opening'];
        $mapData[LAB_RESULT_PHASE] = [0 => 0, 1 => 1, 2 => 2, 3 => 3, 4 => 4, 5 => 5, 6 => 6, 7 => 7, 8 => 8, 9 => 9, 10 => 10];
        Reply::finish(true, 'Success', $mapData);
    }

    public function suggest(Request $request)
    {
        $datas = $request->input('search', '');
        $suggestData = $this->mainModel->read([[[LAB_RESULT_SYMBOL, 'contain', $datas]]], function ($builder) {
            $builder->limit(20);
        });
        $suggest = [];
        if ($suggestData['result']) {

            $suggest = $suggestData['data']->mapWithKeys(function ($item) {
                return [$item->{LAB_RESULT_ID} => $item->{LAB_RESULT_SYMBOL}];
            });
        }
        Reply::finish(true, '', $suggest);
    }

    public function filter(Request $request)
    {
        $datas = $request->all();
        $datas[FLAG_FILTER_LOGIC] = 'and';
        $responseData = $this->mainModel->filter($datas);
        if (!$responseData['result']) Reply::finish($responseData);

        $dbName = Ctrl::get('control_lab_db', 'coin_crawler');
        $Candle1mModel = Models::get('Admin/Lab_candle_1m');
        $Candle1mModel->query_builder = DB::connection($dbName)->table('lab_candle_1m');

        $data = $responseData['data']['data_table'];
       
        foreach($data as $row){
            
            $sym = $row->{LAB_RESULT_SYMBOL};
            $time = $row->{LAB_RESULT_CHART};
            $dataLab = $Candle1mModel->read([[ [LAB_CANDLE_1M_SYMBOL, '=' , $sym], [LAB_CANDLE_1M_TIME , '=' , $time] ]]);
            if(isset($dataLab['data'][0])){
                $volume = $dataLab['data'][0]->{LAB_CANDLE_1M_VOLUME};
                $row->{'lab_volume_1m'} = $volume;
            }
           
        }
        Reply::finish($responseData);
    }

    public function get(Request $request)
    {
        $data = $request->input('data', []);
        $limit = $request->input('limit', null);
        $skip = $request->input('skip', null);
        $orderBy = $request->input('orderBy', null);
        $orderAsc = $request->input('asc', true);

        $selectColumn = array_keys($this->mainModel->struct);

        $result = $this->mainModel->read($data, function ($db) use ($limit, $skip, $orderBy, $orderAsc) {
            if ($orderBy !== null) $db->orderBy($orderBy, $orderAsc ? 'ASC' : 'DESC');
            if ($skip !== null) $db->skip($skip);
            if ($limit !== null) $db->limit($limit);
        }, false, [
            LAB_RESULT_ID,
            LAB_RESULT_ORDER_TIME,
            LAB_RESULT_TYPE,
            LAB_RESULT_PROFIT,
            LAB_RESULT_REAL_PROFIT,
            LAB_RESULT_STATUS,
            LAB_RESULT_SYMBOL,
            LAB_RESULT_PENDING,
            LAB_RESULT_PARAMS,
            LAB_RESULT_STRATEGY,
            LAB_RESULT_CAMPAIGN,
            LAB_RESULT_SELL_TIME,
            LAB_RESULT_CHART,
            LAB_RESULT_PHASE,
            LAB_RESULT_REAL_PNL,
            LAB_RESULT_FLOW,
            LAB_RESULT_CONTAINER,
            LAB_RESULT_EVENT_PROFIT
        ]);

        return $result;
    }


    //

    //

    public function updateIndicator(Request $request){
        set_time_limit(0);
        $account_id = $request->input('account_id', '');

        $account_id = intval($account_id);

        if($account_id == '')  Reply::finish(false , 'no account id', '' );


        $responseData = $this->mainModel->read([[ [LAB_RESULT_ACCOUNT , '=' , $account_id] ]] );



        $Candle1dModel = Models::get('Admin/Lab_candle_1d');
        $Candle1dModel->query_builder = DB::connection(Ctrl::get('control_lab_db', 'coin_crawler'))->table('lab_candle_1d');

        $data = $responseData['data'];
       
        foreach($data as $row){
            
            $id = $row->{LAB_RESULT_ID};
            $sym = $row->{LAB_RESULT_SYMBOL};
            $time = intval($row->{LAB_RESULT_CHART}) ;
       
            $dataLab = $Candle1dModel->read([[ [LAB_CANDLE_1D_SYMBOL, '=' , $sym], [LAB_CANDLE_1D_TIME , '=' , $time] ]]);
     
            if(isset($dataLab['data'][0])){

          

                $rsi = $dataLab['data'][0]->{LAB_CANDLE_1D_RSI14};
                $rsi_ema9 = $dataLab['data'][0]->{LAB_CANDLE_1D_RSI_EMA9};
                $rsi_wma = $dataLab['data'][0]->{LAB_CANDLE_1D_RSI_WMA};
                $row->{LAB_RESULT_1D_RSI_14} = $rsi;
                $row->{LAB_RESULT_1D_RSI_EMA9} = $rsi_ema9;
                $row->{LAB_RESULT_1D_RSI_WMA} = $rsi_wma;

              


                $this->mainModel->edit([
                    DATA_KEY =>[[ [LAB_RESULT_ID , '=' , $id] ]],
                    DATA_EDITOR => (array)$row
                ]);
            }
           
        }
        
        
        Reply::finish(true , 'success', $account_id );

    }

    public function updateWalletBalance(Request $request){
        set_time_limit(0);
        $account_id = $request->input('account_id', '');

        $account_id = intval($account_id);

        if($account_id == '')  Reply::finish(false , 'no account id', '' );


        $responseData = $this->mainModel->read([[ [LAB_RESULT_ACCOUNT , '=' , $account_id] ]] );



        $ModelLabTrackBalance = Models::get('Admin/Lab_track_balance');

        $data = $responseData['data'];
       
        foreach($data as $row){
            
            $id = $row->{LAB_RESULT_ID};
        
            $time = intval($row->{LAB_RESULT_CHART}) ;
            // $time = intval($row->{LAB_RESULT_CLOSE_TIME}) ;
       
            $dataLab =  $ModelLabTrackBalance->read([[ [LAB_TRACK_BL_ACCOUNT, '=' ,   $account_id], [LAB_TRACK_BL_TIME , '=' , $time] ]]);
         
            if(isset($dataLab['data'][0])){

               
                $row->{LAB_RESULT_WALLET_BALANCE} = $dataLab['data'][0]->{LAB_TRACK_BL_BALANCE};

              


                $this->mainModel->edit([
                    DATA_KEY =>[[ [LAB_RESULT_ID , '=' , $id] ]],
                    DATA_EDITOR => (array)$row
                ]);
            }
           
        }
        
        
        Reply::finish(true , 'success', $account_id );

    }

    public function updateProfitInvest(Request $request){
        set_time_limit(0);
        $account_id = $request->input('account_id', '');

        $account_id = intval($account_id);

        if($account_id == '')  Reply::finish(false , 'no account id', '' );


        $responseData = $this->mainModel->read([[ [LAB_RESULT_ACCOUNT , '=' , $account_id] ]] );

        $data = $responseData['data'];
       
        foreach($data as $row){
            
            $id = $row->{LAB_RESULT_ID};
        
     
            if(isset($row->{LAB_RESULT_WALLET_BALANCE})){
                $row->{LAB_RESULT_PROFIT_INVEST} = ($row->{LAB_RESULT_REAL_PNL} / $row->{LAB_RESULT_WALLET_BALANCE}) * 100;

                $this->mainModel->edit([
                    DATA_KEY =>[[ [LAB_RESULT_ID , '=' , $id] ]],
                    DATA_EDITOR => (array)$row
                ]);
            }
            
           
           
        }
        
        
        Reply::finish(true , 'success', $account_id );

    }




}

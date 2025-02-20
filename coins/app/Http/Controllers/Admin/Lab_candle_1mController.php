<?php
namespace App\Http\Controllers\Admin;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

use App\Helpers\Auth\Role;
use App\Helpers\Control\Ctrl;
use App\Helpers\DB\Edge;
use App\Helpers\DB\Models;
use Illuminate\Support\Facades\DB;
use App\Helpers\Request\Reply;
use App\Helpers\Uploader\FileFunc;
use App\Helpers\Token\JWToken;
use App\Http\Controllers\Controller;


class Lab_candle_1mController extends Controller  
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

        $this->mainModel = Models::get('Admin/Lab_candle_1m');
        $this->mainModel->query_builder = DB::connection(Ctrl::get('control_lab_db', 'coin_crawler'))->table('lab_candle_1m');
        $this->tableName = LAB_CANDLE_1M_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[LAB_CANDLE_1M_ID] = true;

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
        $datas[LAB_CANDLE_1M_ID] = uniqid();
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
            $datas[$key][LAB_CANDLE_1M_ID] = uniqid();
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
        $mapData[LAB_CANDLE_1M_SYMBOL] = Edge::mapping(Models::get('Admin/Lab_watchlist'), null, LAB_WL_SYMBOL, LAB_WL_SYMBOL);
        Reply::finish(true, 'Success', $mapData);
    }

    public function suggest(Request $request)
    {
        $datas = $request->input('search', '');
        $suggestData = $this->mainModel->read([[[LAB_CANDLE_1M_SYMBOL, 'contain', $datas]]], function($builder){$builder->limit(20);});
        $suggest = [];
        if($suggestData['result']){
             
            $suggest = $suggestData['data']->mapWithKeys(function ($item){
                return [$item->{LAB_CANDLE_1M_ID} => $item->{LAB_CANDLE_1M_SYMBOL}];
            });
        }
        Reply::finish(true, '', $suggest);
    }

    public function filter(Request $request)
    {
        $datas = $request->all();
        $datas[FLAG_FILTER_LOGIC] = 'and';
        // $symbol = $datas['symbol'];
        $responseData = $this->mainModel->filter($datas);
        if(!$responseData['result']) Reply::finish($responseData);
        Reply::finish($responseData);
    }

    public function get(Request $request){
        $data = $request->input('data', []);
        $limit = $request->input('limit', null);
        $skip = $request->input('skip', null);
        $orderBy = $request->input('orderBy', null);
        $orderAsc = $request->input('asc', true);

        $symbol = $request->input('symbol', null);

        $selectColumn = array_keys($this->mainModel->struct);

        $result = $this->mainModel->read($data, function($db) use($limit, $skip, $orderBy, $orderAsc , $symbol){
            if($orderBy !== null) $db->orderBy($orderBy, $orderAsc ? 'ASC' : 'DESC');
            if($skip !== null) $db->skip($skip);
            if($limit !== null) $db->limit($limit);
            if($symbol !== null) $db->whereIn(LAB_CANDLE_1M_SYMBOL, $symbol);

        }, false, $selectColumn);

        return $result;
    }

    public function getMissData(Request $request){
        $symbols = $request->input('symbols', null);
        $dbName = $request->input('dbName', null);
        if($dbName == null || $dbName == '') Reply::finish(false, 'Please define database');
        $m1Model = Models::get('Admin/Lab_candle_1m', [], $dbName);
        return $m1Model->read([[[LAB_CANDLE_1M_INTERVAL, '>', 60000]]], function($db) use($symbols){
            $db->whereIn(LAB_CANDLE_1M_SYMBOL, $symbols)->orderBy(LAB_CANDLE_1M_TIME);
        });
    }


    

    //
    
    //
    
   
   
    
}
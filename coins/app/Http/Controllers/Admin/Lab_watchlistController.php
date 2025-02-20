<?php
namespace App\Http\Controllers\Admin;

use App\Crawler\Caculator\EmaLab;
use App\Crawler\Caculator\RsiEma;
use App\Crawler\Caculator\RsiLab;
use App\Crawler\Caculator\SignalLab;
use App\Crawler\History\CandleLab;
use App\Helpers\Admin\Services;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

use App\Helpers\Auth\Role;
use App\Helpers\DB\Models;
use App\Helpers\Request\Checker;
use App\Helpers\Request\Reply;
use App\Helpers\Uploader\FileFunc;
use App\Helpers\Token\JWToken;
use App\Http\Controllers\Controller;


class Lab_watchlistController extends Controller  
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

        $this->mainModel = Models::get('Admin/Lab_watchlist');
        $this->tableName = LAB_WATCHLIST_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[LAB_WL_ID] = true;

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
        $datas[LAB_WL_ID] = uniqid();
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
            $datas[$key][LAB_WL_ID] = uniqid();
        }
        $result = $this->mainModel->add($datas);
        if(!$result['result']) Reply::finish($result);
        Reply::finish(true, 'success', $datas);
    }

    public function drop(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        if(!Checker::validate($datas[LAB_WL_SYMBOL], 'Word')) return Reply::make(false, 'Wrong format');
        $result = exec('sudo systemctl stop lab_candle@'.$datas[LAB_WL_SYMBOL] . '*');
        $datas =  $this->mainModel->keyToCondition($datas);
        $dropResult = $this->mainModel->drop([$datas]);
        Reply::finish($dropResult);
    }

    public function drops(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        foreach ($datas as $key=>$data){
            if(!Checker::validate($data[LAB_WL_SYMBOL], 'Word')) return Reply::make(false, 'Wrong format');
            $result = exec('sudo systemctl stop lab_candle@'.$data[LAB_WL_SYMBOL] . '*');
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
        if(isset($datas[DATA_EDITOR][LAB_WL_SYMBOL])) unset($datas[DATA_EDITOR][LAB_WL_SYMBOL]);
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
        if(isset($datas[DATA_EDITOR][LAB_WL_SYMBOL])) unset($datas[DATA_EDITOR][LAB_WL_SYMBOL]);
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
        Reply::finish(true, 'Success', $mapData);
    }

    public function suggest(Request $request)
    {
        $datas = $request->input('search', '');
        $suggestData = $this->mainModel->read([[[LAB_WL_SYMBOL, 'contain', $datas]]], function($builder){$builder->limit(20);});
        $suggest = [];
        if($suggestData['result']){
             
            $suggest = $suggestData['data']->mapWithKeys(function ($item){
                return [$item->{LAB_WL_ID} => $item->{LAB_WL_SYMBOL}];
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
        foreach($responseData['data'][DATA_TABLE] as $key => $val){
            $responseData['data'][DATA_TABLE][$key]->{'lab_candle'} = Services::isActive('lab_candle@'.$val->{LAB_WL_SYMBOL} . '*');
        }
        Reply::finish($responseData);
    }

    // public function startService(Request $request){
    //     set_time_limit(0);
    //     $symbol = $request->input('symbol');

    //     $result = exec('sudo php '.base_path().'/artisan lab_candle_start '.$symbol);

    //     $result = $this->mainModel->edit([
    //         DATA_KEY => [[[LAB_WL_SYMBOL, '=', $symbol]]],
    //         DATA_EDITOR => [LAB_WL_TIME => time(), LAB_WL_STOPTIME => null]
    //     ]);

    //     ob_end_clean();
    //     return $result;

    // }

    // public function calculate(Request $request){
    //     set_time_limit(0);
    //     $symbol = $request->input('symbol');
    //     $command = 'sudo php ' . base_path() . '/artisan lab_candle_calculate ' . $symbol;
    //     $result = exec($command);
    //     ob_end_clean();
    //     return Reply::make(true, 'success', $result);

    // }

    public function stopService(Request $request){
        $symbol = $request->input('symbol');
        if(!Checker::validate($symbol, 'Word')) return Reply::make(false, 'Wrong format');
        $result = exec('sudo systemctl stop lab_candle@'.$symbol . '*');
        $result = $this->mainModel->edit([
            DATA_KEY => [[[LAB_WL_SYMBOL, '=', $symbol]]],
            DATA_EDITOR => [LAB_WL_STOPTIME => time()]
        ]);
        return Reply::make(true, 'success', $result);

    }

    public function restartService(Request $request){
        $symbol = $request->input('symbol');
        if(!Checker::validate($symbol, 'Word')) return Reply::make(false, 'Wrong format');
        // $result = exec('sudo systemctl restart lab_candle@'.$symbol . '*');
        $result = exec('sudo systemctl restart lab_candle@'.$symbol);
        $result = $this->mainModel->edit([
            DATA_KEY => [[[LAB_WL_SYMBOL, '=', $symbol]]],
            DATA_EDITOR => [LAB_WL_TIME => time(), LAB_WL_STOPTIME => null]
        ]);

        return Reply::make(true, 'success', $result);
    }

    public function cleanData(Request $request){
        $symbol = $request->input('symbol');
        $result = Models::get('Admin/Lab_candle_1m')->drop([[[LAB_CANDLE_1M_SYMBOL, '=', $symbol]]]);
        if(!$result['result']) return $result;
        $result = Models::get('Admin/Lab_candle_3m')->drop([[[LAB_CANDLE_3M_SYMBOL, '=', $symbol]]]);
        if(!$result['result']) return $result;
        $result = Models::get('Admin/Lab_candle_15m')->drop([[[LAB_CANDLE_15M_SYMBOL, '=', $symbol]]]);
        if(!$result['result']) return $result;
        $result = Models::get('Admin/Lab_candle_1h')->drop([[[LAB_CANDLE_1H_SYMBOL, '=', $symbol]]]);
        if(!$result['result']) return $result;
        $result = Models::get('Admin/Lab_candle_4h')->drop([[[LAB_CANDLE_4H_SYMBOL, '=', $symbol]]]);
        if(!$result['result']) return $result;
        $result = Models::get('Admin/Lab_candle_1d')->drop([[[LAB_CANDLE_1D_SYMBOL, '=', $symbol]]]);
        if(!$result['result']) return $result;

        return Reply::make(true, 'success');

    }



    public function updateRank(Request $request)
    {
        set_time_limit(0);
  


        $responseData = $this->mainModel->read([]);

   

        if (!$responseData['result']) Reply::finish($responseData);

        $model_coin_market = Models::get('Admin/CoinMarket');

        $ranks = $model_coin_market->read();

        if (!$ranks['result']) Reply::finish($ranks);
        $ranks = $ranks['data'];


        $rankData = [];
        foreach ($ranks as $row) {
            $rankData[$row->{COINMARKET_SYMBOL}] = $row->{COINMARKET_RANK};
        }




        $data = $responseData['data'];

        foreach ($data as $row) {

 
            $id = $row->{LAB_WL_ID};
            $sym = $row->{LAB_WL_SYMBOL};

            $row->{LAB_WL_SYM_RANK} = isset($rankData[$sym]) ? $rankData[$sym] : '';
          
            $this->mainModel->edit([
                DATA_KEY => [[[LAB_WL_ID, '=', $id]]],
                DATA_EDITOR => (array)$row
            ]);
        }


        Reply::finish(true, 'success', 'ok');
    }





    //
    
    //
    
   
   
    
}
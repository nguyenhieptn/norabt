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


class Lab_candle_1dController extends Controller
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

        $this->mainModel = Models::get('Admin/Lab_candle_1d');

        $this->mainModel->query_builder = DB::connection(Ctrl::get('control_lab_db', 'coin_crawler'))->table('lab_candle_1d');
        $this->tableName = LAB_CANDLE_1D_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[LAB_CANDLE_1D_ID] = true;

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
        $datas[LAB_CANDLE_1D_ID] = uniqid();
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
            $datas[$key][LAB_CANDLE_1D_ID] = uniqid();
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
        $mapData[LAB_CANDLE_1D_SYMBOL] = Edge::mapping(Models::get('Admin/Lab_watchlist'), null, LAB_WL_SYMBOL, LAB_WL_SYMBOL);
        Reply::finish(true, 'Success', $mapData);
    }

    public function suggest(Request $request)
    {
        $datas = $request->input('search', '');
        $suggestData = $this->mainModel->read([[[LAB_CANDLE_1D_SYMBOL, 'contain', $datas]]], function ($builder) {
            $builder->limit(20);
        });
        $suggest = [];
        if ($suggestData['result']) {

            $suggest = $suggestData['data']->mapWithKeys(function ($item) {
                return [$item->{LAB_CANDLE_1D_ID} => $item->{LAB_CANDLE_1D_SYMBOL}];
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
        if (!$responseData['result']) Reply::finish($responseData);
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
        }, false, $selectColumn);

        return $result;
    }





    public function getFluctuation(Request $request)
    {
        set_time_limit(0);
        $startTime = $request->input('startTime', '');
        $stopTime = $request->input('stopTime', '');
        $opt = $request->input('opt', '');

        if ($startTime == '' || $stopTime == '' || $opt == '') {
            Reply::finish(false, 'something wrong', 'error');
        }

        $model_coin_market = Models::get('Admin/CoinMarket');

        $ranks = $model_coin_market->read();

        if (!$ranks['result']) return Reply::finish(false, 'something wrong', 'error');;
        $ranks = $ranks['data'];


        $rankData = [];
        foreach($ranks as $row ){
            $rankData[$row->{COINMARKET_SYMBOL}] = $row->{COINMARKET_RANK};
        }

  

        $startTime = intval($startTime)  * 1000;
        $stopTime = intval($stopTime) * 1000;

        $colNames =  [
            'symbol' => 'lab_candle_' . $opt . '_symbol',
            'low' =>  'lab_candle_' . $opt . '_low',
            'high' =>  'lab_candle_' . $opt . '_high',
            'opentime' =>  'lab_candle_' . $opt . '_open_time',
            'closetime' =>  'lab_candle_' . $opt . '_close_time',
            'startpoint' =>  'lab_candle_' . $opt . '_startpoint',

        ];


        if ($opt == '4h') {
            $model = Models::get('Admin/Lab_candle_4h');
            $model->query_builder = DB::connection(Ctrl::get('control_lab_db', 'coin_crawler'))->table('lab_candle_4h');
        } else {
            $model = Models::get('Admin/Lab_candle_1d');

            $model->query_builder = DB::connection(Ctrl::get('control_lab_db', 'coin_crawler'))->table('lab_candle_1d');
        }





        $data = $model->read([[
            [$colNames['closetime'], '>=', $startTime],
            [$colNames['closetime'], '<=', $stopTime],
            [$colNames['startpoint'], '=', 1]
        ]], function ($db) use ($colNames) {
            $db->orderBy($colNames['closetime'], 'ASC');
        });



        if (!$data['result']) return Reply::finish(false, 'something wrong', 'error');;
        $data = $data['data'];


        $tranferData = [];

        foreach ($data as $row) {
            $symbol = $row->{$colNames['symbol']};

            if (array_key_exists($symbol, $tranferData)) {
                $tranferData[$symbol][] = $row;
            } else {

                $tranferData[$symbol] = [];
                $tranferData[$symbol][] = $row;
            }
        }

       

        $resultData = [];
        foreach ($tranferData as $key => $value) {



            $out = $this->calFluctuation($value , $colNames , $rankData);

            $resultData[] = $out;
        }



        Reply::finish(true, 'success', $resultData);
    }


    private function calFluctuation($val , $colNames , $rank )
    {

        $lowlowsum = 0;
        $highhighsum = 0;
        $highlowsum = 0;

        $lowlowcount = 0;
        $highlowcount = 0;
        $highhighcount = 0;

        $minTime = 0;
        $maxTime = 0;
        $symbol = '';

        $maxHighLow = 0;
        $minLowLow = 0;
        foreach ($val as $i => $row) {

            $time = $row->{$colNames['closetime']};
            if($i == 0 ){
                $minTime = $time;
                $symbol = $row->{$colNames['symbol']};
            }else{
                $maxTime = $time;
            }
            if (isset($val[$i - 1])) {

                
                $highval = floatval($row->{$colNames['high']});
                $lowval = floatval($row->{$colNames['low']});
                if($lowval > 0){
                    if (floatval($row->{$colNames['low']}) > 0) {
                        $highlowval = (($highval - $lowval) * 100) / $highval;

                        $highlowval = round($highlowval , 3);
                        
                        $highlowsum += $highlowval ;
                        $highlowcount++;

                        if($highlowval > $maxHighLow){
                            $maxHighLow = $highlowval;
                        } 
                       
                    }
                }

                if (floatval($val[$i - 1]->{$colNames['low']}) > 0) {

                    $lowlowval =  (( $lowval - floatval($val[$i - 1]->{$colNames['low']})) * 100) / $lowval;

                    $lowlowval = round($lowlowval , 3);
                    if ($lowlowval < 0) {
                        $lowlowsum += $lowlowval;
                        $lowlowcount++;
                    }else{
                        $lowlowval = 0;
                    }

                    if( $lowlowval  < $minLowLow ){
                        $minLowLow = $lowlowval;
                    } 


                }

                if (floatval($val[$i - 1]->{$colNames['high']}) > 0) {

                    $highhighval =  (( $highval - floatval($val[$i - 1]->{$colNames['high']})) * 100) / $highval;

                    $highhighval = round($highhighval , 3);
                    if ($highhighval > 0) {
                        $highhighsum += $highhighval;
                        $highhighcount++;
                    }


                }
               
            }
        }

        $avgHighLow = $highlowcount > 0 ?  $highlowsum / $highlowcount : 0;
        $avgLowLow = $lowlowcount > 0 ?  $lowlowsum / $lowlowcount : 0;
        $avgHighHigh = $highhighcount > 0 ? $highhighsum / $highhighcount : 0;
        return [
            'symbol' => $symbol,
            'minTime' => $minTime,
            'maxTime' => $maxTime,
            'highlowavg' => $avgHighLow ,
            'lowlowavg' => $avgLowLow,
            'highhighavg' => $avgHighHigh ,
            'max' => $maxHighLow,
            'min' => $minLowLow,
            'rank' => isset($rank[$symbol]) ? $rank[$symbol] : ''
        ];



    }


    //

    //




}

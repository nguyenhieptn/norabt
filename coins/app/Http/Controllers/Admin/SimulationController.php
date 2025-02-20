<?php
namespace App\Http\Controllers\Admin;

use App\Crawler\Caculator\Ema;
use App\Crawler\History\Candle;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

use App\Helpers\Auth\Role;
use App\Helpers\Control\Ctrl;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use App\Helpers\Uploader\FileFunc;
use App\Helpers\Token\JWToken;
use App\Http\Controllers\Controller;
use Illuminate\Support\Facades\DB;

class SimulationController extends Controller  
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();
        if(!Role::checkAdmin()) Reply::finish(false, ERROR_PERMISSION, ['data'=>'Please login by other account']); 
        
    }


    public function getLabCandleData(Request $requests){

        $symbol = $requests->input('symbol', '');
        if($symbol == '') Reply::finish(false, 'No symbol');
        $interval = $requests->input('interval', '1m');
        $stop = $requests->input('stop', '');
        $start = $requests->input('start', '');
        $campaign = $requests->input('campaign', '');

        $model = Models::get('Admin/Lab_candle_'.$interval);
        $model->query_builder = DB::connection(Ctrl::get('control_lab_db', 'coin_crawler'))->table('lab_candle_'.$interval);
        $LabModel = Models::get('Admin/Lab_results');
        $orderModel = Models::get('Admin/Lab_order');

        $columnName = [
            'LAB_CANDLE_ID' => "lab_candle_" . $interval . "_id",
            'LAB_CANDLE_TIME' => "lab_candle_" . $interval . "_time",
            'LAB_CANDLE_SYMBOL' => "lab_candle_" . $interval . "_symbol",
            'LAB_CANDLE_OPEN_TIME' => "lab_candle_" . $interval . "_open_time",
            'LAB_CANDLE_CLOSE_TIME' => "lab_candle_" . $interval . "_close_time",
            'LAB_CANDLE_OPEN' => "lab_candle_" . $interval . "_open",
            'LAB_CANDLE_CLOSE' => "lab_candle_" . $interval . "_close",
            'LAB_CANDLE_HIGH' => "lab_candle_" . $interval . "_high",
            'LAB_CANDLE_LOW' => "lab_candle_" . $interval . "_low",
            'LAB_CANDLE_TRADES' => "lab_candle_" . $interval . "_trades",
            'LAB_CANDLE_VOLUME' => "lab_candle_" . $interval . "_volume",
            'LAB_CANDLE_EMA5' => "lab_candle_" . $interval . "_ema5",
            'LAB_CANDLE_EMA9' => "lab_candle_" . $interval . "_ema9",
            'LAB_CANDLE_EMA12' => "lab_candle_" . $interval . "_ema12",
            'LAB_CANDLE_EMA13' => "lab_candle_" . $interval . "_ema13",
            'LAB_CANDLE_EMA26' => "lab_candle_" . $interval . "_ema26",
            'LAB_CANDLE_MACD' => "lab_candle_".$interval."_macd",
            'LAB_CANDLE_SIGNAL' => "lab_candle_".$interval."_signal",
            'LAB_CANDLE_HISTOGRAM' => "lab_candle_".$interval."_histogram",
            'LAB_CANDLE_STARTPOINT' => "lab_candle_".$interval."_startpoint",
            'LAB_CANDLE_SIGNAL' => "lab_candle_" . $interval . "_signal",
            'LAB_CANDLE_HISTOGRAM' => "lab_candle_" . $interval . "_histogram",
            'LAB_CANDLE_SIGNAL7'=>'lab_candle_'.$interval.'_signal7',
            'LAB_CANDLE_HISTOGRAM7'=>'lab_candle_'.$interval.'_histogram7',
            'LAB_CANDLE_SIGNAL4'=>'lab_candle_'.$interval.'_signal4',
            'LAB_CANDLE_HISTOGRAM4'=>'lab_candle_'.$interval.'_histogram4',
            'LAB_CANDLE_SIGNAL2'=>'lab_candle_'.$interval.'_signal2',
            'LAB_CANDLE_HISTOGRAM2'=>'lab_candle_'.$interval.'_histogram2',
            'LAB_CANDLE_SIGNAL3'=>'lab_candle_'.$interval.'_signal3',
            'LAB_CANDLE_HISTOGRAM3'=>'lab_candle_'.$interval.'_histogram3',
            'LAB_CANDLE_SIGNAL5'=>'lab_candle_'.$interval.'_signal5',
            'LAB_CANDLE_HISTOGRAM5'=>'lab_candle_'.$interval.'_histogram5',
            'LAB_CANDLE_SIGNAL6'=>'lab_candle_'.$interval.'_signal6',
            'LAB_CANDLE_HISTOGRAM6'=>'lab_candle_'.$interval.'_histogram6',
            'LAB_CANDLE_STARTPOINT' => "lab_candle_" . $interval . "_startpoint",
            'LAB_CANDLE_RSI14' => "lab_candle_" . $interval . "_rsi14",
            'LAB_CANDLE_RSI_EMA9' => "lab_candle_" . $interval . "_rsi_ema9",
            'LAB_CANDLE_RSI_EMA5' => "lab_candle_" . $interval . "_rsi_ema5",
            'LAB_CANDLE_RSI_EMA4' => "lab_candle_" . $interval . "_rsi_ema4",
            
            
        ];

        $candleDatas = $model->read([[ 
            [$columnName['LAB_CANDLE_SYMBOL'], '=', $symbol], 
            [$columnName['LAB_CANDLE_STARTPOINT'], '=', 1],
            
            
        ]], function($db) use($columnName, $start, $stop){

            if($start != '') $db->where($columnName['LAB_CANDLE_TIME'], '>=', $start * 1000);
            if($stop != '') $db->where($columnName['LAB_CANDLE_TIME'], '<=', $stop * 1000);

            if($start == '' || $stop == '') $db->limit(1000);

            $db->orderBy($columnName['LAB_CANDLE_TIME'], 'DESC')->limit(5000);
            
        });

        if(!$candleDatas['result']) return $candleDatas;

        $candleDatas = $candleDatas['data'];

        if(count($candleDatas) == 0) Reply::finish(false, 'Can not get data');


        $labEventDatas = $LabModel->read([[
            [LAB_RESULT_CHART, '>=', $candleDatas[count($candleDatas)-1]->{$columnName['LAB_CANDLE_OPEN_TIME']} ],
            [LAB_RESULT_CHART, '<=', $candleDatas[0]->{$columnName['LAB_CANDLE_CLOSE_TIME']} ]
        ]], function($db) use($campaign,$start, $stop){
            if($campaign != '') $db->where(LAB_RESULT_CAMPAIGN, '=', $campaign);
            if($start == '' || $stop == '') $db->limit(100);
            $db->orderBy(LAB_RESULT_CHART, 'DESC');

        }, true, [
            LAB_RESULT_ID,
            LAB_RESULT_CHART, 
            LAB_RESULT_ORDER_TIME, 
            LAB_RESULT_TYPE, 
            LAB_RESULT_ORDER_PRICE, 
            LAB_RESULT_ENTER_PRICE,
            LAB_RESULT_STATUS, 
            LAB_RESULT_PROFIT, 
            LAB_RESULT_MATCHED_PRICE,
            LAB_RESULT_MATCHED_TIME,
            LAB_RESULT_SELL_PRICE, 
            LAB_RESULT_SELL_TIME, 
            LAB_RESULT_PARAMS
        ]);

        if(!$labEventDatas['result']) return $labEventDatas;

        $labEventDatas = $labEventDatas['data'];

        $LabEventId = [];
        $labEventLength = count($labEventDatas);
        for ($i = $labEventLength - 1; $i >= 0; $i--){
            $labEventData = $labEventDatas[$i];
            $LabEventId[] = $labEventData->{LAB_RESULT_ID};
            // if(!isset($LabEventDataIndex[$labEventData->{LAB_RESULT_CHART}])) $LabEventDataIndex[$labEventData->{LAB_RESULT_CHART}] = $labEventData;
        }



        $orderData = $orderModel->read([], function($db) use($LabEventId){

            $db->whereIn(LAB_ORDER_ACTION, $LabEventId);
            $db->orderBy(LAB_ORDER_TIME, 'DESC');

        }, true, [
            LAB_ORDER_ID,
            LAB_ORDER_TIME,
            LAB_ORDER_QTY,
            LAB_ORDER_TYPE,
            LAB_ORDER_PRICE,
            LAB_ORDER_PHASE
        ]);

        if(!$orderData['result']) return $orderData;

        $orderData = $orderData['data'];



        $returnData = ['data' => [], 'event_flag' => array_reverse($labEventDatas->toArray()), 'order_flag'=>array_reverse($orderData->toArray())];

        $candleLength = count($candleDatas);
        for ($i = $candleLength - 1; $i >= 0; $i--){
            $candleData = $candleDatas[$i];
            $returnData['data'][] = [
                'open_time' => $candleData->{$columnName['LAB_CANDLE_OPEN_TIME']},
                'close_time' => $candleData->{$columnName['LAB_CANDLE_CLOSE_TIME']},
                'open' => $candleData->{$columnName['LAB_CANDLE_OPEN']},
                'close' => $candleData->{$columnName['LAB_CANDLE_CLOSE']},
                'high' => $candleData->{$columnName['LAB_CANDLE_HIGH']},
                'low' => $candleData->{$columnName['LAB_CANDLE_LOW']},
                'ema5' => $candleData->{$columnName['LAB_CANDLE_EMA5']},
                'ema9' => $candleData->{$columnName['LAB_CANDLE_EMA9']},
                'ema12' => $candleData->{$columnName['LAB_CANDLE_EMA12']},
                'ema13' => $candleData->{$columnName['LAB_CANDLE_EMA13']},
                'ema26' => $candleData->{$columnName['LAB_CANDLE_EMA26']},
                'macd' => $candleData->{$columnName['LAB_CANDLE_MACD']},
                'signal' => $candleData->{$columnName['LAB_CANDLE_SIGNAL']},
                'histogram' => $candleData->{$columnName['LAB_CANDLE_HISTOGRAM']},
                'histogram2' => $candleData->{$columnName['LAB_CANDLE_HISTOGRAM2']},
                'histogram3' => $candleData->{$columnName['LAB_CANDLE_HISTOGRAM3']},
                'histogram4' => $candleData->{$columnName['LAB_CANDLE_HISTOGRAM4']},
                'histogram5' => $candleData->{$columnName['LAB_CANDLE_HISTOGRAM5']},
                'histogram6' => $candleData->{$columnName['LAB_CANDLE_HISTOGRAM6']},
                'histogram7' => $candleData->{$columnName['LAB_CANDLE_HISTOGRAM7']},
                'rsi' => $candleData->{$columnName['LAB_CANDLE_RSI14']},
                'rsi_ema9' => $candleData->{$columnName['LAB_CANDLE_RSI_EMA9']},
                'rsi_ema5' => $candleData->{$columnName['LAB_CANDLE_RSI_EMA5']},
                'rsi_ema4' => $candleData->{$columnName['LAB_CANDLE_RSI_EMA4']},
            ];
        }

        Reply::finish(true, 'success', $returnData);

    }

}
<?php
namespace App\Http\Controllers\Admin;

use App\Crawler\Caculator\Ema;
use App\Crawler\History\Candle;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

use App\Helpers\Auth\Role;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use App\Helpers\Uploader\FileFunc;
use App\Helpers\Token\JWToken;
use App\Http\Controllers\Controller;

class TradechartController extends Controller  
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();
        if(!Role::checkAdmin()) Reply::finish(false, ERROR_PERMISSION, ['data'=>'Please login by other account']); 
        
    }


    public function getCandleData(Request $requests){

        $symbol = $requests->input('symbol', '');
        if($symbol == '') Reply::finish(false, 'No symbol');
        $interval = $requests->input('interval', '1m');
        $limit = $requests->input('limit', '1000');

        $account = $requests->input('account', null);
        if($account === null) Reply::finish(false, 'No Account');

        $model = Models::get('Admin/Candle_'.$interval);
        $eventModel = Models::get('Admin/Actions');
       

        $columnName = [
            'CANDLE_ID' => "candle_" . $interval . "_id",
            'CANDLE_SYMBOL' => "candle_" . $interval . "_symbol",
            'CANDLE_OPEN_TIME' => "candle_" . $interval . "_open_time",
            'CANDLE_CLOSE_TIME' => "candle_" . $interval . "_close_time",
            'CANDLE_OPEN' => "candle_" . $interval . "_open",
            'CANDLE_CLOSE' => "candle_" . $interval . "_close",
            'CANDLE_HIGH' => "candle_" . $interval . "_high",
            'CANDLE_LOW' => "candle_" . $interval . "_low",
            'CANDLE_TRADES' => "candle_" . $interval . "_trades",
            'CANDLE_VOLUME' => "candle_" . $interval . "_volume",
            'CANDLE_EMA5' => "candle_" . $interval . "_ema5",
            'CANDLE_EMA9' => "candle_" . $interval . "_ema9",
            'CANDLE_EMA12' => "candle_" . $interval . "_ema12",
            'CANDLE_EMA13' => "candle_" . $interval . "_ema13",
            'CANDLE_EMA26' => "candle_" . $interval . "_ema26",
            'CANDLE_MACD' => "candle_".$interval."_macd",
            'CANDLE_SIGNAL' => "candle_".$interval."_signal",
            'CANDLE_HISTOGRAM' => "candle_".$interval."_histogram",
            'CANDLE_SIGNAL7'=>'candle_'.$interval.'_signal7',
            'CANDLE_HISTOGRAM7'=>'candle_'.$interval.'_histogram7',
            'CANDLE_SIGNAL4'=>'candle_'.$interval.'_signal4',
            'CANDLE_HISTOGRAM4'=>'candle_'.$interval.'_histogram4',
            'CANDLE_SIGNAL2'=>'candle_'.$interval.'_signal2',
            'CANDLE_HISTOGRAM2'=>'candle_'.$interval.'_histogram2',
            'CANDLE_SIGNAL3'=>'candle_'.$interval.'_signal3',
            'CANDLE_HISTOGRAM3'=>'candle_'.$interval.'_histogram3',
            'CANDLE_SIGNAL5'=>'candle_'.$interval.'_signal5',
            'CANDLE_HISTOGRAM5'=>'candle_'.$interval.'_histogram5',
            'CANDLE_SIGNAL6'=>'candle_'.$interval.'_signal6',
            'CANDLE_HISTOGRAM6'=>'candle_'.$interval.'_histogram6',
            'CANDLE_RSI14'=>'candle_'.$interval.'_rsi14',
            'CANDLE_RSI_EMA9'=>'candle_'.$interval.'_rsi_ema9',
            'CANDLE_RSI_EMA5'=>'candle_'.$interval.'_rsi_ema5',
            'CANDLE_RSI_EMA4'=>'candle_'.$interval.'_rsi_ema4',
            'CANDLE_RSI_WMA'=>'candle_'.$interval.'_rsi_wma',
            
        ];

        $candleDatas = $model->read([[ [$columnName['CANDLE_SYMBOL'], '=', $symbol]]], function($db) use($columnName, $limit){
            $db->orderBy($columnName['CANDLE_CLOSE_TIME'], 'DESC')->limit($limit);
        });

        if(!$candleDatas['result']) return $candleDatas;

        $candleDatas = $candleDatas['data'];

        $eventDatas = [];
        $orderData = [];
        if($limit >= 1000){
            $eventDatas = $eventModel->read([[ [ACTION_SYMBOL, '=', $symbol], [ACTION_ACCOUNT, '=', $account], [ACTION_CHART, '>=', $candleDatas[count($candleDatas)-1]->{$columnName['CANDLE_OPEN_TIME']} ] ]], function($db) use($columnName){
                $db->orderBy(ACTION_CHART, 'DESC');
            }, true, [
                ACTION_ID,
                ACTION_CHART, 
                ACTION_TYPE, 
                ACTION_MATCHED_PRICE, 
                ACTION_ENTER_PRICE,
                ACTION_STATUS, 
                ACTION_PROFIT, 
                ACTION_MATCHED_TIME,
                ACTION_MATCHED_PRICE,
                ACTION_SELL_TIME, 
                ACTION_SELL_PRICE,
                ACTION_STOP_REASON]);
    
            if(!$eventDatas['result']) return $eventDatas;

            
    
            $eventDatas = $eventDatas['data']->toArray();

            $LabEventId = [];
            foreach($eventDatas as $event){
                $LabEventId[] = $event->{ACTION_ID};
            }

            $orderModel = Models::get('Admin/Orders');

            $orderData = $orderModel->read([[[ORDER_QTY , '>', 0]]], function($db) use($LabEventId){
                $db->whereIn(ORDER_ACTION, $LabEventId);
                $db->orderBy(ORDER_TIME, 'DESC');
    
            }, true, [
                ORDER_ID,
                ORDER_TIME,
                ORDER_QTY,
                ORDER_TYPE,
                ORDER_PRICE,
                ORDER_SIDE
            ]);
    
            if(!$orderData['result']) return $orderData;
    
            $orderData = $orderData['data']->toArray();
        }

        
        $returnData = ['data' => [], 'flag' => array_reverse($eventDatas), 'order_flag' => array_reverse($orderData)];

        $candleLength = count($candleDatas);
        for ($i = $candleLength - 1; $i >= 0; $i--){
            $candleData = $candleDatas[$i];
            $returnData['data'][] = [
                'open_time' => $candleData->{$columnName['CANDLE_OPEN_TIME']},
                'close_time' => $candleData->{$columnName['CANDLE_CLOSE_TIME']},
                'open' => $candleData->{$columnName['CANDLE_OPEN']},
                'close' => $candleData->{$columnName['CANDLE_CLOSE']},
                'high' => $candleData->{$columnName['CANDLE_HIGH']},
                'low' => $candleData->{$columnName['CANDLE_LOW']},
                'ema5' => $candleData->{$columnName['CANDLE_EMA5']},
                'ema9' => $candleData->{$columnName['CANDLE_EMA9']},
                'ema12' => $candleData->{$columnName['CANDLE_EMA12']},
                'ema13' => $candleData->{$columnName['CANDLE_EMA13']},
                'ema26' => $candleData->{$columnName['CANDLE_EMA26']},
                'macd' => $candleData->{$columnName['CANDLE_MACD']},
                'signal' => $candleData->{$columnName['CANDLE_SIGNAL']},
                'histogram' => $candleData->{$columnName['CANDLE_HISTOGRAM']},
                'histogram7' => $candleData->{$columnName['CANDLE_HISTOGRAM7']},
                'histogram4' => $candleData->{$columnName['CANDLE_HISTOGRAM4']},
                'histogram5' => $candleData->{$columnName['CANDLE_HISTOGRAM5']},
                'histogram6' => $candleData->{$columnName['CANDLE_HISTOGRAM6']},
                'histogram2' => $candleData->{$columnName['CANDLE_HISTOGRAM2']},
                'histogram3' => $candleData->{$columnName['CANDLE_HISTOGRAM3']},
                'rsi' => $candleData->{$columnName['CANDLE_RSI14']},
                'rsi_ema9' => $candleData->{$columnName['CANDLE_RSI_EMA9']},
                'rsi_ema5' => $candleData->{$columnName['CANDLE_RSI_EMA5']},
                'rsi_ema4' => $candleData->{$columnName['CANDLE_RSI_EMA4']},
                'rsi_wma' => $candleData->{$columnName['CANDLE_RSI_WMA']},
            ];
        }

        Reply::finish(true, 'success', $returnData);

    }

}
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

class TestnetchartController extends Controller  
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();
        if(!Role::checkMonitor()) Reply::finish(false, ERROR_PERMISSION, ['data'=>'Please login by other account']); 
        
    }


    public function getCandleData(Request $requests){

        $symbol = $requests->input('symbol', '');
        if($symbol == '') Reply::finish(false, 'No symbol');
        $interval = $requests->input('interval', '1m');
        $limit = $requests->input('limit', '1000');

        $account = $requests->input('account', '');

        $model = Models::get('Admin/Candle_'.$interval);
        $LabModel = Models::get('Admin/Testnet_results');
        $change24Model = Models::get('Admin/Change_24h');
        $orderModel = Models::get('Admin/Testnet_order');

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
            'CANDLE_STARTPOINT' => "candle_".$interval."_startpoint",
            'CANDLE_SIGNAL' => "candle_" . $interval . "_signal",
            'CANDLE_HISTOGRAM' => "candle_" . $interval . "_histogram",
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
            $db->orderBy($columnName['CANDLE_CLOSE_TIME'], 'DESC');
            $db->limit($limit);
        });

        if(!$candleDatas['result']) return $candleDatas;

        $candleDatas = $candleDatas['data'];


        $altsCoinData = [];
        $orderData = [];
        $labEventDatas = [];

        if($limit >= 1000){

            $labEventDatas = $LabModel->read([[ [TESTNET_RESULT_SYMBOL, '=', $symbol], [TESTNET_RESULT_CHART, '>=', $candleDatas[count($candleDatas)-1]->{$columnName['CANDLE_OPEN_TIME']} ]]], function($db) use($account){

                if($account != '') $db->where(TESTNET_RESULT_ACCOUNT, '=', $account);
                $db->orderBy(TESTNET_RESULT_CHART, 'DESC');
    
            }, true, [
                TESTNET_RESULT_ID,
                TESTNET_RESULT_CHART, 
                TESTNET_RESULT_ENTER_TIME, 
                TESTNET_RESULT_TYPE, 
                TESTNET_RESULT_ENTER_PRICE, 
                TESTNET_RESULT_STATUS, 
                TESTNET_RESULT_PROFIT, 
                TESTNET_RESULT_MATCHED_PRICE,
                TESTNET_RESULT_MATCHED_TIME,
                TESTNET_RESULT_SELL_PRICE, 
                TESTNET_RESULT_SELL_TIME, 
                TESTNET_RESULT_PARAMS
            ]);
    
            if(!$labEventDatas['result']) return $labEventDatas;
    
            $labEventDatas = $labEventDatas['data']->toArray();
    
            $LabEventDataIndex = [];
            $labEventLength = count($labEventDatas);
            $LabEventId = [];
            for ($i = $labEventLength - 1; $i >= 0; $i--){
                $labEventData = $labEventDatas[$i];
                $LabEventId[] = $labEventData->{TESTNET_RESULT_ID};
                // if(!isset($LabEventDataIndex[$labEventData->{TESTNET_RESULT_CHART}])) $LabEventDataIndex[$labEventData->{TESTNET_RESULT_CHART}] = $labEventData;
            }

            $altsCoinData = $change24Model->read([], function($db){
                $db->orderBy(CHANGE24H_TIME, 'DESC')->limit(5000);
            }, false, [
                CHANGE24H_TIME, CHANGE24H_UP
            ]);
            if(!$altsCoinData['result']) return $altsCoinData;
            $altsCoinData = $altsCoinData['data']->toArray();

            $orderData = $orderModel->read([], function($db) use($LabEventId){

                $db->whereIn(TESTNET_ORDER_ACTION, $LabEventId);
                $db->orderBy(TESTNET_ORDER_TIME, 'DESC');
    
            }, true, [
                TESTNET_ORDER_ID,
                TESTNET_ORDER_TIME,
                TESTNET_ORDER_QTY,
                TESTNET_ORDER_TYPE,
                TESTNET_ORDER_PRICE,
                TESTNET_ORDER_PHASE
            ]);
    
            if(!$orderData['result']) return $orderData;
    
            $orderData = $orderData['data']->toArray();
        }


        $returnData = ['data' => [], "alts_coin" =>$altsCoinData , 'event_flag' => array_reverse($labEventDatas), 'order_flag'=>array_reverse($orderData)];

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
                'histogram2' => $candleData->{$columnName['CANDLE_HISTOGRAM2']},
                'histogram3' => $candleData->{$columnName['CANDLE_HISTOGRAM3']},
                'histogram4' => $candleData->{$columnName['CANDLE_HISTOGRAM4']},
                'histogram5' => $candleData->{$columnName['CANDLE_HISTOGRAM5']},
                'histogram6' => $candleData->{$columnName['CANDLE_HISTOGRAM6']},
                'histogram7' => $candleData->{$columnName['CANDLE_HISTOGRAM7']},
                'rsi' => $candleData->{$columnName['CANDLE_RSI14']},
                'rsi_ema9' => $candleData->{$columnName['CANDLE_RSI_EMA9']},
                'rsi_ema5' => $candleData->{$columnName['CANDLE_RSI_EMA5']},
                'rsi_ema4' => $candleData->{$columnName['CANDLE_RSI_EMA4']},
                'rsi_wma' => $candleData->{$columnName['CANDLE_RSI_WMA']},
                'volume' => $candleData->{$columnName['CANDLE_VOLUME']}
                            
            ];
        }

        Reply::finish(true, 'success', $returnData);

    }


    public function getCandleData1w1M(Request $requests){ 
        $symbol = $requests->input('symbol', '');
        if($symbol == '') Reply::finish(false, 'No symbol');
        $interval = $requests->input('interval', '1w');

        $model = Models::get('Crawler/Candlestick_'.$interval);

        $result = $model->read([[  ['candlestick_' . $interval . '_symbol', '=', $symbol]]], function($db) use($interval) {
            $db->orderBy(  'candlestick_' . $interval . '_close_time', 'DESC');
           
        });

        Reply::finish($result);
    } 

    public function getCandleDataTable1w(Request $requests){ 
 

        $model = Models::get('Crawler/Candlestick_1w');

        $result = $model->read([], function($db)  {
            $db->orderBy( CANDLESTICK_1W_OPEN_TIME, 'DESC');
            $db->limit(1);
           
        });

        $time = $result['data'][0]->{CANDLESTICK_1W_OPEN_TIME};

      
      

        $result = $model->read([[  [CANDLESTICK_1W_OPEN_TIME , '>=' , $time - 604800000 *5]  ]]);

         Reply::finish($result);
     
    } 

    public function getCandleDataTable1M(Request $requests){ 
 

        $model = Models::get('Crawler/Candlestick_1M');

        $result = $model->read([], function($db)  {
            $db->orderBy( CANDLESTICK_1M_OPEN_TIME, 'DESC');
            $db->limit(1);
           
        });

        $time = $result['data'][0]->{CANDLESTICK_1M_OPEN_TIME};

        $result = $model->read([[  [CANDLESTICK_1M_OPEN_TIME , '>=' , $time - 2678400000 *5] ]]);

         Reply::finish($result);
     
    } 

}
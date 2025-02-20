<?php

namespace App\Event\Lab;

use App\Helpers\Admin\Telegram;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use App\Event\EventFunc;
use Exception;

class EventCheck_old2
{
    use EventFunc;

    function __construct($campaign)
    {

        try {
            //code...

            date_default_timezone_set('Asia/Ho_Chi_Minh');
            $this->campaign = $campaign;
            $this->symbol = $campaign->{LAB_CAMPAIGN_SYMBOL};

            $params = $campaign->{LAB_CAMPAIGN_PARAMS};
            $params = json_decode($params, true);
            if (!$params) $params = [];
            $this->params = $params;

            $this->Candle1hModel = Models::get('Admin/Lab_candle_1h');
            $this->Candle15mModel = Models::get('Admin/Lab_candle_15m');
            $this->Candle3mModel = Models::get('Admin/Lab_candle_3m');
            $this->Candle1mModel = Models::get('Admin/Lab_candle_1m');
            $this->eventModel = Models::get('Admin/Lab_results');
            $this->eventLog = Models::get('Admin/Lab_event_logs');
            $this->eventOrder = Models::get('Admin/Lab_order');
            $this->strategyModel = Models::get('Admin/Lab_strategies');

            $this->altsCoinModel = Models::get('Admin/Change_24h');

            $strategy = $campaign->{LAB_CAMPAIGN_STRATEGY};
            $strategyData = $this->strategyModel->read([[[LAB_STRATEGY_ID, '=', $strategy]]]);
            if (!$strategyData['result']) throw new Exception($strategyData['message']);
            if (!isset($strategyData['data'][0])) throw new Exception('Can not find any Strategy');
            $strategyDB = $strategyData['data'][0];
            $strategyData = $strategyDB->{LAB_STRATEGY_CONTENT};
            $strategyData = json_decode($strategyData, true);
            if ($strategyData == null) throw new Exception('Please define Strategy');


            $this->cfgStoploss = get($strategyDB->{LAB_STRATEGY_STOPLOSS}, 0.2);
            $this->cfgTakeprofit = get($strategyDB->{LAB_STRATEGY_TAKEPROFIT}, 1);
            $this->cfgInterval = get($strategyDB->{LAB_STRATEGY_INTERVAL}, 6);
            $this->cfgTimelife = get($strategyDB->{LAB_STRATEGY_TIMELIFE}, 6);
            $this->cfgBaseprofit = get($strategyDB->{LAB_STRATEGY_BASEPROFIT}, $this->cfgTakeprofit);
            $this->cfgStepprofit = get($strategyDB->{LAB_STRATEGY_STEPPROFIT}, 0);
            $this->cfgBackprofit = get($strategyDB->{LAB_STRATEGY_BACKPROFIT}, 0);
            $this->cfgBackprofitBaseon = get($strategyDB->{LAB_STRATEGY_BASEPROFIT_BASEON}, 'close');

            $this->cfgStrategy = $strategyData;

            $this->labPendingTime = 0; // save the time when event finish. 
            $this->labPendingStop = 0; // stop event skip, if > 1 then stop

            $this->maxOrderProfit = 0;
            $this->baseProfit = $this->cfgBaseprofit;

            $this->event = null;

            $this->needData = $this->calNeedMetadataData($this->cfgStrategy);

            $this->data = [];
            $this->orderData = [];

            $this->models = [];

            $this->periodFrame = [
                '1m' => 60 * 1000,
                '3m' => 3 * 60 * 1000,
                '15m' => 15 * 60 * 1000,
                '1h' => 60 * 60 * 1000,
                '4h' => 4 * 60 * 60 * 1000,
            ];
        } catch (\Exception $th) {
            $ms = " [" .  $this->campaign->{LAB_CAMPAIGN_NAME} . "] " . $th->getFile() . " " . $th->getLine() . " ". $th->getMessage();
            echo $ms . "\n";
            Telegram::send(TELE_ICON_ERROR . $ms, TELE_SIMULATE_ERROR);
        }
    }


    private function getData($time, $candle1m)
    {
        foreach ($this->needData as $symbol => $frames) {
            if (!isset($this->data[$symbol])) $this->data[$symbol] = [];
            foreach ($frames as $frame => $maxIndex) {

                $maxIndex = -$maxIndex;

                $columnName = [
                    'LAB_CANDLE_ID' => "lab_candle_" . $frame . "_id",
                    'LAB_CANDLE_TIME' => "lab_candle_" . $frame . "_time",
                    'LAB_CANDLE_SYMBOL' => "lab_candle_" . $frame . "_symbol",
                    'LAB_CANDLE_OPEN_TIME' => "lab_candle_" . $frame . "_open_time",
                    'LAB_CANDLE_CLOSE_TIME' => "lab_candle_" . $frame . "_close_time",
                    'LAB_CANDLE_OPEN' => "lab_candle_" . $frame . "_open",
                    'LAB_CANDLE_CLOSE' => "lab_candle_" . $frame . "_close",
                    'LAB_CANDLE_HIGH' => "lab_candle_" . $frame . "_high",
                    'LAB_CANDLE_LOW' => "lab_candle_" . $frame . "_low",
                    'LAB_CANDLE_TRADES' => "lab_candle_" . $frame . "_trades",
                    'LAB_CANDLE_VOLUME' => "lab_candle_" . $frame . "_volume",
                    'LAB_CANDLE_EMA5' => "lab_candle_" . $frame . "_ema5",
                    'LAB_CANDLE_EMA9' => "lab_candle_" . $frame . "_ema9",
                    'LAB_CANDLE_EMA12' => "lab_candle_" . $frame . "_ema12",
                    'LAB_CANDLE_EMA13' => "lab_candle_" . $frame . "_ema13",
                    'LAB_CANDLE_EMA26' => "lab_candle_" . $frame . "_ema26",
                    'LAB_CANDLE_MACD' => "lab_candle_" . $frame . "_macd",
                    'LAB_CANDLE_SIGNAL' => "lab_candle_" . $frame . "_signal",
                    'LAB_CANDLE_HISTOGRAM' => "lab_candle_" . $frame . "_histogram",
                    'LAB_CANDLE_STARTPOINT' => "lab_candle_" . $frame . "_startpoint",
                ];

                if (!isset($this->data[$symbol][$frame])) $this->data[$symbol][$frame] = [];

                if (!isset($this->models[$frame])) $this->models[$frame] = Models::get('Admin/Lab_candle_' . $frame);

                if ($symbol == $this->symbol && $frame == '1m') {
                    $frame0 = $candle1m;
                } else {
                    $frame0 = $this->models[$frame]->read([[
                        [$columnName['LAB_CANDLE_SYMBOL'], '=', $symbol],
                        [$columnName['LAB_CANDLE_TIME'], '<=', $time],
                        [$columnName['LAB_CANDLE_TIME'], '>', $time - 60 * 1000]
                    ]], function ($db) use ($columnName) {
                        $db->orderBy($columnName['LAB_CANDLE_TIME'], 'DESC')->limit(1);
                    });
                    if (!$frame0['result']) return $frame0;
                    if (!isset($frame0['data'][0])) return Reply::make(false, 'Can not get data ' . $symbol . ' frame 0');
                    $frame0 = $frame0['data'][0];
                }

                $needRefresh = true;
                if (
                    isset($this->data[$symbol][$frame][0])
                    && $this->data[$symbol][$frame][0]->{$columnName['LAB_CANDLE_CLOSE_TIME']} == $frame0->{$columnName['LAB_CANDLE_CLOSE_TIME']}
                ) {
                    $needRefresh = false;
                    $this->data[$symbol][$frame][0] = $frame0;
                } else {
                    $this->data[$symbol][$frame] = [$frame0];
                }

                if ($needRefresh && $maxIndex > 0) {
                    $frames = $this->models[$frame]->read([[
                        [$columnName['LAB_CANDLE_SYMBOL'], '=', $symbol],
                        [$columnName['LAB_CANDLE_STARTPOINT'], '=', '1'],
                        [$columnName['LAB_CANDLE_CLOSE_TIME'], '<', $frame0->{$columnName['LAB_CANDLE_CLOSE_TIME']}],
                        [$columnName['LAB_CANDLE_CLOSE_TIME'], '>', $frame0->{$columnName['LAB_CANDLE_CLOSE_TIME']} - (($maxIndex + 2) * $this->periodFrame[$frame])]

                    ]], function ($db) use ($columnName, $maxIndex) {
                        $db->orderBy($columnName['LAB_CANDLE_CLOSE_TIME'], 'DESC')->limit($maxIndex);
                    });

                    if (!$frames['result']) return $frames;

                    foreach ($frames['data'] as $data) {
                        $this->data[$symbol][$frame][] = $data;
                    }
                }

                if (count($this->data[$symbol][$frame]) < $maxIndex + 1) return Reply::make(false, "Can not get enough $maxIndex data " . $symbol . ' ' . $frame);
            }
        }

        
        // if(!isset($this->altsCoinData) || ($time - doubleval($this->altsCoinData->{CHANGE24H_TIME})) > 60000){
        //     $altCoinData = $this->altsCoinModel->read([[[CHANGE24H_TIME, '<=', $time], [CHANGE24H_TIME, '>', $time-600000] ]], function($db){
        //         $db->orderBy(CHANGE24H_TIME, 'DESC')->limit(1);
        //     });
           
        //     if(!$altCoinData['result']) return $altCoinData;
        //     if(!isset($altCoinData['data'][0])) return Reply::make(false, 'No Alts Coin Data at ' . date("d/m/Y H:i:s", $time / 1000));
        //     $this->altsCoinData = $altCoinData['data'][0];
            
        // }

        return Reply::make(true, 'success');
    }


    private function caculateElement($struct, $dynamicIndex=null)
    {

        if (is_numeric($struct)) return Reply::make(true, $struct, $struct);

        if (is_string($struct)) {
            if ($struct == 'order_time') {
                if ($this->event == null) return Reply::make(false, 'No Event');
                return Reply::make(true, $struct, doubleval($this->event->{LAB_RESULT_ORDER_TIME}));
            }
            return Reply::make(false, 'Can not caculate ' . $struct);
        }

        $type = get($struct['type'], 'frame');

        if ($type == 'frame') {
            $frame = get($struct['frame'], null);
            $index = get($struct['index'], null);
            $column = get($struct['column'], null);
            $symbol = get($struct['symbol'], $this->symbol);
            $percent = doubleval(get($struct['percent'], 100));
            $position = get($struct['position'], 'current');

            if($index == 'dynamic'){
                $index = $dynamicIndex;
            }else{
                $index = -intval($index);
            }

            if ($percent != 100) {
                $des = "$symbol Frame $percent% $frame $column($index)";
            } else {
                $des = "$symbol Frame $frame $column($index)";
            }

            if ($frame === null || $index === null || $column === null || $symbol === null)
                return Reply::make(false, 'Please define symbol, frame, column and index '. $des . json_encode($struct));
            
            $column = 'lab_candle_' . $frame . '_' . $column;

            $data = $this->data;

            if ($position == 'order') {
                $phase = get($struct['phase'], 0);
                $data = $this->orderData[$phase];
                $des .= " Pharse $phase";
            }

            if (!isset($data[$symbol])) return Reply::make(false, 'Can not get Data ' . $symbol);
            if (!isset($data[$symbol][$frame])) return Reply::make(false, "Can not get Data $symbol $frame");
            if (!isset($data[$symbol][$frame][$index])) return Reply::make(false, "Can not get Data $symbol $frame $index");
            if (!isset($data[$symbol][$frame][$index]->{$column})) return Reply::make(false, "Can not get Data $symbol $frame $index $column");;

            if (is_numeric($data[$symbol][$frame][$index]->{$column}))
                return Reply::make(true, $des, doubleval($data[$symbol][$frame][$index]->{$column}) * $percent / 100);
            return Reply::make(true, $des, $data[$symbol][$frame][$index]->{$column});
        }

        if ($type == 'event') {
            if ($this->event == null) return Reply::make(false, 'No Event');
            $column = get($struct['column'], null);
            $column = 'lab_result_'. $column;
            $percent = doubleval(get($struct['percent'], 100));
            $value = $this->event->{$column};
            $des = "Event $percent% $column";
            if (is_numeric($value))
                return Reply::make(true, $des, doubleval($value) * $percent / 100);
            return Reply::make(true, $des, $value);
        }

        if($type == 'altscoin'){
            $column = get($struct['column'], null);
            $column = 'change24h_'. $column;
            if(!isset($this->altsCoinData) || !isset($this->altsCoinData->{$column})) return Reply::make(false, 'Can not get data ' . json_encode($struct));
            $value = $this->altsCoinData->{$column};
            $percent = doubleval(get($struct['percent'], 100));
            $des = "AltsCoin $percent% $column";
            if (is_numeric($value))
                return Reply::make(true, $des, doubleval($value) * $percent / 100);
            return Reply::make(true, $des, $value);
        }

        if ($type == 'cross') {

            $index = get($struct['index'], null);
            $frame = get($struct['frame'], null);
            $stop = get($struct['stop'], null);
            $thresold = get($struct['thresold'], null);
            $column1 = get($struct['column_1'], null);
            $column2 = get($struct['column_2'], null);
            $symbol = get($struct['symbol'], $this->symbol);
            if ($frame === null || $index === null || $column1 === null || $column2 === null)
                return Reply::make(false, 'Please define symbol, frame, column and index ' . json_encode($struct));

            if($index == 'dynamic'){
                $index = $dynamicIndex;
            }else{
                $index = -intval($index);
            }
            $column1 = 'lab_candle_' . $frame . '_' . $column1;
            $column2 = 'lab_candle_' . $frame . '_' . $column2;

            $des = "$symbol Frame $frame $column1 cross $column2 in $index candles";

            if (!isset($this->data[$symbol])) return Reply::make(false, 'Can not get Data ' . $symbol);
            if (!isset($this->data[$symbol][$frame])) return Reply::make(false, "Can not get Data $symbol $frame");

            $cross = 0;
            $needStop = 0;
            $frameData = $this->data[$symbol][$frame];
            if (count($frameData) < $index) return Reply::make(false, 'Not enough Data to calculate ' . json_encode($struct));
            for ($i = 1; $i <= $index; $i++) {
                $newValue1 = doubleval($frameData[$i - 1]->{$column1});
                $newValue2 = doubleval($frameData[$i - 1]->{$column2});

                $oldValue1 = doubleval($frameData[$i]->{$column1});
                $oldValue2 = doubleval($frameData[$i]->{$column2});

                if(is_array($stop)){
                    $isStop = $this->compareOr($stop, $i);
                    if(!$isStop['result']) return $isStop;
                    
                    
                    if($isStop['data']){
                        // print_r($isStop);
                        echo date("d/m/Y H:i:s", $this->data[$this->symbol]['1m'][0]->{LAB_CANDLE_1M_TIME} / 1000) ."_stop_". $needStop. "_". $cross . "\n";
                        return Reply::make(true, $des, $cross);
                    }
                }
               
                if (($newValue1 - $newValue2) * ($oldValue1 - $oldValue2) <= 0) {
                    $cross++;
                    $needStop=0;

                } else {

                    if(is_numeric($thresold)){
                        $needStop++;
                        if ($needStop >= $thresold) {
                            echo date("d/m/Y H:i:s", $this->data[$this->symbol]['1m'][0]->{LAB_CANDLE_1M_TIME} / 1000) ."_thresold_". $needStop. "_". $cross . "\n";
                            return Reply::make(true, $des, $cross);
                        }
                    }
                    
                    
                }
            }

            // echo date("d/m/Y H:i:s", $this->data[$this->symbol]['1m'][0]->{LAB_CANDLE_1M_TIME} / 1000) ."_". $cross . "\n";

            return Reply::make(true, $des, $cross);
        }

        Reply::make(false, 'Can not caculate ' . json_encode($struct));
    }


    public function check($candle1m)
    {
        try {


            $time = $candle1m->{LAB_CANDLE_1M_TIME};
            $time_start = microtime(true);
            $result = $this->getData($time, $candle1m);
            if (!$result['result']) {
                echo $result['message'] . "\n";
                return Reply::make(true, $result['message']);
            }

            $isPending = $this->checkEvent();

            if (!$isPending['result']) return $isPending;

            if ($isPending['data']) {
                // echo "Event check pending " . $this->symbol . " Excute time " . (microtime(true) - $time_start) . " second\n";
                return $isPending;
            }

            $type = 0;

            $longResult = null;
            $shortResult = null;

            $condition = $this->getMatchConfition(LAB_RESULT_TYPE_SHORT, 0);
            
            if($condition != null){
                $shortResult = $this->compareOr($condition['condition']);
                if (!$shortResult['result']) return $shortResult;
                if($shortResult['data']) $type = LAB_RESULT_TYPE_SHORT;
                
            }

            if($type == 0){
                $condition = $this->getMatchConfition(LAB_RESULT_TYPE_LONG, 0);
                
                if($condition != null){
                    $longResult = $this->compareOr($condition['condition']);
                    if (!$longResult['result']) return $longResult;
                    if($longResult['data']) $type = LAB_RESULT_TYPE_LONG;
                }
            }
           
            if (isset($this->params[LAB_CAMPAIGN_PARAMS_LOG]) && $this->params[LAB_CAMPAIGN_PARAMS_LOG] == 1) {
                $this->eventLog->add([[
                    LAB_ELOG_TIME => $time,
                    LAB_ELOG_CAMPAIGN => $this->campaign->{LAB_CAMPAIGN_ID},
                    LAB_ELOG_SYMBOL => $this->symbol,
                    LAB_ELOG_MATCHED => $type,
                    LAB_ELOG_CHART => $candle1m->{LAB_CANDLE_1M_OPEN_TIME},
                    LAB_ELOG_RESULT => json_encode([
                        'long' => $longResult,
                        'short' => $shortResult,
                    ]),
                    LAB_ELOG_BASE => json_encode($this->data)
                ]]);
            }

            if ($type != 0) {

                $condition = $this->getMatchConfition($type, 0);

                $enterStep = get($condition['enter_step'], 0);
                $enterRule = get($condition['enter_rule'], null);

                $interval = $this->cfgInterval;

                if ($this->labPendingTime >= 0 && $time - $this->labPendingTime >= ($interval * 60000)) {

                    $this->labPendingTime = -1;

                    $closePrice = doubleval($candle1m->{LAB_CANDLE_1M_CLOSE});


                    $addData = [
                        LAB_RESULT_ENTER_TIME => $time,
                        LAB_RESULT_ENTER_PRICE => $closePrice,
                        LAB_RESULT_CAMPAIGN => $this->campaign->{LAB_CAMPAIGN_ID},
                        LAB_RESULT_SYMBOL => $this->symbol,
                        LAB_RESULT_TYPE => $type,
                        LAB_RESULT_CHART => $time,
                        LAB_RESULT_LOW => $candle1m->{LAB_CANDLE_1M_LOW},
                        LAB_RESULT_HIGH => $candle1m->{LAB_CANDLE_1M_HIGH},
                        LAB_RESULT_BASE => json_encode(['0' => $this->data]),
                        LAB_RESULT_PENDING => 1,
                        LAB_RESULT_STATUS => LAB_RESULT_STATUS_ENTER_WAITTING,
                        LAB_RESULT_PHASE => 0,
                        LAB_RESULT_STRATEGY => $this->campaign->{LAB_CAMPAIGN_STRATEGY},

                    ];

                    $this->eventModel->add([$addData]);

                    $event =  $this->eventModel->read([[
                        [LAB_RESULT_CAMPAIGN, '=', $this->campaign->{LAB_CAMPAIGN_ID}],
                        [LAB_RESULT_PENDING, '=', 1]
                    ]]);
                    if (!$event['result'] || !isset($event['data'][0])) {
                        return Reply::make(true, 'No Pending Event', false);
                    }

                    $event = $event['data'][0];
                    $this->event = $event;

                    if ($enterStep <= 0 && $enterRule === null) {
                        $this->makeOrder($event, $closePrice, 0, $time);
                    } else {
                        $this->enterBase = $closePrice;
                        Telegram::send(TELE_ICON_WAITTING . " [" .  $this->campaign->{LAB_CAMPAIGN_NAME} . "] #" . $this->symbol  . " Waitting for " . ($type == LAB_RESULT_TYPE_LONG ? 'Long' : 'Short') . " Order\n-Time: " . date("d/m/Y H:i:s", $time / 1000) . " \n- Close Price: " . $closePrice, TELE_SIMULATE);
                    }
                }
            }


            // echo "Event check " . $this->symbol . " Excute time " . (microtime(true) - $time_start) . " second\n";

            return Reply::make(true, 'Check done');
        } catch (\Exception $th) {
            return Reply::make(false, $th->getFile() . ' ' . $th->getLine() . ' ' . $th->getMessage());
        }
    }



    private function checkEvent()
    {

        $khung15m = $this->data[$this->symbol]['15m'];
        $khung3m = $this->data[$this->symbol]['3m'];
        $khung1m = $this->data[$this->symbol]['1m'];

        $closePrice = doubleval($khung1m[0]->{LAB_CANDLE_1M_CLOSE});
        $high = doubleval($khung1m[0]->{LAB_CANDLE_1M_HIGH});
        $low = doubleval($khung1m[0]->{LAB_CANDLE_1M_LOW});
        $openTime = doubleval($khung1m[0]->{LAB_CANDLE_1M_OPEN_TIME});
        $closeTime = doubleval($khung1m[0]->{LAB_CANDLE_1M_CLOSE_TIME});
        $ema5 = doubleval($khung1m[0]->{LAB_CANDLE_1M_EMA5});

        if ($this->cfgBackprofitBaseon == 'ema5_3m') {
            $ema5 = doubleval($khung3m[0]->{LAB_CANDLE_3M_EMA5});
        }
        if ($this->cfgBackprofitBaseon == 'ema5_15m') {
            $ema5 = doubleval($khung15m[0]->{LAB_CANDLE_15M_EMA5});
        }

        $time = doubleval($khung1m[0]->{LAB_CANDLE_1M_TIME});

        $event =  $this->eventModel->read([[
            [LAB_RESULT_CAMPAIGN, '=', $this->campaign->{LAB_CAMPAIGN_ID}],
            [LAB_RESULT_PENDING, '=', 1]
        ]]);
        if (!$event['result'] || !isset($event['data'][0])) {
            return Reply::make(true, 'No Pending Event', false);
        }

        $event = $event['data'][0];
        $this->event = $event;

        $this->orderData = json_decode($event->{LAB_RESULT_BASE}, true);
        if (json_last_error() != JSON_ERROR_NONE) return Reply::make(false, 'Can not get Order data');

        $type = $event->{LAB_RESULT_TYPE};
        $phase = doubleval($event->{LAB_RESULT_PHASE});

        $stoploss = $this->cfgStoploss;
        $takeprofit = $this->cfgTakeprofit;
        $stepprofit = $this->cfgStepprofit;
        $backprofit = $this->cfgBackprofit;
        $timelife = $this->cfgTimelife;
        $baseprofit = $this->cfgBaseprofit;

        $enterPrice = doubleval($event->{LAB_RESULT_ORDER_PRICE});

        $condition = $this->getMatchConfition($type, $phase);

        if ( $phase > 0 && ($event->{LAB_RESULT_STATUS} == LAB_RESULT_STATUS_ENTER_WAITTING || $event->{LAB_RESULT_STATUS} == LAB_RESULT_STATUS_PHASE_PENDING)){
            //Have to use params of old phase when new phase still not matched.
            $preCondition = $this->getMatchConfition($type, $phase-1);
            $stoploss = doubleval(get($preCondition['stoploss'], $this->cfgStoploss));
            $takeprofit = doubleval(get($preCondition['takeprofit'], $this->cfgTakeprofit));
            $baseprofit = doubleval(get($preCondition['baseprofit'], $this->cfgBaseprofit));
            $stepprofit = doubleval(get($preCondition['stepprofit'], $this->cfgStepprofit));
            $backprofit = doubleval(get($preCondition['backprofit'], $this->cfgBackprofit));
        }else{
            $stoploss = doubleval(get($condition['stoploss'], $this->cfgStoploss));
            $takeprofit = doubleval(get($condition['takeprofit'], $this->cfgTakeprofit));
            $baseprofit = doubleval(get($condition['baseprofit'], $this->cfgBaseprofit));
            $stepprofit = doubleval(get($condition['stepprofit'], $this->cfgStepprofit));
            $backprofit = doubleval(get($condition['backprofit'], $this->cfgBackprofit));
        }
        
        

        $enterStep = get($condition['enter_step'], 0);
        $enterRule = get($condition['enter_rule'], null);
        $enterCancle = get($condition['enter_cancle'], null);

        $market = false;

       
        if ($event->{LAB_RESULT_STATUS} == LAB_RESULT_STATUS_PENDING || $event->{LAB_RESULT_STATUS} == LAB_RESULT_STATUS_PHASE_PENDING) {

            $price = $this->getCheckPendingPrice($event, $closePrice, $high, $low, $openTime);
            $isMatched = false;

            if (!isset($this->maker)) {
                $matchedPrice = $closePrice;
                $this->maker = true;
            } else {
                $matchedPrice = $enterPrice;
            }

            $enterPriceSetting = get($condition['enter_price'], 'market');
            if ($enterPriceSetting == 'market') $market = true;

            if ($type == LAB_RESULT_TYPE_LONG) {

                if ($market || $price <= $enterPrice) {

                    $totalQty = doubleval($this->event->{LAB_RESULT_MATCHED_QTY}) + doubleval($this->event->{LAB_RESULT_ORDER_QTY});
                    $matchedPriceAvg = ($matchedPrice * doubleval($this->event->{LAB_RESULT_ORDER_QTY}) + doubleval($this->event->{LAB_RESULT_MATCHED_PRICE}) * doubleval($this->event->{LAB_RESULT_MATCHED_QTY})) / $totalQty;
                    
                    $this->eventModel->edit([
                        DATA_KEY => [[[LAB_RESULT_ID, '=', $event->{LAB_RESULT_ID}]]],
                        DATA_EDITOR => [
                            LAB_RESULT_STATUS => $phase == ($this->getMatchLeng($type) - 1) ? LAB_RESULT_STATUS_MATCHED : LAB_RESULT_STATUS_MATCHED_PART,
                            LAB_RESULT_MATCHED_PRICE => $matchedPriceAvg,
                            LAB_RESULT_MATCHED_TIME => $time,
                            LAB_RESULT_MATCHED_QTY => $totalQty,
                            LAB_RESULT_MATCHED_EMA5 => $ema5,
                            LAB_RESULT_LOW => $khung1m[0]->{LAB_CANDLE_1M_LOW},
                            LAB_RESULT_HIGH => $khung1m[0]->{LAB_CANDLE_1M_HIGH},
                            LAB_RESULT_BASEPROFIT => doubleval(get($condition['baseprofit'], $this->cfgBaseprofit))
                        ]
                    ]);

                    $isMatched = true;
                }
            } else if ($type == LAB_RESULT_TYPE_SHORT) {

                if ($market || $price >= $enterPrice) {

                    $totalQty = doubleval($this->event->{LAB_RESULT_MATCHED_QTY}) + doubleval($this->event->{LAB_RESULT_ORDER_QTY});
                    $matchedPriceAvg = ($matchedPrice * doubleval($this->event->{LAB_RESULT_ORDER_QTY}) + doubleval($this->event->{LAB_RESULT_MATCHED_PRICE}) * doubleval($this->event->{LAB_RESULT_MATCHED_QTY})) / $totalQty;

                    $this->eventModel->edit([
                        DATA_KEY => [[[LAB_RESULT_ID, '=', $event->{LAB_RESULT_ID}]]],
                        DATA_EDITOR => [
                            LAB_RESULT_STATUS => $phase == ($this->getMatchLeng($type) - 1) ? LAB_RESULT_STATUS_MATCHED : LAB_RESULT_STATUS_MATCHED_PART,
                            LAB_RESULT_MATCHED_PRICE => $matchedPriceAvg,
                            LAB_RESULT_MATCHED_QTY => $totalQty,
                            LAB_RESULT_MATCHED_TIME => $time,
                            LAB_RESULT_MATCHED_EMA5 => $ema5,
                            LAB_RESULT_BASEPROFIT => doubleval(get($condition['baseprofit'], $this->cfgBaseprofit))
                        ]
                    ]);
                    $isMatched = true;
                }
            }

            if (!$isMatched) {
                $startTime = doubleval($event->{LAB_RESULT_ORDER_TIME});
                if ((doubleval($time) - $startTime) >= $timelife * 60000) {
                    $this->eventModel->edit([
                        DATA_KEY => [[[LAB_RESULT_ID, '=', $event->{LAB_RESULT_ID}]]],
                        DATA_EDITOR => [
                            LAB_RESULT_STATUS => doubleval($event->{LAB_RESULT_MATCHED_QTY}) > 0 ? LAB_RESULT_STATUS_MATCHED_PART : LAB_RESULT_STATUS_CANCLE,
                            LAB_RESULT_PHASE => $phase > 0 ? $phase - 1 : $phase
                        ]
                    ]);
                    Telegram::send(TELE_ICON_CANCEL . " [" . $this->campaign->{LAB_CAMPAIGN_NAME} . "] #" . $this->symbol . " Cancel \n- Time:" . date("d/m/Y H:i:s", $time / 1000), TELE_SIMULATE);
                    return Reply::make(true, 'Pending Event', true);
                }
            } else {

                $this->maker = null;
                $this->maxOrderProfit = 0;
                $this->baseProfit = doubleval(get($condition['baseprofit'], $this->cfgBaseprofit));

                /** Log oder to oder table */
                $this->eventOrder->add([[
                    LAB_ORDER_ACTION => $this->event->{LAB_RESULT_ID},
                    LAB_ORDER_TIME => $time,
                    LAB_ORDER_PRICE => $matchedPrice,
                    LAB_ORDER_SYMBOL => $this->symbol,
                    LAB_ORDER_QTY =>  doubleval($this->event->{LAB_RESULT_ORDER_QTY}),
                    LAB_ORDER_TYPE => $type,
                    LAB_ORDER_PHASE => $phase,
                ]]);

                Telegram::send(
                    TELE_ICON_MATCHED . " [" . $this->campaign->{LAB_CAMPAIGN_NAME} . "] #" . $this->symbol . " Matched"
                        . " \n- Time:" . date("d/m/Y H:i:s", $time / 1000)
                        . "\n- Matched Price:" . $matchedPrice,
                    TELE_SIMULATE
                );

                return Reply::make(true, 'Pending Event', true);
            }
        }

        if (doubleval($event->{LAB_RESULT_MATCHED_QTY}) > 0 && $event->{LAB_RESULT_STATUS} != LAB_STATUS_STOP_PENDING) {

            $matchedPrice = doubleval($event->{LAB_RESULT_MATCHED_PRICE});
            $matchedEma5 = doubleval($event->{LAB_RESULT_MATCHED_EMA5});

            $price = $this->getCheckMatchedPrice($event, $closePrice, $high, $low, $openTime);

            if ($type == LAB_TYPE_LONG) {

                $maxProfitReal = ($price['max'] - $matchedPrice) * 100 / $matchedPrice;
                $minProfitReal = ($price['min'] - $matchedPrice) * 100 / $matchedPrice;
                $profitReal = ($closePrice - $matchedPrice) * 100 / $matchedPrice;

                if ($this->cfgBackprofitBaseon == 'close') {

                    $maxProfit = $maxProfitReal;
                    $minProfit = $minProfitReal;
                    $profit = $profitReal;
                } else {
                    $profit = ($ema5 - $matchedEma5) * 100 / $matchedPrice;
                    $maxProfit = $profit;
                    $minProfit = $profit;
                }
            } else {

                $maxProfitReal = ($matchedPrice - $price['min']) * 100 / $matchedPrice;
                $minProfitReal = ($matchedPrice - $price['max']) * 100 / $matchedPrice;
                $profitReal = ($matchedPrice - $closePrice) * 100 / $matchedPrice;

                if ($this->cfgBackprofitBaseon == 'close') {

                    $maxProfit = $maxProfitReal;
                    $minProfit = $minProfitReal;
                    $profit = $profitReal;
                } else {
                    $profit =  ($matchedEma5 - $ema5) * 100 / $matchedPrice;
                    $maxProfit = $profit;
                    $minProfit = $profit;
                }
            }

            $this->event->{LAB_RESULT_PROFIT} = $profitReal;

            $editData = [];

            $finished = false;

            $isTakeprofit = false;

            // Profit Rule for stop

            if (doubleval($khung1m[0]->{LAB_CANDLE_1M_CLOSE_TIME}) - doubleval($khung1m[1]->{LAB_CANDLE_1M_CLOSE_TIME}) > 120000) {
                $editData = [
                    LAB_RESULT_STATUS => LAB_RESULT_STATUS_STOP_PENDING,
                    LAB_RESULT_PARAMS => 'Package lost',
                ];
                $finished = true;
            }

            if (!$finished) {

                if ($maxProfitReal >= $takeprofit) {
                    $editData = [
                        LAB_RESULT_STATUS => LAB_RESULT_STATUS_STOP_PENDING,
                        LAB_RESULT_PARAMS => 'Profit >= ' . $takeprofit
                    ];
                    $finished = true;
                    $isTakeprofit = true;
                }

                if ($minProfitReal <= -$stoploss) {

                    $editData = [
                        LAB_RESULT_STATUS => LAB_RESULT_STATUS_STOP_PENDING,
                        LAB_RESULT_PARAMS => 'Profit <= -' . $stoploss
                    ];
                    $finished = true;
                    $isTakeprofit = true;
                }
            }

            if (!$finished) {

                if ($maxProfit > $this->maxOrderProfit) {
                    $this->maxOrderProfit = $maxProfit;
                }

                if ($stepprofit > 0 && $this->maxOrderProfit > ($this->baseProfit + $stepprofit)) {
                    $this->baseProfit = $this->baseProfit + floor(($this->maxOrderProfit - $this->baseProfit) / $stepprofit) * $stepprofit;
                }

                if ($this->baseProfit > 0 && $this->maxOrderProfit > $this->baseProfit && $profit < $this->baseProfit - $backprofit) {
                    $editData = [
                        LAB_RESULT_STATUS => LAB_RESULT_STATUS_STOP_PENDING,
                        LAB_RESULT_PARAMS => 'Profit <= Base profit (' . $this->baseProfit . ') - back Step Profit('.$backprofit.')'
                    ];


                    $finished = true;
                }
            }

            // Price Rule for stop

            if (!$finished) {

                if ($type == LAB_RESULT_TYPE_LONG) {

                    if (isset($this->cfgStrategy['long'])) {
                        if (isset($this->cfgStrategy['long']['stop'])) {
                            $condition = $this->cfgStrategy['long']['stop'];
                            $result = $this->compareOr($condition);
                            if (!$result['result']) return $result;
                            if ($result['data']) {
                                $editData = [
                                    LAB_RESULT_STATUS => LAB_RESULT_STATUS_STOP_PENDING,
                                    LAB_RESULT_PARAMS => $result['message'],
                                ];
                                $finished = true;
                            }
                        }
                    }
                } else if ($type == LAB_RESULT_TYPE_SHORT) {

                    if (isset($this->cfgStrategy['short'])) {
                        if (isset($this->cfgStrategy['short']['stop'])) {
                            $condition = $this->cfgStrategy['short']['stop'];
                            $result = $this->compareOr($condition);
                            if (!$result['result']) return $result;
                            if ($result['data']) {
                                $editData = [
                                    LAB_RESULT_STATUS => LAB_RESULT_STATUS_STOP_PENDING,
                                    LAB_RESULT_PARAMS => $result['message'],
                                ];
                                $finished = true;
                            }
                        }
                    }
                }
            }


            /** Update profit each 20 events */
            if(!isset($this->updateProfitCount)) $this->updateProfitCount = 0;
            if($this->updateProfitCount >= 20){
                $this->updateProfitCount = 0;
                $editData[LAB_RESULT_BASEPROFIT] = $this->baseProfit;
                $editData[LAB_RESULT_PROFIT] = $profitReal;

                $this->eventModel->edit([
                    DATA_KEY => [[[LAB_RESULT_ID, '=', $event->{LAB_RESULT_ID}]]],
                    DATA_EDITOR => $editData
                ]);
            }else{
                $this->updateProfitCount ++;
            }
            

            
            /** Logging if is enabled */
            if (isset($this->params[LAB_CAMPAIGN_PARAMS_LOG_ORDER]) && $this->params[LAB_CAMPAIGN_PARAMS_LOG_ORDER] == 1) {
                $this->eventLog->add([[
                    LAB_ELOG_TIME => $time,
                    LAB_ELOG_CAMPAIGN => $this->campaign->{LAB_CAMPAIGN_ID},
                    LAB_ELOG_SYMBOL => $this->symbol,
                    LAB_ELOG_MATCHED => $type,
                    LAB_ELOG_CHART => $khung1m[0]->{LAB_CANDLE_1M_OPEN_TIME},
                    LAB_ELOG_RESULT => json_encode([
                        'Status' => $finished ? 'Stop Pending' : 'Matched',
                    ]),
                    LAB_ELOG_MAXPROFIT => $maxProfitReal,
                    LAB_ELOG_MINPROFIT => $minProfitReal,
                    LAB_ELOG_PROFIT => $profit,
                    LAB_ELOG_BASEPROFIT => $this->baseProfit,
                    LAB_ELOG_STATUS => $finished ? 'Stop Pending' : 'Matched',
                    LAB_ELOG_BASE => json_encode($this->data)
                ]]);
            }

            if ($finished) {

                $this->labPendingStop = 0;

                if ($isTakeprofit) {
                    $this->labPendingStop = 1;
                } else {
                    $this->labPendingStop = 0;
                }

                $editData[LAB_RESULT_BASEPROFIT] = $this->baseProfit;
                $editData[LAB_RESULT_PROFIT] = $profitReal;

                $this->eventModel->edit([
                    DATA_KEY => [[[LAB_RESULT_ID, '=', $event->{LAB_RESULT_ID}]]],
                    DATA_EDITOR => $editData
                ]);

                Telegram::send(TELE_ICON_STOP . " [" . $this->campaign->{LAB_CAMPAIGN_NAME} . "] #" . $this->symbol 
                . " Stop \n- Reason: " . $editData[LAB_RESULT_PARAMS], TELE_SIMULATE);

                return Reply::make(true, 'Pending Event', true);
            }
        }

        if ($event->{LAB_RESULT_STATUS} == LAB_RESULT_STATUS_STOP_PENDING) {
            if ($this->labPendingStop < 1) {
                $this->labPendingStop++;
                return Reply::make(true, 'Pending Event', true);
            }

            $matchedPrice = doubleval($event->{LAB_RESULT_MATCHED_PRICE});

            // $price = $this->getCheckPendingPrice($event, $closePrice, $high, $low, $openTime);
            $price = $closePrice;

            if ($type == LAB_RESULT_TYPE_LONG) {
                $profit = ($price - $matchedPrice) * 100 / $matchedPrice;
            } else {
                $profit = - ($price - $matchedPrice) * 100 / $matchedPrice;
            }

            $posProfit = $profit - 0.08;
            $PNL = $posProfit * ($matchedPrice * doubleval($this->event->{LAB_RESULT_MATCHED_QTY}))/100;
            $realProfit =  $PNL*100/100;

            $editData = [
                LAB_RESULT_PENDING => '0',
                LAB_RESULT_STATUS => $posProfit > 0 ? LAB_RESULT_STATUS_TAKEPROFIT : LAB_RESULT_STATUS_STOPLOSS,
                LAB_RESULT_SELL_PRICE => $price,
                LAB_RESULT_SELL_TIME => $time,
                LAB_RESULT_PROFIT => $profit,
                LAB_RESULT_EVENT_PROFIT => $posProfit,
                LAB_RESULT_REAL_PROFIT => $realProfit,
            ];

            $this->eventModel->edit([
                DATA_KEY => [[[LAB_RESULT_ID, '=', $event->{LAB_RESULT_ID}]]],
                DATA_EDITOR => $editData
            ]);

            $this->labPendingTime = $time;

            if (isset($this->params[LAB_CAMPAIGN_PARAMS_LOG_ORDER]) && $this->params[LAB_CAMPAIGN_PARAMS_LOG_ORDER] == 1) {
                $this->eventLog->add([[

                    LAB_ELOG_TIME => $time,
                    LAB_ELOG_CAMPAIGN => $this->campaign->{LAB_CAMPAIGN_ID},
                    LAB_ELOG_SYMBOL => $this->symbol,
                    LAB_ELOG_MATCHED => $type,
                    LAB_ELOG_CHART => $khung1m[0]->{LAB_CANDLE_1M_OPEN_TIME},
                    LAB_ELOG_RESULT => json_encode([
                        'Status' => $posProfit > 0 ? 'Take profit' : 'Stoploss',
                    ]),
                    LAB_ELOG_PROFIT => $profit,
                    LAB_ELOG_BASE => json_encode($this->data)
                ]]);
            }

            Telegram::send(($posProfit > 0 ? TELE_ICON_TAKEPROFIT : TELE_ICON_STOPLOSS) . " [" . $this->campaign->{LAB_CAMPAIGN_NAME} . "] #" . $this->symbol . " " . ($posProfit > 0 ? "Take Profit" : "Stoploss")
                    . "\n- Type: " . ($type == LAB_TYPE_LONG ? "Long" : "Short")
                    . "\n- Time: " . date("d/m/Y H:i:s", $time / 1000)
                    . "\n- Price: " . $price
                    . "\n- Profit: " . $profit
                    . "\n- Event Profit: " . ($posProfit)
                    . "\n- Real Profit: " . ($realProfit),
                TELE_SIMULATE
            );

            return Reply::make(true, 'No Pending Event', false);
        }

        if ($event->{LAB_RESULT_STATUS} == LAB_RESULT_STATUS_ENTER_WAITTING) {

            $isMakeOrder = false;

            if ($type == LAB_RESULT_TYPE_LONG) {

                if ($enterRule == null) {
                    if ($this->enterBase > $closePrice) {
                        $this->enterBase = $closePrice;
                    } else {

                        $percentChange = ($closePrice - $this->enterBase) * 100 / $closePrice;

                        if ($percentChange > $enterStep) {
                            $isMakeOrder = true;
                        }
                    }
                } else {
                    $result = $this->compareOr($enterRule);
                    if (!$result['result']) return $result;
                    $isMakeOrder = $result['data'];
                }
            } else if ($type == LAB_RESULT_TYPE_SHORT) {

                if ($enterRule == null) {
                    if ($this->enterBase < $closePrice) {
                        $this->enterBase = $closePrice;
                    } else {
                        $percentChange = ($this->enterBase - $closePrice) * 100 / $closePrice;

                        if ($percentChange > $enterStep) {
                            $isMakeOrder = true;
                        }
                    }
                } else {
                    $result = $this->compareOr($enterRule);
                    if (!$result['result']) return $result;
                    $isMakeOrder = $result['data'];
                }
            }

            if ($isMakeOrder) {

                $this->makeOrder($event, $closePrice , $phase, $time);
            } else if ($enterCancle != null) {

                $result = $this->compareOr($enterCancle);
                if (!$result['result']) return $result;
                if ($result['data']) {
                    $this->eventModel->edit([
                        DATA_KEY => [[[LAB_RESULT_ID, '=', $event->{LAB_RESULT_ID}]]],
                        DATA_EDITOR => [
                            LAB_RESULT_STATUS => doubleval($event->{LAB_RESULT_MATCHED_QTY}) > 0 ? LAB_RESULT_STATUS_MATCHED_PART : LAB_RESULT_STATUS_CANCLE,
                            LAB_RESULT_PENDING => doubleval($event->{LAB_RESULT_MATCHED_QTY}) > 0 ? 1 : 0,
                        ]
                    ]);
                    Telegram::send(TELE_ICON_CANCEL . " [" .  $this->campaign->{LAB_CAMPAIGN_NAME} . "] #" . $this->symbol . " Cancel waitting order"
                        . " \n- Time:" . date("d/m/Y H:i:s", $time / 1000), TELE_SIMULATE);
                    
                    return Reply::make(true, 'Pending Event', true);
                }
            }
        }
        
        if ($event->{LAB_RESULT_STATUS} == LAB_RESULT_STATUS_MATCHED_PART) {
            
            if ($phase < ($this->getMatchLeng($type) - 1)) {
                $nextCondition = $this->getMatchConfition($type, $phase + 1);

                $checkResult = $this->compareOr($nextCondition['condition']);
                if (!$checkResult['result']) return $checkResult;
                if ($checkResult['data']) {

                    $enterStep = get($nextCondition['enter_step'], 0);
                    $enterRule = get($nextCondition['enter_rule'], null);

                    $closePrice = doubleval($khung1m[0]->{LAB_CANDLE_1M_CLOSE});

                    $baseonData = $this->orderData;
                    $baseonData[$phase + 1] = $this->data;

                    $addData = [
                        LAB_RESULT_ENTER_TIME => $time,
                        LAB_RESULT_ENTER_PRICE => $closePrice,
                        LAB_RESULT_LOW => $khung1m[0]->{LAB_CANDLE_1M_LOW},
                        LAB_RESULT_HIGH => $khung1m[0]->{LAB_CANDLE_1M_HIGH},
                        LAB_RESULT_BASE => json_encode($baseonData),
                        LAB_RESULT_STATUS => LAB_RESULT_STATUS_ENTER_WAITTING,
                        LAB_RESULT_PHASE => $phase + 1
                    ];

                    $this->eventModel->edit([
                        DATA_KEY => [[[LAB_RESULT_ID, '=', $event->{LAB_RESULT_ID}]]],
                        DATA_EDITOR => $addData
                    ]);

                    if ($enterStep <= 0 && $enterRule === null) {
                        $this->makeOrder($event, $closePrice, $phase + 1, $time);
                    } else {
                        $this->enterBase = $closePrice;
                        Telegram::send(
                            TELE_ICON_WAITTING . " [" .  $this->campaign->{LAB_CAMPAIGN_NAME} . "] #" . $this->symbol  . " Waitting for " . ($type == LAB_RESULT_TYPE_LONG ? 'Long' : 'Short') . " Order Pharse " . (intval($phase) + 1)
                                . "\n-Time: " . date("d/m/Y H:i:s", $time / 1000)
                                . " \n- Close Price: " . $closePrice,
                            TELE_SIMULATE
                        );
                    }
                }
            } else {
                $this->eventModel->edit([
                    DATA_KEY => [[[LAB_RESULT_ID, '=', $event->{LAB_RESULT_ID}]]],
                    DATA_EDITOR => [
                        LAB_RESULT_STATUS => LAB_RESULT_STATUS_MATCHED,
                    ]
                ]);
            }
        }

       

        return Reply::make(true, 'Pending Event', true);
    }


    private function getMatchConfition($type, $phase)
    {
        if($type == LAB_RESULT_TYPE_LONG) $type = 'long';
        else if($type == LAB_RESULT_TYPE_SHORT) $type = 'short';
        $straType = $this->cfgStrategy[$type];
        if(isset($straType['disable']) && $straType['disable']) return null;
        return $straType['match'][doubleval($phase)];
    }

    private function getMatchLeng($type)
    {
        if($type == LAB_RESULT_TYPE_LONG) $type = 'long';
        else if($type == LAB_RESULT_TYPE_SHORT) $type = 'short';
        return count($this->cfgStrategy[$type]['match']);
    }


    private function makeOrder($action, $closePrice, $phase, $time)
    {
        $type = $action->{LAB_RESULT_TYPE};
        $condition = $this->getMatchConfition($type, $phase);

        $enterPriceSetting = get($condition['enter_price'], 'market');
        $margin = get($condition['margin'], 1);
        if (is_numeric($enterPriceSetting)) {
            $enterPrice = $closePrice * $enterPriceSetting / 100;
        } else {
            $enterPrice = $closePrice;
        }

        $qty = get($condition['enter_package'], 100)/$closePrice;
        $qty = $qty * $margin;

        $this->eventModel->edit(
            [
                DATA_KEY => [[[LAB_RESULT_ID, '=', $action->{LAB_RESULT_ID}]]],
                DATA_EDITOR => [
                    LAB_RESULT_ORDER_PRICE => $enterPrice,
                    LAB_RESULT_ORDER_TIME => $time,
                    LAB_RESULT_ORDER_QTY => $qty,
                    LAB_RESULT_STATUS => $phase == 0 ? LAB_RESULT_STATUS_PENDING : LAB_RESULT_STATUS_PHASE_PENDING,
                    LAB_RESULT_LOW => $this->data[$this->symbol]['1m'][0]->{LAB_CANDLE_1M_LOW},
                    LAB_RESULT_HIGH => $this->data[$this->symbol]['1m'][0]->{LAB_CANDLE_1M_HIGH},
                ]
            ]
        );
        Telegram::send(
            ($type == LAB_RESULT_TYPE_SHORT ? TELE_ICON_SHORT : TELE_ICON_LONG) . " [" . $this->campaign->{LAB_CAMPAIGN_NAME} . "] #" . $this->symbol . " " . ($type == LAB_RESULT_TYPE_SHORT ? 'Short' : 'Long') . " Order Pharse $phase "
                . "\n- Time:" . date("d/m/Y H:i:s", $time / 1000)
                . "\n- Close Price:" . $closePrice
                . "\n- Enter Price:" . $enterPrice,
            TELE_SIMULATE
        );
    }

    private function getCheckPendingPrice($event, $price, $high, $low, $open_time)
    {
        $type = $event->{LAB_RESULT_TYPE};
        if ($type == LAB_RESULT_TYPE_LONG) {
            if ($open_time > $event->{LAB_RESULT_ORDER_TIME}) return $low;
            if ($low != $event->{LAB_RESULT_LOW}) return $low;
        } else if ($type == LAB_RESULT_TYPE_SHORT) {
            if ($open_time > $event->{LAB_RESULT_ORDER_TIME}) return $high;
            if ($high != $event->{LAB_RESULT_HIGH}) return $high;
        }
        return $price;
    }

    private function getCheckMatchedPrice($event, $price, $high, $low, $open_time)
    {

        if ($open_time > $event->{LAB_RESULT_MATCHED_TIME}) return ['max' => $high, 'min' => $low];
        $max = $price;
        $min = $price;
        if ($high != $event->{LAB_RESULT_HIGH}) $max = $high;
        if ($low != $event->{LAB_RESULT_LOW}) $min = $low;

        return ['max' => $max, 'min' => $min];
    }
}

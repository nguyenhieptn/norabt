<?php

namespace App\Event\Testnet;

use App\Helpers\Admin\Telegram;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use App\Event\EventFunc;
use App\Helpers\Request\Query;
use Exception;

class EventCheck
{
    use EventFunc;

    function __construct($campaignId)
    {

        try {
            //code...
            date_default_timezone_set('Asia/Ho_Chi_Minh');
            
            $this->eventModel = Models::get('Admin/Testnet_results');
            $this->eventLogModel = Models::get('Admin/Testnet_event_logs');
            $this->StrategyModel = Models::get('Admin/Strategies');
            $this->campaignModel = Models::get('Admin/Testnet_campaign');
            $this->eventOrder = Models::get('Admin/Testnet_order');

            $this->altsCoinModel = Models::get('Admin/Change_24h');
            $this->enterBaseModel = Models::get('Admin/Testnet_enterbase');
            $this->profitBaseModel = Models::get('Admin/Testnet_profitbase');

            $this->watchlistModel = Models::get('Admin/Watchlist');
            $this->testnetEventsModel = Models::get('Admin/Testnet_events');

            $this->volatilityModel = Models::get('Admin/Volatility');
            $this->volatilityData = [
                'data' => null,
                'time' => 0,
            ];

            $campaign = $this->campaignModel->read([[[TESTNET_ID, '=', $campaignId]]]);
            if (!$campaign['result'] || !isset($campaign['data'][0])) {
                throw new Exception('No Campaign ID ' . $campaignId);
            }
            $campaign = $campaign['data'][0];
            $this->campaign = $campaign;
            $this->symbol = $campaign->{TESTNET_SYMBOL};

            $params = $campaign->{TESTNET_PARAM};
            $params = json_decode($params, true);
            if (!$params) $params = [];
            $this->params = $params;


            $watchlist = $this->watchlistModel->read([[[WL_SYMBOL, '=', $this->symbol]]]);
            if (!$watchlist['result'] || !isset($watchlist['data'][0])) {
                throw new Exception('No watchlist symbol ');
            }
            $this->watchlist = $watchlist['data'][0];

            $strategyId = $campaign->{TESTNET_STRATEGY};
            $strategyData = $this->StrategyModel->read([[[STRATEGY_ID, '=', $strategyId]]]);
            if (!$strategyData['result']) Reply::finish($strategyData);
            if (!isset($strategyData['data'][0])) Reply::finish(false, 'Can not find any Strategy');

            $strategyDB = $strategyData['data'][0];
            $strategyData = $strategyDB->{STRATEGY_CONTENT};
            $strategyData = json_decode($strategyData, true);
            if ($strategyData == null) Reply::finish(false, 'Please define Strategy');

            $this->cfgStrategy = $strategyData;
            $this->cfgStoploss = get($strategyDB->{STRATEGY_STOPLOSS}, 0.2);
            $this->cfgTakeprofit = get($strategyDB->{STRATEGY_TAKEPROFIT}, 1);
            $this->cfgInterval = get($strategyDB->{STRATEGY_INTERVAL}, 6);
            $this->cfgTimelife = get($strategyDB->{STRATEGY_TIMELIFE}, 6);
            $this->cfgBaseprofit = get($strategyDB->{STRATEGY_BASEPROFIT}, $this->cfgTakeprofit);
            $this->cfgStepprofit = get($strategyDB->{STRATEGY_STEPPROFIT}, 0);
            $this->cfgBackprofit = get($strategyDB->{STRATEGY_BACKPROFIT}, 0);
            $this->cfgMargin = get($strategyDB->{STRATEGY_MARGIN}, 1);
            $this->cfgBackprofitBaseon = get($strategyDB->{STRATEGY_BASEPROFIT_BASEON}, 'close');


            $this->baseProfit = null;
            $this->maxOrderProfit = 0;

            $this->event = null;

            $this->labPendingTime = 0; // save the time when event finish. 
            $this->labPendingStop = 0; // stop event skip, if > 1 then stop

            $this->packageLost = 0;

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
                '1d' => 24 * 60 * 60 * 1000,
                '1w' => 7 * 24 * 60 * 60 * 1000,
            ];

            // using for enter step
            $this->enterBase = null;

            // using for release step
            $this->releaseBase = null;

            // marking of which params phase is using
            $this->matchedParamsPhase = null;


            // allow_negative_price_rate
            $this->allowNegativeWaittingPriceLong = get($this->cfgStrategy['long']['allow_negative_price_rate'], true);
            $this->allowNegativeWaittingPriceShort = get($this->cfgStrategy['short']['allow_negative_price_rate'], true);


            // max trades open
            $this->maxTradesOpen = get($this->cfgStrategy['max_open_trades'], 0);

            //side long or short both
            $this->side = get($campaign->{TESTNET_SIDE}, 'BOTH');

            //Telegram bot

            $this->teleBot = get($campaign->{TESTNET_TELE_BOT}, TELE_BOT_DEFAULT);
            $this->teleGrNotice = get($campaign->{TESTNET_TELE_GR_NOTICE}, null);
            $this->teleGrError = get($campaign->{TESTNET_TELE_GR_ERROR}, TELE_TEST_ERROR);
            $this->teleGrSummary = get($campaign->{TESTNET_TELE_GR_SUMMARY}, null);
            if ($this->teleGrSummary != null) $this->teleGrSummary = explode(',', $this->teleGrSummary);


            $this->getPrecision('');


        } catch (\Exception $th) {
            $ms = $th->getFile() . " " . $th->getLine() . " " . $th->getMessage();
            echo $ms . "\n";
            Telegram::send(TELE_ICON_ERROR . $ms, get($this->teleGrError, TELE_TEST_ERROR), get($this->teleBot, TELE_BOT_DEFAULT));
            $pid = $this->stopService($campaignId);
            pcntl_waitpid($pid, $status);
            
        }
    }


    private function getData($time)
    {
        foreach ($this->needData as $symbol => $frames) {
            if (!isset($this->data[$symbol])) $this->data[$symbol] = [];
            foreach ($frames as $frame => $maxIndex) {

                $maxIndex = -$maxIndex;

                $columnName = [
                    'CANDLE_ID' => "candle_" . $frame . "_id",
                    'CANDLE_SYMBOL' => "candle_" . $frame . "_symbol",
                    'CANDLE_OPEN_TIME' => "candle_" . $frame . "_open_time",
                    'CANDLE_CLOSE_TIME' => "candle_" . $frame . "_close_time",
                    'CANDLE_OPEN' => "candle_" . $frame . "_open",
                    'CANDLE_CLOSE' => "candle_" . $frame . "_close",
                    'CANDLE_HIGH' => "candle_" . $frame . "_high",
                    'CANDLE_LOW' => "candle_" . $frame . "_low",
                    'CANDLE_TRADES' => "candle_" . $frame . "_trades",
                    'CANDLE_VOLUME' => "candle_" . $frame . "_volume",
                    'CANDLE_EMA5' => "candle_" . $frame . "_ema5",
                    'CANDLE_EMA9' => "candle_" . $frame . "_ema9",
                    'CANDLE_EMA12' => "candle_" . $frame . "_ema12",
                    'CANDLE_EMA13' => "candle_" . $frame . "_ema13",
                    'CANDLE_EMA26' => "candle_" . $frame . "_ema26",
                    'CANDLE_MACD' => "candle_" . $frame . "_macd",
                    'CANDLE_SIGNAL' => "candle_" . $frame . "_signal",
                    'CANDLE_HISTOGRAM' => "candle_" . $frame . "_histogram",
                ];

                if (!isset($this->data[$symbol][$frame])) $this->data[$symbol][$frame] = [];

                if (!isset($this->models[$frame])) $this->models[$frame] = Models::get('Admin/Candle_' . $frame);

                $frame0 = $this->models[$frame]->read([[
                    [$columnName['CANDLE_SYMBOL'], '=', $symbol],
                    [$columnName['CANDLE_CLOSE_TIME'], '>', $time - 60 * 1000]
                ]], function ($db) use ($columnName) {
                    $db->orderBy($columnName['CANDLE_CLOSE_TIME'], 'DESC')->limit(1);
                });
                if (!$frame0['result']) return $frame0;
                if (!isset($frame0['data'][0])) return Reply::make(false, 'Can not get data ' . $symbol . ' frame 0');
                $frame0 = $frame0['data'][0];

                $needRefresh = true;
                if (
                    isset($this->data[$symbol][$frame][0])
                    && $this->data[$symbol][$frame][0]->{$columnName['CANDLE_CLOSE_TIME']} == $frame0->{$columnName['CANDLE_CLOSE_TIME']}
                ) {
                    $needRefresh = false;
                    $this->data[$symbol][$frame][0] = $frame0;
                } else {
                    $this->data[$symbol][$frame] = [$frame0];
                }

                if ($needRefresh && $maxIndex > 0) {
                    $frames = $this->models[$frame]->read([[
                        [$columnName['CANDLE_SYMBOL'], '=', $symbol],
                        [$columnName['CANDLE_CLOSE_TIME'], '<', $frame0->{$columnName['CANDLE_CLOSE_TIME']}],
                        [$columnName['CANDLE_CLOSE_TIME'], '>', $frame0->{$columnName['CANDLE_CLOSE_TIME']} - (($maxIndex + 2) * $this->periodFrame[$frame])]

                    ]], function ($db) use ($columnName, $maxIndex) {
                        $db->orderBy($columnName['CANDLE_CLOSE_TIME'], 'DESC')->limit($maxIndex);
                    });

                    if (!$frames['result']) return $frames;

                    foreach ($frames['data'] as $data) {
                        $this->data[$symbol][$frame][] = $data;
                    }
                }

                if (count($this->data[$symbol][$frame]) < $maxIndex + 1) return Reply::make(false, "Can not get enough $maxIndex data " . $symbol . ' ' . $frame);
            }
        }

        // if (!isset($this->altsCoinData) || ($time - doubleval($this->altsCoinData->{CHANGE24H_TIME})) > 300000) {
        //     $altCoinData = $this->altsCoinModel->read([[[CHANGE24H_TIME, '<=', $time], [CHANGE24H_TIME, '>', $time - 600000]]], function ($db) {
        //         $db->orderBy(CHANGE24H_TIME, 'DESC')->limit(1);
        //     });

        //     if (!$altCoinData['result']) return $altCoinData;
        //     if (!isset($altCoinData['data'][0])) return Reply::make(false, 'No Alts Coin Data at ' . date("H:i:s d/m/Y", $time / 1000));
        //     $this->altsCoinData = $altCoinData['data'][0];
        // }

        return Reply::make(true, 'success');
    }


    private function getVolatility(){
        $crTime = time();
        if($this->volatilityData['data'] == null || ($crTime - $this->volatilityData['time']) > 30){
            $data = $this->volatilityModel->read([[[VOLATILITY_SYMBOL, '=', $this->symbol]]]);
            if(!$data['result']) return $data;
            if(!isset($data['data'][0])) return Reply::make(true, 'Can not find any volatility data', null);
            $this->volatilityData['data'] = $data['data'][0];
            $this->volatilityData['time'] = $crTime;
        }

        return Reply::make(true, 'success', $this->volatilityData['data']); 
    }


    private function caculateElement($struct, $dynamicIndex = null)
    {

        if (is_numeric($struct)) return Reply::make(true, $struct, $struct);

        if (is_string($struct)) {
            if ($struct == 'order_time') {
                if ($this->event == null) return Reply::make(false, 'No Event');
                return Reply::make(true, $struct, doubleval($this->event->{TESTNET_RESULT_MATCHED_TIME}));
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

            if ($index == 'dynamic') {
                $index = $dynamicIndex;
            } else {
                $index = -intval($index);
            }

            if ($percent != 100) {
                $des = "$symbol Frame $percent% $frame $column($index)";
            } else {
                $des = "$symbol Frame $frame $column($index)";
            }

            if ($frame === null || $index === null || $column === null || $symbol === null)
                return Reply::make(false, 'Please define symbol, frame, column and index ' . $des . json_encode($struct));

            $column = 'candle_' . $frame . '_' . $column;

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
            $column = 'testnet_result_' . $column;
            $percent = doubleval(get($struct['percent'], 100));
            $value = $this->event->{$column};
            if($percent != 100){
                $des = "Event $percent% $column";
            }else{
                $des = "Event $column";
            }
            
            if (is_numeric($value))
                return Reply::make(true, $des, doubleval($value) * $percent / 100);
            return Reply::make(true, $des, $value);
        }

        if ($type == 'altscoin') {
            $column = get($struct['column'], null);
            $column = 'change24h_' . $column;
            if (!isset($this->altsCoinData) || !isset($this->altsCoinData->{$column})) return Reply::make(false, 'Can not get data ' . json_encode($struct));
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

            if ($index == 'dynamic') {
                $index = $dynamicIndex;
            } else {
                $index = -intval($index);
            }
            $column1 = 'candle_' . $frame . '_' . $column1;
            $column2 = 'candle_' . $frame . '_' . $column2;

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

                if (is_array($stop)) {
                    $isStop = $this->compareOr($stop, $i);
                    if (!$isStop['result']) return $isStop;


                    if ($isStop['data']) {
                        // print_r($isStop);
                        echo date("H:i:s d/m/Y", time()) . "_stop_" . $needStop . "_" . $cross . "\n";
                        return Reply::make(true, $des, $cross);
                    }
                }

                if (($newValue1 - $newValue2) * ($oldValue1 - $oldValue2) <= 0) {
                    $cross++;
                    $needStop = 0;
                } else {

                    if (is_numeric($thresold)) {
                        $needStop++;
                        if ($needStop >= $thresold) {
                            echo date("H:i:s d/m/Y", time()) . "_thresold_" . $needStop . "_" . $cross . "\n";
                            return Reply::make(true, $des, $cross);
                        }
                    }
                }
            }

            // echo date("H:i:s d/m/Y", $this->data[$this->symbol]['1m'][0]->{CANDLE_1M_TIME} / 1000) ."_". $cross . "\n";

            return Reply::make(true, $des, $cross);
        }

        if($type == 'calculate'){
            $number1 = get($struct['number_1'], null);
            $number2 = get($struct['number_2'], null);
            $logic = get($struct['logic'], null);

            if ($number1 === null || $number2 === null || $logic === null)
                return Reply::make(false, 'Please define number_1, number_2, logic' . json_encode($struct));
            $num1 = $this->caculateElement($number1);
            if(!$num1['result']) return $num1;
            $num2 = $this->caculateElement($number2);
            if(!$num2['result']) return $num2;

            $des1 = $num1['message'];
            $des2 = $num2['message'];
            $des = $des1 . $logic . $des2;

            $result = null;
            if($logic == '+') $result = doubleval($num1['data']) + doubleval($num2['data']);
            if($logic == '-') $result = doubleval($num1['data']) - doubleval($num2['data']);
            if($logic == '*') $result = doubleval($num1['data']) * doubleval($num2['data']);
            if($logic == '/') $result = doubleval($num1['data']) / doubleval($num2['data']);
            if($result === null) return Reply::make(false, 'Does not support logic ' . $logic);

            return Reply::make(true, $des, $result);

        }

        if($type == 'volatility'){
            $frame = get($struct['frame'], null);
            $volatility = get($struct['volatility'], null);
            $avg = get($struct['avg'], null);
            $object = get($struct['object'], null);
            if($frame == null || $volatility == null || $avg == null || $object == null) return Reply::make(false, 'Please define Frame, Volatility, Avg, Object');
            $colName = 'volatility_' . $frame . "_" . $volatility . "_avg" . $avg . "_" . $object;
            $volData = $this->getVolatility();
            $des = "Volatility $frame $volatility avg in $avg $object";
            if(!$volData['result']) return $volData;
            if($volData['data'] === null) return Reply::make(true, $des, null);
            $volData = $volData['data'];
            if(isset($volData->{$colName})){
                return Reply::make(true, $des, doubleval($volData->{$colName})); 
            }else{
                Reply::make(false, 'Can not calculate ' . $des);
            }
        }

        Reply::make(false, 'Can not caculate ' . json_encode($struct));
    }

    public function stopService($campaignId)
    {
        $this->campaignModel->edit([
            DATA_KEY => [[[TESTNET_ID, '=', $campaignId]]],
            DATA_EDITOR => [TESTNET_STOP_TIME => time()],
        ]);
        $pid = pcntl_fork();
        if ($pid == -1) {
            echo "Can not fork";
            return;
        } else if ($pid == 0) {
            sleep(5);
            exec('sudo systemctl stop testnet_start@' . $campaignId . ' 2>&1 > /dev/null &');
            die();
        }
        return $pid;
    }


    public function check()
    {
        while (true) {

            usleep(250000);


            if ($this->packageLost > 1000) {
                $this->packageLost = 0;
                // $this->stopService($this->campaign->{TESTNET_ID});
                Telegram::send(TELE_ICON_ERROR . " [ERROR] #" . $this->campaign->{TESTNET_NAME} . " package loss", $this->teleGrError, $this->teleBot);
            }

            $time_start = microtime(true);
            $time = round($time_start * 1000);

            $result = $this->getData($time);
            if (!$result['result']) {
                echo $result['message'] . "\n";
                $this->packageLost++;
                continue;
            }

            // echo "Event check get Data " . $this->symbol . " Excute time " . (microtime(true) - $time_start) . " second\n";
            if (
                doubleval($this->data[$this->symbol]['1h'][0]->{CANDLE_1H_CLOSE_TIME}) <= $time
                || doubleval($this->data[$this->symbol]['15m'][0]->{CANDLE_15M_CLOSE_TIME}) <= $time
                || doubleval($this->data[$this->symbol]['3m'][0]->{CANDLE_3M_CLOSE_TIME}) <= $time
                || doubleval($this->data[$this->symbol]['1m'][0]->{CANDLE_1M_CLOSE_TIME}) <= $time
            ) {
                // echo $this->symbol . "Real Ignore\n";

                $this->packageLost++;
                continue;
            }

            $this->packageLost = 0;

            $isPending = $this->checkEvent();

            if (!$isPending['result']) return $isPending;

            if ($isPending['data']) {
                // echo "Event check pending " . $this->symbol . " Excute time " . (microtime(true) - $time_start) . " second\n";
                continue;
            }

            $type = 0;
            $flow = null;

            $longResult = null;
            $shortResult = null;
            $startReason = '';

            foreach($this->cfgStrategy as $flowName => $flowData){
                if(!isset($flowData['type'])) continue;
                $flowType = $flowData['type'];
                if($flowType == 'LONG'){
                    if ($this->side == 'LONG' || $this->side == 'BOTH') {
                        if ($type == 0) {
                            $condition = $this->getMatchCondition($flowName, 0);
                            if ($condition != null) {
                                $longResult = $this->compareOr($condition['condition']);
                                if (!$longResult['result']) return $longResult;
                                $startReason = $longResult['message'];
                                if ($longResult['data']){
                                    $type = TESTNET_RESULT_TYPE_LONG;
                                    $flow = $flowName;
                                    break;
                                }
                                
                            }
                        }
                    }
                }
                else if($flowType == 'SHORT'){
                    if ($this->side == 'SHORT' || $this->side == 'BOTH') {
                        $condition = $this->getMatchCondition($flowName, 0);
                        if ($condition != null) {
                            $shortResult = $this->compareOr($condition['condition']);
                            if (!$shortResult['result']) return $shortResult;
                            $startReason = $shortResult['message'];
                            if ($shortResult['data']){
                                $type = TESTNET_RESULT_TYPE_SHORT;
                                $flow = $flowName;
                                break;
                            }
                           
                        }
                    }
                }
                
            }

            if (isset($this->params[TESTNET_PARAM_LOG]) && $this->params[TESTNET_PARAM_LOG] == 1) {
                $this->eventLogModel->add([[
                    TESTNET_ELOG_TIME => $time,
                    TESTNET_ELOG_CAMPAIGN => $this->campaign->{TESTNET_ID},
                    TESTNET_ELOG_SYMBOL => $this->symbol,
                    TESTNET_ELOG_MATCHED => $type,
                    TESTNET_ELOG_CHART => $time,
                    TESTNET_ELOG_RESULT => json_encode([
                        'long' => $longResult,
                        'short' => $shortResult,
                    ]),
                    TESTNET_ELOG_BASE => json_encode($this->data)
                ]]);
            }

            $candle1m = $this->data[$this->symbol]['1m'][0];

            if ($type != 0) {

                //reset data
                $this->maker = null;
                $this->maxOrderProfit = 0;
                $this->baseProfit = doubleval(get($condition['baseprofit'], $this->cfgBaseprofit));


                $interval = $this->cfgInterval;
                $LabPendingTime = 0;
                $this->matchedParamsPhase = null;

                if ($interval > 0) {
                    // Get last action to check interval between action
                    $lastAction = $this->eventModel->read([
                        [
                            [TESTNET_RESULT_CAMPAIGN, '=', $this->campaign->{TESTNET_ID}],
                            [TESTNET_RESULT_PENDING, '=', '0']
                        ]
                    ], function ($db) {
                        $db->orderBy(TESTNET_RESULT_ENTER_TIME, 'DESC')->limit(1);
                    });
                    if (!$lastAction['result']) return $lastAction;
                    if (isset($lastAction['data'][0])) $LabPendingTime = doubleval($lastAction['data'][0]->{TESTNET_RESULT_SELL_TIME});
                }


                if ($time - $LabPendingTime >= ($interval * 60000)) {


                    //Check max trade open limit
                    if ($this->maxTradesOpen > 0) {
                        $openTrades = $this->eventModel->count([[[TESTNET_RESULT_PENDING, '=', 1], [TESTNET_RESULT_STRATEGY, '=', $this->campaign->{TESTNET_STRATEGY}]]]);
                        if (!$openTrades['result']) return $openTrades;
                        if ($this->maxTradesOpen <= $openTrades['data']) {
                            continue;
                        }
                    }


                    $closePrice = doubleval($candle1m->{CANDLE_1M_CLOSE});

                    $addData = [
                        TESTNET_RESULT_ENTER_TIME => $time,
                        TESTNET_RESULT_ENTER_PRICE => $closePrice,
                        TESTNET_RESULT_CAMPAIGN => $this->campaign->{TESTNET_ID},
                        TESTNET_RESULT_SYMBOL => $this->symbol,
                        TESTNET_RESULT_TYPE => $type,
                        TESTNET_RESULT_CHART => $time,
                        TESTNET_RESULT_LOW => $candle1m->{CANDLE_1M_LOW},
                        TESTNET_RESULT_HIGH => $candle1m->{CANDLE_1M_HIGH},
                        TESTNET_RESULT_BASE => json_encode(['0' => $this->data]),
                        TESTNET_RESULT_PENDING => 1,
                        TESTNET_RESULT_STATUS => TESTNET_RESULT_STATUS_ENTER_WAITTING,
                        TESTNET_RESULT_ORDER_PHASE => 0,
                        TESTNET_RESULT_STRATEGY => $this->campaign->{TESTNET_STRATEGY},
                        TESTNET_RESULT_START_REASON => $startReason,
                        TESTNET_RESULT_FLOW => $flow,
                        TESTNET_RESULT_BUDGET => $this->getInvestBudget()
                    ];

                    $this->eventModel->add([$addData]);

                    $event =  $this->eventModel->read([[
                        [TESTNET_RESULT_CAMPAIGN, '=', $this->campaign->{TESTNET_ID}],
                        [TESTNET_RESULT_PENDING, '=', 1]
                    ]]);
                    if (!$event['result'] || !isset($event['data'][0])) {
                        return Reply::make(true, 'No Pending Event', false);
                    }

                    $event = $event['data'][0];
                    $this->event = $event;

                    $enterStep = get($condition['enter_step'], 0);
                    $enterRule = get($condition['enter_rule'], null);

                    if ($enterStep <= 0 && $enterRule === null) {
                        $this->makeOrder($event, $closePrice, 0, $time);
                    } else {
                        $this->enterBase = $closePrice;

                        $this->enterBaseModel->add([[
                            ENTERBASE_ACTION => $event->{TESTNET_RESULT_ID},
                            ENTERBASE_TIME => $time,
                            ENTERBASE_EVENT => ENTERBASE_EVENT_WAITTING,
                            ENTERBASE_VALUE => $closePrice,
                            ENTERBASE_PRICE => $closePrice,
                            ENTERBASE_SYMBOL => $this->symbol,
                            ENTERBASE_CAMPAIGN => $this->campaign->{TESTNET_ID}
                        ]]);

                        // Telegram::send(TELE_ICON_WAITTING . " [" .  $this->campaign->{TESTNET_NAME} . "] #" . $this->symbol
                        //     . " Waitting for " . ($type == TESTNET_RESULT_TYPE_LONG ? 'Long' : 'Short') . " Order"
                        //     . " \n- Time: " . date("H:i:s d/m/Y", $time / 1000)
                        //     . " \n- Close Price: " . $closePrice
                        //     . " \n- Flow: " . $flow
                        //     , 
                        //     $this->teleGrNotice,
                        //     $this->teleBot
                        // );
                        Telegram::send(TELE_ICON_WAITTING . " [" .  $this->campaign->{TESTNET_NAME} . "] #" . $this->symbol
                            . " Chờ để vào lệnh " . ($type == TESTNET_RESULT_TYPE_LONG ? 'Long' : 'Short') . " phase 0"
                            . " \n- Thời gian: " . date("H:i:s d/m/Y", $time / 1000)
                            . " \n- Giá: " . $closePrice
                            . " \n- Flow: " . $flow
                            , 
                            $this->teleGrNotice,
                            $this->teleBot
                        );

                        // $this->addEvent("Chờ để vào lệnh " . ($type == TESTNET_RESULT_TYPE_LONG ? 'Long' : 'Short') . " phase 0");
                    }
                }
            }

            // echo "Event check " . $this->symbol . " Excute time " . (microtime(true) - $time_start) . " second\n";

        }

        return Reply::make(false, "[" . $this->campaign->{TESTNET_NAME} . "] Service Stopped");
    }



    private function checkEvent()
    {

        $khung15m = $this->data[$this->symbol]['15m'];
        $khung3m = $this->data[$this->symbol]['3m'];
        $khung1m = $this->data[$this->symbol]['1m'];

        $closePrice = doubleval($khung1m[0]->{CANDLE_1M_CLOSE});
        $high = doubleval($khung1m[0]->{CANDLE_1M_HIGH});
        $low = doubleval($khung1m[0]->{CANDLE_1M_LOW});
        $openTime = doubleval($khung1m[0]->{CANDLE_1M_OPEN_TIME});
        $closeTime = doubleval($khung1m[0]->{CANDLE_1M_CLOSE_TIME});
        $ema5 = doubleval($khung1m[0]->{CANDLE_1M_EMA5});

        if ($this->cfgBackprofitBaseon == 'ema5_3m') {
            $ema5 = doubleval($khung3m[0]->{CANDLE_3M_EMA5});
        }

        if ($this->cfgBackprofitBaseon == 'ema5_15m') {
            $ema5 = doubleval($khung15m[0]->{CANDLE_15M_EMA5});
        }

        $time = round(microtime(true) * 1000);

        $event =  $this->eventModel->read([[
            [TESTNET_RESULT_CAMPAIGN, '=', $this->campaign->{TESTNET_ID}],
            [TESTNET_RESULT_PENDING, '=', 1]
        ]]);

        if (!$event['result'] || !isset($event['data'][0])) {
            return Reply::make(true, 'No Pending Event', false);
        }

        $event = $event['data'][0];
        $this->event = $event;

        $this->orderData = json_decode($event->{TESTNET_RESULT_BASE}, true);
        if (json_last_error() != JSON_ERROR_NONE) return Reply::make(false, 'Can not get Order data');

        $type = $event->{TESTNET_RESULT_TYPE};
        $status = $event->{TESTNET_RESULT_STATUS};
        $flow = $event->{TESTNET_RESULT_FLOW};

        $phase = doubleval($event->{TESTNET_RESULT_PHASE});
        $nextPhase = doubleval($event->{TESTNET_RESULT_ORDER_PHASE});

        $condition = $this->getMatchCondition($flow, $phase);
        $nextCondition = $this->getMatchCondition($flow, $nextPhase);

        if ($status == TESTNET_RESULT_STATUS_MATCHED || $status == TESTNET_RESULT_STATUS_MATCHED_PART) {
            if ($this->matchedParamsPhase !== $phase) {
                $this->matchedParamsPhase = $phase;
                // Reste max profit and set phase 0 base profit
                $this->maker = null;
                $this->maxOrderProfit = 0;
                $this->baseProfit = doubleval(get($condition['baseprofit'], $this->cfgBaseprofit));

                //log next phase note.

                $afterPhase = get($condition['next_phase'], $phase + 1);
                $afterCondition = $this->getMatchCondition($flow, $afterPhase);
                if($afterCondition){
                    $this->eventModel->edit([
                        DATA_KEY => [[[TESTNET_RESULT_ID, '=', $event->{TESTNET_RESULT_ID}]]],
                        DATA_EDITOR => [
                            TESTNET_RESULT_NEXTPHASE_NOTE => get($afterCondition['note'], ''),
                            TESTNET_RESULT_PHASE_NOTE => get($condition['note'], ''),
                        ]
                    ]);
                }
            }
        }

        $market = false;


        if ($status == TESTNET_RESULT_STATUS_PENDING || $status == TESTNET_RESULT_STATUS_PHASE_PENDING) {

            $enterPrice = doubleval($event->{TESTNET_RESULT_ORDER_PRICE});
            $price = $this->getCheckPendingPrice($event, $closePrice, $high, $low, $openTime);
            $isMatched = false;

            $isTaker = false;
            if (!isset($this->maker) || !$this->maker) {
                $matchedPrice = $closePrice;
                $isTaker = true;
                $this->maker = true;
            } else {
                $matchedPrice = $enterPrice;
            }

            $enterPriceSetting = get($condition['enter_price'], 'market');
            if ($enterPriceSetting == 'market') $market = true;

            if ($type == TESTNET_RESULT_TYPE_LONG) {

                if ($market || $price <= $enterPrice) {

                    $totalQty = doubleval($this->event->{TESTNET_RESULT_MATCHED_QTY}) + doubleval($this->event->{TESTNET_RESULT_ORDER_QTY});
                    $matchedPriceAvg = ($matchedPrice * doubleval($this->event->{TESTNET_RESULT_ORDER_QTY}) + doubleval($this->event->{TESTNET_RESULT_MATCHED_PRICE}) * doubleval($this->event->{TESTNET_RESULT_MATCHED_QTY})) / $totalQty;

                    $editData = [
                        TESTNET_RESULT_STATUS => $nextPhase == ($this->getMatchLeng($flow) - 1) ? TESTNET_RESULT_STATUS_MATCHED : TESTNET_RESULT_STATUS_MATCHED_PART,
                        TESTNET_RESULT_MATCHED_PRICE => $matchedPriceAvg,
                        TESTNET_RESULT_MATCHED_TIME => $time,
                        TESTNET_RESULT_MATCHED_QTY => $totalQty,
                        TESTNET_RESULT_MATCHED_EMA5 => $ema5,
                        TESTNET_RESULT_LOW => $khung1m[0]->{CANDLE_1M_LOW},
                        TESTNET_RESULT_HIGH => $khung1m[0]->{CANDLE_1M_HIGH},
                        TESTNET_RESULT_BASEPROFIT => doubleval(get($condition['baseprofit'], $this->cfgBaseprofit)),
                        TESTNET_RESULT_PHASE => $nextPhase,
                        TESTNET_RESULT_LAST_PRICE => $matchedPrice
                    ];
                    if($event->{TESTNET_RESULT_FIRST_PRICE} == null ) $editData[TESTNET_RESULT_FIRST_PRICE] = $matchedPrice;
                    $this->eventModel->edit([
                        DATA_KEY => [[[TESTNET_RESULT_ID, '=', $event->{TESTNET_RESULT_ID}]]],
                        DATA_EDITOR => $editData,
                    ]);

                    $isMatched = true;
                }
            } else if ($type == TESTNET_RESULT_TYPE_SHORT) {

                if ($market || $price >= $enterPrice) {

                    $totalQty = doubleval($this->event->{TESTNET_RESULT_MATCHED_QTY}) + doubleval($this->event->{TESTNET_RESULT_ORDER_QTY});
                    $matchedPriceAvg = ($matchedPrice * doubleval($this->event->{TESTNET_RESULT_ORDER_QTY}) + doubleval($this->event->{TESTNET_RESULT_MATCHED_PRICE}) * doubleval($this->event->{TESTNET_RESULT_MATCHED_QTY})) / $totalQty;

                    $editData = [
                        TESTNET_RESULT_STATUS => $nextPhase == ($this->getMatchLeng($flow) - 1) ? TESTNET_RESULT_STATUS_MATCHED : TESTNET_RESULT_STATUS_MATCHED_PART,
                        TESTNET_RESULT_MATCHED_PRICE => $matchedPriceAvg,
                        TESTNET_RESULT_MATCHED_QTY => $totalQty,
                        TESTNET_RESULT_MATCHED_TIME => $time,
                        TESTNET_RESULT_MATCHED_EMA5 => $ema5,
                        TESTNET_RESULT_LOW => $khung1m[0]->{CANDLE_1M_LOW},
                        TESTNET_RESULT_HIGH => $khung1m[0]->{CANDLE_1M_HIGH},
                        TESTNET_RESULT_BASEPROFIT => doubleval(get($condition['baseprofit'], $this->cfgBaseprofit)),
                        TESTNET_RESULT_PHASE => $nextPhase,
                        TESTNET_RESULT_LAST_PRICE => $matchedPrice
                    ];
                    if($event->{TESTNET_RESULT_FIRST_PRICE} == null ) $editData[TESTNET_RESULT_FIRST_PRICE] = $matchedPrice;

                    $this->eventModel->edit([
                        DATA_KEY => [[[TESTNET_RESULT_ID, '=', $event->{TESTNET_RESULT_ID}]]],
                        DATA_EDITOR => $editData,
                    ]);
                    $isMatched = true;
                }
            }

            $timelife = $this->cfgTimelife;
            if (!$isMatched) {
                $startTime = doubleval($event->{TESTNET_RESULT_ORDER_TIME});
                // Cancle action and change back to period phase if break timelife.
                if ((doubleval($time) - $startTime) >= $timelife * 60000) {
                    $this->eventModel->edit([
                        DATA_KEY => [[[TESTNET_RESULT_ID, '=', $event->{TESTNET_RESULT_ID}]]],
                        DATA_EDITOR => [
                            TESTNET_RESULT_STATUS => doubleval($event->{TESTNET_RESULT_MATCHED_QTY}) > 0 ? TESTNET_RESULT_STATUS_MATCHED_PART : TESTNET_RESULT_STATUS_CANCLE,
                        ]
                    ]);
                    Telegram::send(TELE_ICON_CANCEL . " [" . $this->campaign->{TESTNET_NAME} . "] #" . $this->symbol . " Cancel \n- Time:" . date("H:i:s d/m/Y", $time / 1000), 
                        $this->teleGrNotice,
                        $this->teleBot
                    );
                    return Reply::make(true, 'Pending Event', true);
                }
            } else {

                $commitPercent = $isTaker ? 0.04 : 0.02;
                $commit = $commitPercent * $matchedPrice * doubleval($this->event->{TESTNET_RESULT_ORDER_QTY}) / 100;

                $this->eventOrder->add([[
                    TESTNET_ORDER_ACTION => $this->event->{TESTNET_RESULT_ID},
                    TESTNET_ORDER_TIME => $time,
                    TESTNET_ORDER_PRICE => $matchedPrice,
                    TESTNET_ORDER_SYMBOL => $this->symbol,
                    TESTNET_ORDER_QTY =>  doubleval($this->event->{TESTNET_RESULT_ORDER_QTY}),
                    TESTNET_ORDER_TYPE => $type,
                    TESTNET_ORDER_PHASE => $nextPhase,
                    TESTNET_ORDER_COMMIT => $commit,
                ]]);
                
                $this->eventModel->edit([
                    DATA_KEY => [[[TESTNET_RESULT_ID, '=', $event->{TESTNET_RESULT_ID}]]],
                    DATA_EDITOR => [
                        TESTNET_RESULT_EVENT_PROFIT => $this->calEventProfit()
                    ],
                ]);


                $margin = get($event->{TESTNET_RESULT_MARGIN}, 1);

                $ms = TELE_ICON_MATCHED . " [" . $this->campaign->{TESTNET_NAME} . "] #" . $this->symbol . " Khớp lệnh phase " . $nextPhase
                . " \n- Giời gian:" . date("H:i:s d/m/Y", $time / 1000)
                . " \n- Giá khớp:" . $matchedPrice
                . " \n- Flow: " . $flow
                . " \n- Số tiền: " . (round($matchedPrice * doubleval($this->event->{TESTNET_RESULT_ORDER_QTY})*100/$margin)/100) . " USDT"
                // . " \n- Quantity: " . $this->event->{TESTNET_RESULT_ORDER_QTY}
                ;
                Telegram::send(
                    $ms,
                    $this->teleGrNotice,
                    $this->teleBot
                );

                if($this->teleGrSummary != null){
                    foreach($this->teleGrSummary as $gr){
                        Telegram::send($ms, $gr, $this->teleBot);
                    }
                }

                $this->addEvent("Khớp lệnh phase " . $nextPhase);
                // Telegram::send(
                //     TELE_ICON_MATCHED . " [" . $this->campaign->{TESTNET_NAME} . "] #" . $this->symbol . " Matched Pharse " . $nextPhase
                //         . " \n- Time:" . date("H:i:s d/m/Y", $time / 1000)
                //         . " \n- Matched Price:" . $matchedPrice
                //         . " \n- Flow: " . $flow
                //         // . " \n- Quantity: " . $this->event->{TESTNET_RESULT_ORDER_QTY}
                //         ,
                //     $this->teleGrNotice,
                //     $this->teleBot
                // );

                return Reply::make(true, 'Pending Event', true);
            }
        }

        if (doubleval($event->{TESTNET_RESULT_MATCHED_QTY}) > 0 && $status != TESTNET_RESULT_STATUS_STOP_PENDING) {

            $matchedPrice = doubleval($event->{TESTNET_RESULT_MATCHED_PRICE});
            $matchedEma5 = doubleval($event->{TESTNET_RESULT_MATCHED_EMA5});

            $price = $this->getCheckMatchedPrice($event, $closePrice, $high, $low, $openTime);

            if ($type == TESTNET_RESULT_TYPE_LONG) {

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

            $this->event->{TESTNET_RESULT_PROFIT} = $profitReal;

            $editData = [];

            $finished = false;
            $releasePercent = 100;
            $releaseIndex = null;
            $isTakeprofit = false;

            // Profit Rule for stop

            // if (doubleval($khung1m[0]->{CANDLE_1M_CLOSE_TIME}) - doubleval($khung1m[1]->{CANDLE_1M_CLOSE_TIME}) > 120000) {
            //     $editData = [
            //         TESTNET_RESULT_STATUS => TESTNET_RESULT_STATUS_STOP_PENDING,
            //         TESTNET_RESULT_PARAMS => 'Package lost',
            //     ];
            //     $finished = true;
            // }

            if (!$finished) {

                $stoploss = get($condition['stoploss'], $this->cfgStoploss);
                $takeprofit = get($condition['takeprofit'], $this->cfgTakeprofit);

                if($stoploss === false) $stoploss = 90;

                $stoploss = doubleval($stoploss);
            
                if ($takeprofit !== false && $maxProfitReal >= $takeprofit) {
                    $takeprofit = doubleval($takeprofit);
                    $editData = [
                        TESTNET_RESULT_STATUS => TESTNET_RESULT_STATUS_STOP_PENDING,
                        TESTNET_RESULT_PARAMS => 'Profit >= ' . $takeprofit
                    ];
                    $finished = true;
                    $isTakeprofit = true;
                }

                if ($minProfitReal <= -$stoploss) {

                    $editData = [
                        TESTNET_RESULT_STATUS => TESTNET_RESULT_STATUS_STOP_PENDING,
                        TESTNET_RESULT_PARAMS => 'Profit <= -' . $stoploss
                    ];
                    $finished = true;
                    $isTakeprofit = true;
                }
            }

            if (!$finished) {

                $stepprofit = doubleval(get($condition['stepprofit'], $this->cfgStepprofit));
                $backprofit = doubleval(get($condition['backprofit'], $this->cfgBackprofit));

                if ($maxProfit > $this->maxOrderProfit) {

                    if($maxProfit > $this->baseProfit && $this->maxOrderProfit < $this->baseProfit){
                        $this->profitBaseModel->add([[
                            PROFITBASE_ACTION => $event->{TESTNET_RESULT_ID},
                            PROFITBASE_TIME => $time,
                            PROFITBASE_EVENT => PROFITBASE_EVENT_WAITTING,
                            PROFITBASE_VALUE => $this->baseProfit,
                            PROFITBASE_PRICE => $closePrice,
                            PROFITBASE_SYMBOL => $this->symbol,
                            PROFITBASE_CAMPAIGN => $this->campaign->{TESTNET_ID}
                        ]]);
                    }
                    
                    $this->maxOrderProfit = $maxProfit;

                }

                if ($stepprofit > 0 && $this->maxOrderProfit > ($this->baseProfit + $stepprofit)) {
                    $this->baseProfit = $this->baseProfit + floor(($this->maxOrderProfit - $this->baseProfit) / $stepprofit) * $stepprofit;

                    $this->profitBaseModel->add([[
                        PROFITBASE_ACTION => $event->{TESTNET_RESULT_ID},
                        PROFITBASE_TIME => $time,
                        PROFITBASE_EVENT => PROFITBASE_EVENT_MAKESTEP,
                        PROFITBASE_VALUE => $this->baseProfit,
                        PROFITBASE_PRICE => $closePrice,
                        PROFITBASE_SYMBOL => $this->symbol,
                        PROFITBASE_CAMPAIGN => $this->campaign->{TESTNET_ID}
                    ]]);
                }

                if ($this->baseProfit > 0 && $this->maxOrderProfit > $this->baseProfit && $profit < $this->baseProfit - $backprofit) {
                    $editData = [
                        TESTNET_RESULT_STATUS => TESTNET_RESULT_STATUS_STOP_PENDING,
                        TESTNET_RESULT_PARAMS => 'Profit <= Base profit (' . $this->baseProfit . ') - back Step Profit(' . $backprofit . ')'
                    ];

                    $this->profitBaseModel->add([[
                        PROFITBASE_ACTION => $event->{TESTNET_RESULT_ID},
                        PROFITBASE_TIME => $time,
                        PROFITBASE_EVENT => PROFITBASE_EVENT_MAKEORDER,
                        PROFITBASE_VALUE => $this->baseProfit,
                        PROFITBASE_PRICE => $closePrice,
                        PROFITBASE_SYMBOL => $this->symbol,
                        PROFITBASE_CAMPAIGN => $this->campaign->{TESTNET_ID}
                    ]]);


                    $finished = true;
                }
            }

            // Price Rule for stop

            if (!$finished) {

                $runningRelease = $event->{TESTNET_RESULT_ORDER_RELEASE};

                    $stops = $this->getStopConditions($flow);
                    if ($stops != null) {
                        foreach ($stops as $key => $stop) {
    
                            if ($runningRelease !== null && $runningRelease <= $key) continue;
    
                            $condition = $stop['condition'];
                            $result = $this->compareOr($condition);
    
                            if (!$result['result']) return $result;
                            if ($result['data']) {
                                $editData = [
                                    TESTNET_RESULT_PARAMS => $result['message'],
                                    TESTNET_RESULT_ORDER_PHASE => get($stop['phase_update'], $phase),
                                    TESTNET_RESULT_ORDER_RELEASE => $key,
                                ];
                                $finished = true;
                                $releasePercent = get($stop['release_percent'], 100);
                                $releaseIndex = $key;
    
                                echo "release " . $releasePercent . "\n";
                                break;
                            }
                        }
                    }
                
            }


            if ($releasePercent < 100) {
                $qty = $event->{TESTNET_RESULT_MATCHED_QTY};
                $releaseQty = $qty * $releasePercent / 100;
                $pre = $this->getPrecision($this->symbol);
                $preQty = $pre['quantity'];
                $releaseQty = round($releaseQty * (10 ** $preQty)) / 10 ** $preQty;
            } else {
                $releaseQty = null;
            }

            if ($finished) {
                if ($releaseIndex === null) {
                    $editData[TESTNET_RESULT_STATUS] = TESTNET_RESULT_STATUS_STOP_PENDING;
                } else {
                    $editData[TESTNET_RESULT_STATUS] = TESTNET_RESULT_STATUS_RELEASE_WAITTING;
                    $editData[TESTNET_RESULT_ORDER_QTY] = $releaseQty;
                    $this->releaseBase = $profitReal;
                }
            }

            $editData[TESTNET_RESULT_BASEPROFIT] = $this->baseProfit;
            $editData[TESTNET_RESULT_PROFIT] = $profitReal;

            $this->eventModel->edit([
                DATA_KEY => [[[TESTNET_RESULT_ID, '=', $event->{TESTNET_RESULT_ID}]]],
                DATA_EDITOR => $editData
            ]);

            if (isset($this->params[TESTNET_PARAM_LOG_ORDER]) && $this->params[TESTNET_PARAM_LOG_ORDER] == 1) {
                $this->eventLog->add([[
                    TESTNET_ELOG_TIME => $time,
                    TESTNET_ELOG_CAMPAIGN => $this->campaign->{TESTNET_ID},
                    TESTNET_ELOG_SYMBOL => $this->symbol,
                    TESTNET_ELOG_MATCHED => $type,
                    TESTNET_ELOG_CHART => $khung1m[0]->{CANDLE_1M_OPEN_TIME},
                    TESTNET_ELOG_RESULT => json_encode([
                        'Status' => $finished ? 'Stop Pending' : 'Matched',
                    ]),
                    TESTNET_ELOG_MAXPROFIT => $maxProfitReal,
                    TESTNET_ELOG_MINPROFIT => $minProfitReal,
                    TESTNET_ELOG_PROFIT => $profit,
                    TESTNET_ELOG_BASEPROFIT => $this->baseProfit,
                    TESTNET_ELOG_STATUS => $finished ? 'Stop Pending' : 'Matched',
                    TESTNET_ELOG_BASE => json_encode($this->data)
                ]]);
            }

            if ($finished) {

                $this->labPendingStop = 0;

                if ($isTakeprofit) {
                    $this->labPendingStop = 1;
                } else {
                    $this->labPendingStop = 0;
                }

                Telegram::send(TELE_ICON_STOP . " [" . $this->campaign->{TESTNET_NAME} . "] #" . $this->symbol
                    . " Stop \n- Reason: " . $editData[TESTNET_RESULT_PARAMS],
                    $this->teleGrNotice,
                    $this->teleBot
                );

                return Reply::make(true, 'Pending Event', true);
            }
        }

        if ($status == TESTNET_RESULT_STATUS_STOP_PENDING) {
            if ($this->labPendingStop < 1) {
                $this->labPendingStop++;
                return Reply::make(true, 'Pending Event', true);
            }

            $matchedPrice = doubleval($event->{TESTNET_RESULT_MATCHED_PRICE});
            $price = $closePrice;

            $commitPercent = 0.04;
            $commit = $commitPercent * $price * doubleval($this->event->{TESTNET_RESULT_MATCHED_QTY}) / 100;
            if ($type == TESTNET_RESULT_TYPE_LONG) {
                $pnl = ($price - $matchedPrice) * doubleval($this->event->{TESTNET_RESULT_MATCHED_QTY});
            } else {
                $pnl = ($matchedPrice - $price) * doubleval($this->event->{TESTNET_RESULT_MATCHED_QTY});
            }


            $this->eventOrder->add([[
                TESTNET_ORDER_ACTION => $this->event->{TESTNET_RESULT_ID},
                TESTNET_ORDER_TIME => $time,
                TESTNET_ORDER_PRICE => $price,
                TESTNET_ORDER_SYMBOL => $this->symbol,
                TESTNET_ORDER_QTY =>  doubleval($this->event->{TESTNET_RESULT_MATCHED_QTY}),
                TESTNET_ORDER_TYPE => $type == TESTNET_RESULT_TYPE_LONG ? TESTNET_RESULT_TYPE_SHORT : TESTNET_RESULT_TYPE_LONG,
                TESTNET_ORDER_PHASE => $phase,
                TESTNET_ORDER_COMMIT => $commit,
                TESTNET_ORDER_PNL => $pnl,
            ]]);


            $pnlData = $this->calCommit($this->event);
            $commit = $pnlData['commit'];
            $pnl = $pnlData['pnl'];
            $isProfit = $pnl > $commit;
            $package = $this->getInvestBudget();
            $realPNL = $pnl - $commit;
            $margin = get($event->{TESTNET_RESULT_MARGIN}, 1);
            $realProfit = ($realPNL) * 100 / $package;
            $invest = doubleval($this->event->{TESTNET_RESULT_MATCHED_QTY}) * doubleval($this->event->{TESTNET_RESULT_MATCHED_PRICE});
            $profit = $realPNL * 100 / $invest;

            $investNoMargin = $invest/$margin;
            $realEventProfit = $profit * $margin;

            $editData = [
                TESTNET_RESULT_PENDING => '0',
                TESTNET_RESULT_STATUS => $isProfit ? TESTNET_RESULT_STATUS_TAKEPROFIT : TESTNET_RESULT_STATUS_STOPLOSS,
                TESTNET_RESULT_SELL_PRICE => $price,
                TESTNET_RESULT_SELL_TIME => $time,
                TESTNET_RESULT_REAL_PROFIT => $realProfit,
                TESTNET_RESULT_REAL_PNL => $realPNL,
                TESTNET_RESULT_EVENT_PROFIT => $profit,
                TESTNET_RESULT_INTERVAL => $time - $this->event->{TESTNET_RESULT_CHART},
            ];

            $this->eventModel->edit([
                DATA_KEY => [[[TESTNET_RESULT_ID, '=', $event->{TESTNET_RESULT_ID}]]],
                DATA_EDITOR => $editData
            ]);


            if (isset($this->params[TESTNET_PARAM_LOG_ORDER]) && $this->params[TESTNET_PARAM_LOG_ORDER] == 1) {
                $this->eventLog->add([[

                    TESTNET_ELOG_TIME => $time,
                    TESTNET_ELOG_CAMPAIGN => $this->campaign->{TESTNET_ID},
                    TESTNET_ELOG_SYMBOL => $this->symbol,
                    TESTNET_ELOG_MATCHED => $type,
                    TESTNET_ELOG_CHART => $khung1m[0]->{CANDLE_1M_OPEN_TIME},
                    TESTNET_ELOG_RESULT => json_encode([
                        'Status' => $isProfit ? 'Take profit' : 'Stoploss',
                    ]),
                    TESTNET_ELOG_PROFIT => $this->event->{TESTNET_RESULT_PROFIT},
                    TESTNET_ELOG_BASE => json_encode($this->data)
                ]]);
            }

            $ms = ($isProfit ? TELE_ICON_TAKEPROFIT : TELE_ICON_STOPLOSS) . " " .$this->campaign->{TESTNET_NAME}." - TỔNG KẾT"
            ."\n- Symbol: ".$this->symbol
            ."\n- Bắt đầu: ". date("H:i:s d/m/Y", $event->{TESTNET_RESULT_CHART} / 1000)
            ."\n- Kết thúc: " . date("H:i:s d/m/Y", $time / 1000)
            ."\n- Loại vị thế: ". ($type == LAB_TYPE_LONG ? "Long" : "Short")
            ."\n- Flow: " . $flow
            ."\n- Margin Mode: Cross"
            ."\n- Đòn bẩy: x" . $event->{TESTNET_RESULT_MARGIN}
            ."\n- Phase tối đa: ". $event->{TESTNET_RESULT_PHASE}
            ."\n- Đầu tư: ". round($investNoMargin*100)/100 . " USDT"
            ."\n- Tổng vốn: ". round($package*100)/100 . " USDT"
            ."\n- Lợi nhuận ròng: " . round($realPNL*100)/100 . " USDT"
            ."\n- Lợi nhuận trên vốn đầu tư: " . round($realEventProfit*100)/100 . "%";

            Telegram::send(
                $ms,
                $this->teleGrNotice,
                $this->teleBot
            );

            if($this->teleGrSummary != null){
                foreach($this->teleGrSummary as $gr){
                    Telegram::send($ms, $gr, $this->teleBot);
                }
            }

            $this->updateProfit($realPNL);
            $this->addEvent("Đóng lệnh", $realPNL);

            return Reply::make(true, 'No Pending Event', false);
        }

        if ($status == TESTNET_RESULT_STATUS_ENTER_WAITTING) {

            $isMakeOrder = false;
            $isCancle = false;

            $enterRule = get($nextCondition['enter_rule'], null);
            $enterCancle = get($nextCondition['enter_cancle'], null);

            if ($enterRule != null) {

                $result = $this->compareOr($enterRule);
                if (!$result['result']) return $result;
                $isMakeOrder = $result['data'];

                if ($enterCancle != null && !$isMakeOrder) {
                    $result = $this->compareOr($enterCancle);
                    if (!$result['result']) return $result;
                    $isCancle = $result['data'];
                }
            }


            if ($enterRule == null) {

                $enterStep = get($nextCondition['enter_step'], 0);
                $enterBack = get($nextCondition['enter_back'], 0);

                if ($enterStep > 0) {
                    $checkPrice = $this->getCheckWaitingPrice($event, $closePrice, $high, $low, $openTime);
                    $enterPrice = doubleval($event->{TESTNET_RESULT_ENTER_PRICE});

                    if ($type == TESTNET_RESULT_TYPE_LONG) {

                        $down = ($enterPrice - $checkPrice['min']) * 100 / $enterPrice;
                        $downBase = ($enterPrice - $this->enterBase) * 100 / $enterPrice;
                        $currentDown = ($enterPrice - $closePrice) * 100 / $enterPrice;

                        if ($down > ($downBase + $enterStep)) {
                            $downBase = floor($down / $enterStep) * $enterStep;
                            $this->enterBase = $enterPrice - ($enterPrice *  $downBase / 100);

                            $this->enterBaseModel->add([[
                                ENTERBASE_ACTION => $event->{TESTNET_RESULT_ID},
                                ENTERBASE_TIME => $time,
                                ENTERBASE_EVENT => ENTERBASE_EVENT_MAKESTEP,
                                ENTERBASE_VALUE => $this->enterBase,
                                ENTERBASE_PRICE => $closePrice,
                                ENTERBASE_SYMBOL => $this->symbol,
                                ENTERBASE_CAMPAIGN => $this->campaign->{TESTNET_ID}
                            ]]);
                        }

                        if ($downBase - $currentDown >= $enterBack) {
                            if ($currentDown >= 0 || $this->allowNegativeWaittingPriceLong) {
                                $isMakeOrder = true;
                                $this->enterBaseModel->add([[
                                    ENTERBASE_ACTION => $event->{TESTNET_RESULT_ID},
                                    ENTERBASE_TIME => $time,
                                    ENTERBASE_EVENT => ENTERBASE_EVENT_MAKEORDER,
                                    ENTERBASE_VALUE => $this->enterBase,
                                    ENTERBASE_PRICE => $closePrice,
                                    ENTERBASE_SYMBOL => $this->symbol,
                                    ENTERBASE_CAMPAIGN => $this->campaign->{TESTNET_ID}
                                ]]);
                            } else {
                                $isCancle = true;
                                $this->enterBaseModel->add([[
                                    ENTERBASE_ACTION => $event->{TESTNET_RESULT_ID},
                                    ENTERBASE_TIME => $time,
                                    ENTERBASE_EVENT => ENTERBASE_EVENT_CANCLE,
                                    ENTERBASE_VALUE => $this->enterBase,
                                    ENTERBASE_PRICE => $closePrice,
                                    ENTERBASE_SYMBOL => $this->symbol,
                                    ENTERBASE_CAMPAIGN => $this->campaign->{TESTNET_ID}
                                ]]);
                            }
                        }
                    } else if ($type == TESTNET_RESULT_TYPE_SHORT) {

                        $up = ($checkPrice['max'] - $enterPrice) * 100 / $enterPrice;
                        $upBase = ($this->enterBase - $enterPrice) * 100 / $enterPrice;
                        $currentUp = ($closePrice - $enterPrice) * 100 / $enterPrice;

                        if ($up > ($upBase + $enterStep)) {
                            $upBase = floor($up / $enterStep) * $enterStep;
                            $this->enterBase = $enterPrice + ($enterPrice * $upBase / 100); 
                            $this->enterBaseModel->add([[
                                ENTERBASE_ACTION => $event->{TESTNET_RESULT_ID},
                                ENTERBASE_TIME => $time,
                                ENTERBASE_EVENT => ENTERBASE_EVENT_MAKESTEP,
                                ENTERBASE_VALUE => $this->enterBase,
                                ENTERBASE_PRICE => $closePrice,
                                ENTERBASE_SYMBOL => $this->symbol,
                                ENTERBASE_CAMPAIGN => $this->campaign->{TESTNET_ID}
                            ]]);
                        }

                        if ($upBase - $currentUp >= $enterBack) {

                            if ($currentUp >= 0 || $this->allowNegativeWaittingPriceShort) {
                                $isMakeOrder = true;
                                $this->enterBaseModel->add([[
                                    ENTERBASE_ACTION => $event->{TESTNET_RESULT_ID},
                                    ENTERBASE_TIME => $time,
                                    ENTERBASE_EVENT => ENTERBASE_EVENT_MAKEORDER,
                                    ENTERBASE_VALUE => $this->enterBase,
                                    ENTERBASE_PRICE => $closePrice,
                                    ENTERBASE_SYMBOL => $this->symbol,
                                    ENTERBASE_CAMPAIGN => $this->campaign->{TESTNET_ID}
                                ]]);
                            } else {
                                $isCancle = true;
                                $this->enterBaseModel->add([[
                                    ENTERBASE_ACTION => $event->{TESTNET_RESULT_ID},
                                    ENTERBASE_TIME => $time,
                                    ENTERBASE_EVENT => ENTERBASE_EVENT_CANCLE,
                                    ENTERBASE_VALUE => $this->enterBase,
                                    ENTERBASE_PRICE => $closePrice,
                                    ENTERBASE_SYMBOL => $this->symbol,
                                    ENTERBASE_CAMPAIGN => $this->campaign->{TESTNET_ID}
                                ]]);
                            }
                        }
                    }

                }
            }

            if ($isMakeOrder) {
                $this->makeOrder($event, $closePrice, $nextPhase, $time);
                return Reply::make(true, 'Pending Event', true);
            }

            if ($isCancle) {
                $this->eventModel->edit([
                    DATA_KEY => [[[TESTNET_RESULT_ID, '=', $event->{TESTNET_RESULT_ID}]]],
                    DATA_EDITOR => [
                        TESTNET_RESULT_STATUS => doubleval($event->{TESTNET_RESULT_MATCHED_QTY}) > 0 ? TESTNET_RESULT_STATUS_MATCHED_PART : TESTNET_RESULT_STATUS_CANCLE,
                        TESTNET_RESULT_PENDING => doubleval($event->{TESTNET_RESULT_MATCHED_QTY}) > 0 ? 1 : 0,
                    ]
                ]);
                Telegram::send(TELE_ICON_CANCEL
                    . " [" .  $this->campaign->{TESTNET_NAME} . "] #"
                    . $this->symbol . " Cancel waitting order phase $nextPhase"
                    . " \n- Time:" . date("H:i:s d/m/Y", $time / 1000),
                    $this->teleGrNotice,
                    $this->teleBot
                );

                return Reply::make(true, 'Pending Event', $event->{TESTNET_RESULT_MATCHED_QTY} > 0);
            }
        }

        if ($status == TESTNET_RESULT_STATUS_MATCHED_PART) {

            if ($phase < ($this->getMatchLeng($flow) - 1)) {
                $afterPhase = get($condition['next_phase'], $phase + 1);
                $afterCondition = $this->getMatchCondition($flow, $afterPhase);

                $checkResult = $this->compareOr($afterCondition['condition']);
                if (!$checkResult['result']) return $checkResult;
                if ($checkResult['data']) {

                    $enterStep = get($afterCondition['enter_step'], 0);
                    $enterRule = get($afterCondition['enter_rule'], null);

                    $closePrice = doubleval($khung1m[0]->{CANDLE_1M_CLOSE});

                    $baseonData = $this->orderData;
                    $baseonData[$afterPhase] = $this->data;

                    $addData = [
                        TESTNET_RESULT_ENTER_TIME => $time,
                        TESTNET_RESULT_ENTER_PRICE => $closePrice,
                        TESTNET_RESULT_LOW => $khung1m[0]->{CANDLE_1M_LOW},
                        TESTNET_RESULT_HIGH => $khung1m[0]->{CANDLE_1M_HIGH},
                        TESTNET_RESULT_BASE => json_encode($baseonData),
                        TESTNET_RESULT_STATUS => TESTNET_RESULT_STATUS_ENTER_WAITTING,
                        TESTNET_RESULT_ORDER_PHASE => $afterPhase
                    ];

                    

                    $this->eventModel->edit([
                        DATA_KEY => [[[TESTNET_RESULT_ID, '=', $event->{TESTNET_RESULT_ID}]]],
                        DATA_EDITOR => $addData
                    ]);

                    if ($enterStep <= 0 && $enterRule === null) {
                        $this->makeOrder($event, $closePrice, $afterPhase, $time);
                    } else {
                        $this->enterBase = $closePrice;

                        $this->enterBaseModel->add([[
                            ENTERBASE_ACTION => $event->{TESTNET_RESULT_ID},
                            ENTERBASE_TIME => $time,
                            ENTERBASE_EVENT => ENTERBASE_EVENT_WAITTING,
                            ENTERBASE_VALUE => $closePrice,
                            ENTERBASE_PRICE => $closePrice,
                            ENTERBASE_SYMBOL => $this->symbol,
                            ENTERBASE_CAMPAIGN => $this->campaign->{TESTNET_ID}
                        ]]);

                        Telegram::send(
                            TELE_ICON_WAITTING . " [" .  $this->campaign->{TESTNET_NAME} . "] #" . $this->symbol  . " Waitting for " . ($type == TESTNET_RESULT_TYPE_LONG ? 'Long' : 'Short') . " Order Pharse " . ($afterPhase)
                                . "\n-Time: " . date("H:i:s d/m/Y", $time / 1000)
                                . " \n- Close Price: " . $closePrice,
                                $this->teleGrNotice,
                                $this->teleBot
                        );
                    }
                }
            } else {
                $this->eventModel->edit([
                    DATA_KEY => [[[TESTNET_RESULT_ID, '=', $event->{TESTNET_RESULT_ID}]]],
                    DATA_EDITOR => [
                        TESTNET_RESULT_STATUS => TESTNET_RESULT_STATUS_MATCHED,
                    ]
                ]);
            }
        }

        if ($status == TESTNET_RESULT_STATUS_RELEASE_WAITTING) {

            $releaseCondition = $this->getStopCondition($flow, $event->{TESTNET_RESULT_ORDER_RELEASE});

            $isRelease = false;
            $isCancle = false;

            $releaseRule = get($releaseCondition['release_rule'], null);
            $releaseCancle = get($releaseCondition['release_cancle'], null);

            if ($releaseRule != null) {
                $result = $this->compareOr($releaseRule);
                if (!$result['result']) return $result;
                $isRelease = $result['data'];

                if ($releaseCancle != null && !$isRelease) {
                    $result = $this->compareOr($releaseCancle);
                    if (!$result['result']) return $result;
                    $isCancle = $result['data'];
                }
            }

            if ($releaseRule == null) {

                $releaseStep = get($releaseCondition['release_step'], 0);
                $releaseBack = get($releaseCondition['release_back'], 0);

                if ($releaseStep > 0) {

                    $matchedPrice = doubleval($event->{TESTNET_RESULT_MATCHED_PRICE});

                    if ($type == TESTNET_RESULT_TYPE_LONG) {
                        $maxProfit = ($high - $matchedPrice) * 100 / $matchedPrice;
                        $profit = ($closePrice - $matchedPrice) * 100 / $matchedPrice;
                    } else if ($type == TESTNET_RESULT_TYPE_SHORT) {
                        $maxProfit = ($matchedPrice - $low) * 100 / $matchedPrice;
                        $profit = ($matchedPrice - $closePrice) * 100 / $matchedPrice;
                    }

                    if ($maxProfit > ($this->releaseBase + $releaseStep)) {
                        $this->releaseBase = floor($maxProfit / $releaseStep) * $releaseStep;
                        $this->profitBaseModel->add([[
                            PROFITBASE_ACTION => $event->{TESTNET_RESULT_ID},
                            PROFITBASE_TIME => $time,
                            PROFITBASE_EVENT => PROFITBASE_EVENT_MAKESTEP,
                            PROFITBASE_VALUE => $this->releaseBase,
                            PROFITBASE_PRICE => $closePrice,
                            PROFITBASE_SYMBOL => $this->symbol,
                            PROFITBASE_CAMPAIGN => $this->campaign->{TESTNET_ID}
                        ]]);
                    }

                    if ($this->releaseBase - $profit > $releaseBack) {
                        $isRelease = true;
                    } else {
                        $isRelease = false;
                    }
                }
            }

            if ($isRelease) {

                if($this->event->{TESTNET_RESULT_ORDER_QTY} == null){
                    $releaseQty =  doubleval($this->event->{TESTNET_RESULT_MATCHED_QTY});
                }else{
                    $releaseQty =  doubleval($this->event->{TESTNET_RESULT_ORDER_QTY});
                }

                $totalQty = doubleval($this->event->{TESTNET_RESULT_MATCHED_QTY}) - $releaseQty;

                $this->eventModel->edit([
                    DATA_KEY => [[[TESTNET_RESULT_ID, '=', $event->{TESTNET_RESULT_ID}]]],
                    DATA_EDITOR => [
                        TESTNET_RESULT_STATUS => $totalQty > 0 ? TESTNET_RESULT_STATUS_RELEASE_PENDING : TESTNET_RESULT_STATUS_STOP_PENDING
                    ]
                ]);

                if($totalQty > 0) $status = TESTNET_RESULT_STATUS_RELEASE_PENDING;

            } else if ($isCancle) {

                $this->eventModel->edit([
                    DATA_KEY => [[[TESTNET_RESULT_ID, '=', $event->{TESTNET_RESULT_ID}]]],
                    DATA_EDITOR => [
                        TESTNET_RESULT_STATUS => doubleval($event->{TESTNET_RESULT_MATCHED_QTY}) > 0 ? TESTNET_RESULT_STATUS_MATCHED_PART : TESTNET_RESULT_STATUS_CANCLE,
                        TESTNET_RESULT_PENDING => doubleval($event->{TESTNET_RESULT_MATCHED_QTY}) > 0 ? 1 : 0,
                        TESTNET_RESULT_ORDER_RELEASE => null,
                    ]
                ]);

                Telegram::send(TELE_ICON_CANCEL . " [" . $this->binancer->getAccount()->{ACCOUNT_NAME} . "] #" . $this->symbol . " Cancel waitting Release Phase $phase \n- Time:" . date("H:i:s d/m/Y"), 
                $this->teleGrNotice,
                $this->teleBot
            );
                return Reply::make(true, 'Pending Event', true);
            }
        }

        if ($status == TESTNET_RESULT_STATUS_RELEASE_PENDING) {

            //Delay 1 loop
            if ($this->labPendingStop < 1) {
                $this->labPendingStop++;
                return Reply::make(true, 'Pending Event', true);
            }

            $matchedPrice = doubleval($this->event->{TESTNET_RESULT_MATCHED_PRICE});

            $commitPercent = 0.04;
            $commit = $commitPercent * $closePrice * doubleval($this->event->{TESTNET_RESULT_ORDER_QTY}) / 100;
            if ($type == TESTNET_RESULT_TYPE_LONG) {
                $pnl = ($closePrice - $matchedPrice) * doubleval($this->event->{TESTNET_RESULT_ORDER_QTY});
            } else {
                $pnl = ($matchedPrice - $closePrice) * doubleval($this->event->{TESTNET_RESULT_ORDER_QTY});
            }

            $releaseProfit = $pnl - $commit;

            $this->eventOrder->add([[
                TESTNET_ORDER_ACTION => $this->event->{TESTNET_RESULT_ID},
                TESTNET_ORDER_TIME => $time,
                TESTNET_ORDER_PRICE => $closePrice,
                TESTNET_ORDER_SYMBOL => $this->symbol,
                TESTNET_ORDER_QTY =>  doubleval($this->event->{TESTNET_RESULT_ORDER_QTY}),
                TESTNET_ORDER_TYPE => $type == TESTNET_RESULT_TYPE_LONG ? TESTNET_RESULT_TYPE_SHORT : TESTNET_RESULT_TYPE_LONG,
                TESTNET_ORDER_PHASE => $phase,
                TESTNET_ORDER_COMMIT => $commit,
                TESTNET_ORDER_PNL => $pnl,
            ]]);

            $totalQty = doubleval($this->event->{TESTNET_RESULT_MATCHED_QTY}) - doubleval($this->event->{TESTNET_RESULT_ORDER_QTY});

            $this->eventModel->edit([
                DATA_KEY => [[[TESTNET_RESULT_ID, '=', $event->{TESTNET_RESULT_ID}]]],
                DATA_EDITOR => [
                    TESTNET_RESULT_STATUS => $nextPhase == ($this->getMatchLeng($flow) - 1) ? TESTNET_RESULT_STATUS_MATCHED : TESTNET_RESULT_STATUS_MATCHED_PART,
                    TESTNET_RESULT_MATCHED_QTY => $totalQty,
                    TESTNET_RESULT_BASEPROFIT => doubleval(get($condition['baseprofit'], $this->cfgBaseprofit)),
                    TESTNET_RESULT_ORDER_RELEASE => null,
                    TESTNET_RESULT_PHASE => $nextPhase,
                    TESTNET_RESULT_LAST_PRICE => $closePrice,
                    TESTNET_RESULT_EVENT_PROFIT => $this->calEventProfit()
                ]
            ]);

            Telegram::send(($pnl > $commit ? TELE_ICON_TAKEPROFIT : TELE_ICON_STOPLOSS)
                    . " [" . $this->campaign->{TESTNET_NAME} . "] #" . $this->symbol . " Release and comeback phase $nextPhase"
                    . "\n- Type: " . ($type == TESTNET_RESULT_TYPE_LONG ? "Short" : "Long")
                    . "\n- Time: " . date("H:i:s d/m/Y", $time / 1000)
                    . "\n- Price: " . $closePrice
                    . "\n- Real Profit: " . ($releaseProfit),
                $this->teleGrNotice,
                $this->teleBot
            );
        }



        return Reply::make(true, 'Pending Event', true);
    }

    private function getMatchCondition($flow, $phase)
    {
        $straType = $this->cfgStrategy[$flow];
        if (isset($straType['disable']) && $straType['disable']) return null;
        if (!isset($straType['match'][doubleval($phase)])) return null;
        return $straType['match'][doubleval($phase)];
    }

    private function getMatchLeng($flow)
    {
        return count($this->cfgStrategy[$flow]['match']);
    }

    private function getStopCondition($flow, $index)
    {
        $straType = $this->cfgStrategy[$flow];
        if (isset($straType['disable']) && $straType['disable']) return null;
        if (!isset($straType['stop'][doubleval($index)])) return null;
        return $straType['stop'][doubleval($index)];
    }

    private function getStopConditions($flow)
    {
        $straType = $this->cfgStrategy[$flow];
        if (!isset($straType['stop'])) return null;
        return $straType['stop'];
    }


    private function makeOrder($action, $closePrice, $phase, $time)
    {
        $this->maker = false;
        $type = $action->{TESTNET_RESULT_TYPE};
        $flow = $action->{TESTNET_RESULT_FLOW};

        $condition = $this->getMatchCondition($flow, $phase);

        $enterPriceSetting = get($condition['enter_price'], 'market');
        $margin = get($condition['margin'], $this->cfgMargin);
        if (is_numeric($enterPriceSetting)) {
            $enterPrice = $closePrice * $enterPriceSetting / 100;
        } else {
            $enterPrice = $closePrice;
        }

        $phaseBudget = $this->getInvestBudget() * get($condition['enter_package'], 100)/100;
        $qty = $phaseBudget / $enterPrice;
        $qty = $qty * $margin;

        $pre = $this->getPrecision($this->symbol);
        $preQty = $pre['quantity'];
        $qty = round($qty * (10 ** $preQty)) / 10 ** $preQty;

        $this->eventModel->edit(
            [
                DATA_KEY => [[[TESTNET_RESULT_ID, '=', $action->{TESTNET_RESULT_ID}]]],
                DATA_EDITOR => [
                    TESTNET_RESULT_ORDER_PRICE => $enterPrice,
                    TESTNET_RESULT_ORDER_TIME => $time,
                    TESTNET_RESULT_ORDER_QTY => $qty,
                    TESTNET_RESULT_ORDER_PHASE => $phase,
                    TESTNET_RESULT_STATUS => $phase == 0 ? TESTNET_RESULT_STATUS_PENDING : TESTNET_RESULT_STATUS_PHASE_PENDING,
                    TESTNET_RESULT_LOW => $this->data[$this->symbol]['1m'][0]->{CANDLE_1M_LOW},
                    TESTNET_RESULT_HIGH => $this->data[$this->symbol]['1m'][0]->{CANDLE_1M_HIGH},
                    TESTNET_RESULT_MARGIN => $margin,
                ]
            ]
        );
        Telegram::send(
            ($type == TESTNET_RESULT_TYPE_SHORT ? TELE_ICON_SHORT : TELE_ICON_LONG) . " [" . $this->campaign->{TESTNET_NAME} . "] #" . $this->symbol . " " . ($type == TESTNET_RESULT_TYPE_SHORT ? 'Short' : 'Long') . " Gửi lệnh phase $phase "
                . "\n- Thời gian:" . date("H:i:s d/m/Y", $time / 1000)
                . "\n- Giá:" . $closePrice
                . "\n- Flow: " . $flow
                . "\n- Tiền dự kiến: " . round($phaseBudget*100)/100 . " USDT"
                ,
                // . "\n- Quantity: " . $qty,
                $this->teleGrNotice,
                $this->teleBot
        );

        // $this->addEvent("Gửi lệnh ".($type == TESTNET_RESULT_TYPE_SHORT ? 'Short' : 'Long')." phase $phase");
    }

    private function getCheckPendingPrice($event, $price, $high, $low, $open_time)
    {
        $type = $event->{TESTNET_RESULT_TYPE};
        if ($type == TESTNET_RESULT_TYPE_LONG) {
            if ($open_time > $event->{TESTNET_RESULT_ORDER_TIME}) return $low;
            if ($low != $event->{TESTNET_RESULT_LOW}) return $low;
        } else if ($type == TESTNET_RESULT_TYPE_SHORT) {
            if ($open_time > $event->{TESTNET_RESULT_ORDER_TIME}) return $high;
            if ($high != $event->{TESTNET_RESULT_HIGH}) return $high;
        }
        return $price;
    }

    private function getCheckMatchedPrice($event, $price, $high, $low, $open_time)
    {

        if ($open_time > $event->{TESTNET_RESULT_MATCHED_TIME}) return ['max' => $high, 'min' => $low];
        $max = $price;
        $min = $price;
        if ($high != $event->{TESTNET_RESULT_HIGH}) $max = $high;
        if ($low != $event->{TESTNET_RESULT_LOW}) $min = $low;

        return ['max' => $max, 'min' => $min];
    }


    private function getCheckWaitingPrice($event, $price, $high, $low, $open_time)
    {
        if ($open_time > $event->{TESTNET_RESULT_ENTER_TIME}) return ['max' => $high, 'min' => $low];
        $max = $price;
        $min = $price;
        if ($high != $event->{TESTNET_RESULT_HIGH}) $max = $high;
        if ($low != $event->{TESTNET_RESULT_LOW}) $min = $low;

        return ['max' => $max, 'min' => $min];
    }

    private function calCommit($event)
    {
        $id = $event->{TESTNET_RESULT_ID};
        $type = $event->{TESTNET_RESULT_TYPE};

        $commit = 0;
        $PNL = 0;

        $postitionQty = 0;
        $avgPrice = 0;

        $result = $this->eventOrder->read([[[TESTNET_ORDER_ACTION, '=', $id]]]);
        if ($result['result']) {
            foreach ($result['data'] as $data) {
                $commit += doubleval($data->{TESTNET_ORDER_COMMIT});
                $PNL += doubleval($data->{TESTNET_ORDER_PNL});
                if($type == $data->{TESTNET_ORDER_TYPE}){
                    $avgPrice = ($postitionQty * $avgPrice + doubleval($data->{TESTNET_ORDER_QTY}) * doubleval($data->{TESTNET_ORDER_PRICE}))/($postitionQty + doubleval($data->{TESTNET_ORDER_QTY}));
                    $postitionQty += doubleval($data->{TESTNET_ORDER_QTY});
                }else{
                    $postitionQty -= doubleval($data->{TESTNET_ORDER_QTY});
                }
            }
        }

        return ['commit' => $commit, "pnl" => $PNL, 'position_qty' => $postitionQty, 'position_price' => $avgPrice];

    }

    

    private function calEventProfit(){
        $event = $this->event;
        $commit = $this->calCommit($event);
        $realPNL = $commit['pnl'] - $commit['commit'];
        $budget = $commit['position_qty'] * $commit['position_price'];  
        $eventProfit = 0;
        if($budget > 0){
            $eventProfit = ($realPNL) * 100 / $budget;
        }  
        return $eventProfit;

    }

    private function updateProfit($profit){

        $newProfit = doubleval($this->campaign->{TESTNET_PROFIT}) + doubleval($profit);
        $this->campaign->{TESTNET_PROFIT} = $newProfit;
        
        return $this->campaignModel->edit([
            DATA_KEY => [[[TESTNET_ID, '=', $this->campaign->{TESTNET_ID}]]],
            DATA_EDITOR => [TESTNET_PROFIT => $newProfit]
        ]);

    }


    private function getInvestBudget(){
        $budget = doubleval(get($this->campaign->{TESTNET_BUDGET}, 100));
        $profit = doubleval(get($this->campaign->{TESTNET_PROFIT}, 0));
        $reserve = doubleval(get($this->campaign->{TESTNET_RESERVE}, 0));

        $compound = get($this->campaign->{TESTNET_COMPOUND}, 0);

        if($compound){
            $investBudget = ($budget + $profit) * (100 - $reserve)/100;
        }else{
            $investBudget = ($budget) * (100 - $reserve)/100;
        }

        return $investBudget > 0 ? $investBudget : 0;
        
    }


    private $getPrecisionResult = null;

    private function getPrecision($symbol)
    {
        if ($this->getPrecisionResult == null) {
            $this->getPrecisionResult = [];
            $result = Query::make('https://fapi.binance.com/fapi/v1/exchangeInfo', 'GET', [], ['dataType' => 'json']);
            
            if (isset($result['symbols'])) {
                $datas = (array)$result['symbols'];
                foreach ($datas as $data) {
                    $this->getPrecisionResult[$data['symbol']] = [
                        'price' => doubleval($data['pricePrecision']),
                        'quantity' => doubleval($data['quantityPrecision']),
                    ];

                    if (isset($data['filters'])) {

                        $filters = $data['filters'];
                        foreach ($filters as $filter) {
                            if (isset($filter['tickSize'])) {
                                $this->getPrecisionResult[$data['symbol']]['tickSize'] = doubleval($filter['tickSize']);
                                break;
                            }
                        }
                    }
                }
            }
            
        }
        
        if (isset($this->getPrecisionResult[$symbol])) return $this->getPrecisionResult[$symbol];
        return false;
    }


    private function addEvent($content, $profit = null){
        $result = $this->testnetEventsModel->add([[
            TESTNET_EVENTS_ICON => $this->watchlist->{WL_ICON},
            TESTNET_EVENTS_SYMBOL => $this->watchlist->{WL_SYMBOL},
            TESTNET_EVENTS_CONTENT => $content,
            TESTNET_EVENTS_PROFIT => $profit,
            TESTNET_EVENTS_TIME => round(microtime(true)*1000),
            TESTNET_EVENTS_CAMPAIGN => $this->campaign->{TESTNET_ID},
            TESTNET_EVENTS_STRATEGY => $this->campaign->{TESTNET_STRATEGY},
        ]]);
    }
}

<?php

namespace App\Event\Lab;

use App\Helpers\Admin\Telegram;
use App\Helpers\DB\Models;
use Illuminate\Support\Facades\DB;
use App\Helpers\Request\Reply;
use App\Event\EventFunc;
use App\Helpers\Control\Ctrl;
use Exception;
use LDAP\Result;

class EventCheckContainer
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

            $this->campaignModel = Models::get('Admin/Lab_campaigns');
            $this->eventModel = Models::get('Admin/Lab_results');
            $this->eventLog = Models::get('Admin/Lab_event_logs');
            $this->eventOrder = Models::get('Admin/Lab_order');
            $this->strategyModel = Models::get('Admin/Lab_strategies');
            $this->altsCoinModel = Models::get('Admin/Change_24h');
            $this->accountModel = Models::get('Admin/Lab_account');

            //Get account information
            $account = $this->accountModel->read([[[LAB_ACCOUNT_ID, '=', $campaign->{LAB_CAMPAIGN_ACCOUNT}]]]);
            if (!$account['result'] || !isset($account['data'][0])) {
                throw new Exception('No Account ID ' . $campaign->{LAB_CAMPAIGN_ACCOUNT});
            }
            $this->account = $account['data'][0];

            $strategyId = $campaign->{LAB_CAMPAIGN_STRATEGY};
            $strategyData = $this->strategyModel->read([[[LAB_STRATEGY_ID, '=', $strategyId]]]);
            if (!$strategyData['result']) Reply::finish($strategyData);
            if (!isset($strategyData['data'][0])) Reply::finish(false, 'Can not find any Strategy');
            $this->strategyData = $strategyData['data'][0];

            $this->cfgStrategy = $this->processLabStrategy($strategyId);
            if (!$this->cfgStrategy['result']) Reply::finish($this->cfgStrategy);
            $this->cfgStrategy = $this->cfgStrategy['data'];

            $this->labPendingTime = 0; // save the time when event finish. 
            $this->labPendingStop = 0; // the time pending to the next action

            $this->maxOrderProfit = 0;

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
                '1d' => 24 * 60 * 60 * 1000,
                '1w' => 7 * 24 * 60 * 60 * 1000,
            ];

            // using for enter step
            $this->enterBase = null;

            // using for release step
            $this->releaseBase = null;

            // marking of which params phase is using
            $this->matchedParamsPhase = null;

            //side long or short both
            $this->side = get($campaign->{LAB_CAMPAIGN_SIDE}, 'BOTH');

            $this->isTelegram = false;

            $this->dbName = Ctrl::get('control_lab_db', 'coin_crawler');

            $this->initial();
        } catch (\Exception $th) {
            $ms = " [" .  $this->campaign->{LAB_CAMPAIGN_NAME} . "] " . $th->getFile() . " " . $th->getLine() . " " . $th->getMessage();
            echo $ms . "\n";
            Telegram::send(TELE_ICON_ERROR . $ms, TELE_SIMULATE_ERROR);
        }
    }

    private function initial()
    {
        //get getPrecision
        $this->getPrecision('');
        //Cal priority
        $priority = $this->getPriorityIndex();
        if (!$priority['result']) return $priority;
        $this->priority = $priority['data'];
    }


    private function getData($candle1m, $indexData)
    {

        $time = $candle1m->{LAB_CANDLE_1M_TIME};
        $this->time = $time;
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

                if (!isset($this->models[$frame])) {
                    $this->models[$frame] = Models::get('Admin/Lab_candle_' . $frame);
                    $this->models[$frame]->query_builder = DB::connection($this->dbName)->table('lab_candle_' . $frame);
                }

                if ($symbol == $this->symbol && $frame == '1m') {
                    $frame0 = $candle1m;
                } else {

                    $isFrame0 = false;

                    if (isset($indexData[$symbol]) && isset($indexData[$symbol][$frame]) && isset($indexData[$symbol][$frame][$time])) {
                        $frame0 = $indexData[$symbol][$frame][$time];
                        $isFrame0 = true;
                    }

                    if (!$isFrame0) {
                        $frame0 = $this->models[$frame]->read([[
                            [$columnName['LAB_CANDLE_SYMBOL'], '=', $symbol],
                            [$columnName['LAB_CANDLE_TIME'], '=', $time]
                        ]]);
                        if (!$frame0['result']) return $frame0;
                        if (isset($frame0['data'][0])) {
                            $frame0 = $frame0['data'][0];
                            $isFrame0 = true;
                        }
                    }

                    if (!$isFrame0) {
                        $frame0 = $this->models[$frame]->read([[
                            [$columnName['LAB_CANDLE_SYMBOL'], '=', $symbol],
                            [$columnName['LAB_CANDLE_TIME'], '<=', $time],
                            [$columnName['LAB_CANDLE_TIME'], '>', $time - 60 * 1000]
                        ]], function ($db) use ($columnName) {
                            $db->orderBy($columnName['LAB_CANDLE_TIME'], 'DESC')->limit(1);
                        });
                        if (!$frame0['result']) return $frame0;
                        if (isset($frame0['data'][0])) {
                            $frame0 = $frame0['data'][0];
                            $isFrame0 = true;
                        }
                    }

                    if (!$isFrame0) {
                        return Reply::make(false, 'Can not get data ' . $symbol . ' frame ' . $frame . ' 0 ' . $time);
                    }
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


    private function caculateElement($struct, $dynamicIndex = null)
    {

        if (is_numeric($struct)) return Reply::make(true, $struct, $struct);

        if (is_string($struct)) {
            if ($struct == 'order_time') {
                if ($this->event == null) return Reply::make(false, 'No Event');
                return Reply::make(true, $struct, doubleval($this->event->{LAB_RESULT_ORDER_TIME}));
            }
            return Reply::make(true, $struct, $struct);
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

            $column = 'lab_candle_' . $frame . '_' . $column;

            $data = $this->data;

            if ($position == 'order') {
                return Reply::make(false, 'Does not support position = order');
                $phase = get($struct['phase'], 0);
                $data = $this->orderData[$phase];
                $des .= " Pharse $phase";
            }

            if (!isset($data[$symbol])) return Reply::make(false, 'Can not get Data ' . $symbol);
            if (!isset($data[$symbol][$frame])) return Reply::make(false, "Can not get Data $symbol $frame");
            if (!isset($data[$symbol][$frame][$index])) return Reply::make(false, "Can not get Data $symbol $frame $index");

            try {
                if (is_numeric($data[$symbol][$frame][$index]->{$column})) {
                    return Reply::make(true, $des, doubleval($data[$symbol][$frame][$index]->{$column}) * $percent / 100);
                }
                return Reply::make(true, $des, $data[$symbol][$frame][$index]->{$column});
            } catch (\Exception $th) {
                return Reply::make(false, "Can not get Data $symbol $frame $index $column");
            }
        }

        if ($type == 'event') {
            if ($this->event == null) return Reply::make(false, 'No Event');
            $column = get($struct['column'], null);
            $column = 'lab_result_' . $column;
            $percent = doubleval(get($struct['percent'], 100));
            if (!isset($this->event->{$column})) return Reply::make(false, 'Can not find column ' . $column);
            $value = $this->event->{$column};
            if ($percent != 100) {
                $des = "Event $percent% $column";
            } else {
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

        if ($type == 'lastest') {
            $index = get($struct['index'], null);
            $frame = get($struct['frame'], null);
            $condition = get($struct['condition'], null);
            $column = get($struct['column'], null);
            $symbol = get($struct['symbol'], $this->symbol);
            $percent = doubleval(get($struct['percent'], 100));


            if ($frame === null || $index === null || $condition === null || $column === null)
                return Reply::make(false, 'Please define symbol, frame, column and index ' . json_encode($struct));

            if ($percent != 100) {
                $des = "Lastest $symbol Frame $percent% $frame $column";
            } else {
                $des = "Lastest $symbol Frame $frame $column";
            }

            $column = 'lab_candle_' . $frame . '_' . $column;
            $index = -intval($index);

            for ($i = 0; $i <= $index; $i++) {
                $isStop = $this->compareOr($condition, $i);
                if (!$isStop['result']) return $isStop;
                if ($isStop['data']) {
                    $data = $data = $this->data;

                    if (!isset($data[$symbol])) return Reply::make(false, 'Can not get Data ' . $symbol);
                    if (!isset($data[$symbol][$frame])) return Reply::make(false, "Can not get Data $symbol $frame");
                    if (!isset($data[$symbol][$frame][$i])) return Reply::make(false, "Can not get Data $symbol $frame $i");
                    try {
                        if (is_numeric($data[$symbol][$frame][$i]->{$column})) {
                            return Reply::make(true, $des, doubleval($data[$symbol][$frame][$i]->{$column}) * $percent / 100);
                        }
                        return Reply::make(true, $des, $data[$symbol][$frame][$i]->{$column});
                    } catch (\Exception $th) {
                        return Reply::make(false, "Can not get Data $symbol $frame $i $column");
                    }
                }
            }
            return Reply::make(true, $des, null);
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

                if (is_array($stop)) {
                    $isStop = $this->compareOr($stop, $i);
                    if (!$isStop['result']) return $isStop;


                    if ($isStop['data']) {
                        // print_r($isStop);
                        echo date("d/m/Y H:i:s", $this->data[$this->symbol]['1m'][0]->{LAB_CANDLE_1M_TIME} / 1000) . "_stop_" . $needStop . "_" . $cross . "\n";
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
                            echo date("d/m/Y H:i:s", $this->data[$this->symbol]['1m'][0]->{LAB_CANDLE_1M_TIME} / 1000) . "_thresold_" . $needStop . "_" . $cross . "\n";
                            return Reply::make(true, $des, $cross);
                        }
                    }
                }
            }

            // echo date("d/m/Y H:i:s", $this->data[$this->symbol]['1m'][0]->{LAB_CANDLE_1M_TIME} / 1000) ."_". $cross . "\n";

            return Reply::make(true, $des, $cross);
        }

        if ($type == 'calculate') {
            $number1 = get($struct['number_1'], null);
            $number2 = get($struct['number_2'], null);
            $logic = get($struct['logic'], null);

            if ($number1 === null || $number2 === null || $logic === null)
                return Reply::make(false, 'Please define number_1, number_2, logic' . json_encode($struct));
            $num1 = $this->caculateElement($number1);
            if (!$num1['result']) return $num1;
            $num2 = $this->caculateElement($number2);
            if (!$num2['result']) return $num2;

            $des1 = $num1['message'];
            $des2 = $num2['message'];
            $des = $des1 . $logic . $des2;

            $result = null;
            if ($logic == '+') $result = doubleval($num1['data']) + doubleval($num2['data']);
            if ($logic == '-') $result = doubleval($num1['data']) - doubleval($num2['data']);
            if ($logic == '*') $result = doubleval($num1['data']) * doubleval($num2['data']);
            if ($logic == '/') $result = doubleval($num1['data']) / doubleval($num2['data']);
            if ($result === null) return Reply::make(false, 'Does not support logic ' . $logic);

            return Reply::make(true, $des, $result);
        }

        if ($type == 'if') {
            $condition = get($struct['condition'], null);
            $true = get($struct['true'], null);
            $false = get($struct['false'], null);

            if ($condition === null || $true === null || $false === null)
                return Reply::make(false, 'Please define condition, true, false' . json_encode($struct));

            $conditionCheck = $this->compareOr($condition);
            if (!$conditionCheck['result']) return $conditionCheck;
            $conditionCheck = $conditionCheck['data'];

            $des = 'if ' . $conditionCheck['message'];
            $result = null;
            if ($conditionCheck) {
                $trueValue = $this->caculateElement($true);
                if (!$trueValue['result']) return $trueValue;
                return Reply::make(true, "If (" . $conditionCheck['message'] . ") return " . $trueValue['message'], $trueValue['data']);
            } else {
                $falseValue = $this->caculateElement($false);
                if (!$falseValue['result']) return $falseValue;
                return Reply::make(true, "If not (" . $conditionCheck['message'] . ") return " . $falseValue['message'], $falseValue['data']);
            }
        }

        return Reply::make(false, 'Can not caculate ' . json_encode($struct));
    }


    public function check($candle1m, $indexData)
    {

        try {

            $time = $candle1m->{LAB_CANDLE_1M_TIME};
            $time_start = microtime(true);
            $result = $this->getData($candle1m, $indexData);
            // echo "Event check get Data " . $this->symbol . " Excute time " . (microtime(true) - $time_start) . " second\n";
            if (!$result['result']) {
                $this->log($result['message']);
                return Reply::make(true, $result['message']);
            }

            //Check is pending event
            $isPending = $this->checkEvent();
            if (!$isPending['result']) return $isPending;
            if ($isPending['data']) {
                return Reply::make(true, 'pending', $this->event);
            }


            $type = 0;
            $flow = null;
            $strategy = null;
            $container = null;
            $flowName = null;

            $longResult = null;
            $shortResult = null;
            $startReason = '';


            foreach ($this->cfgStrategy as $flowN => $flowData) {
                if (!isset($flowData['type'])) continue;
                if (!$this->checkBlacklist($flowN)) continue;
                $flowType = $flowData['type'];
                if ($flowType == 'LONG') {
                    if ($this->side == 'LONG' || $this->side == 'BOTH') {
                        if ($type == 0) {
                            $condition = $this->getMatchCondition($flowN, 0);
                            if ($condition != null) {
                                $longResult = $this->compareOr($condition['condition']);
                                if (!$longResult['result']) return $longResult;

                                $startReason = $longResult['message'];
                                if ($longResult['data']) {
                                    $freeSlot = $this->getFreeSlot($flowN);
                                    if (is_null($freeSlot) || $freeSlot > 0) {
                                        $type = LAB_RESULT_TYPE_LONG;
                                        $flow = $flowData['name'];
                                        $strategy = $flowData['strategy'];
                                        $container = get($flowData['container'], null);
                                        $flowName = $flowN;
                                        break;
                                    }
                                }
                            }
                        }
                    }
                } else if ($flowType == 'SHORT') {
                    if ($this->side == 'SHORT' || $this->side == 'BOTH') {
                        $condition = $this->getMatchCondition($flowN, 0);
                        if ($condition != null) {
                            $shortResult = $this->compareOr($condition['condition']);
                            if (!$shortResult['result']) return $shortResult;
                            $startReason = $shortResult['message'];
                            if ($shortResult['data']) {
                                $freeSlot = $this->getFreeSlot($flowN);
                                if (is_null($freeSlot) || $freeSlot > 0) {
                                    $type = LAB_RESULT_TYPE_SHORT;
                                    $flow = $flowData['name'];
                                    $strategy = $flowData['strategy'];
                                    $container = get($flowData['container'], null);
                                    $flowName = $flowN;
                                    break;
                                }
                            }
                        }
                    }
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

                //reset all local data
                $this->maker = null;
                $this->maxOrderProfit = 0;
                $this->baseProfit = doubleval(get($condition['baseprofit'], $this->getFlowData($flowName, 'baseprofit')));
                $this->matchedParamsPhase = null;

                $interval = $this->getFlowData($flowName, 'interval');

                if ($this->labPendingTime >= 0 && $time - $this->labPendingTime >= ($interval * 60000)) {
                    $this->labPendingTime = -1;

                    //Check max trade open limit
                    $freePossition = $this->getFreePosition($flowName);
                    if (!is_null($freePossition) && $freePossition <= 0) {
                        return Reply::make(true, 'max open trade limit');
                    };

                    $closePrice = doubleval($candle1m->{LAB_CANDLE_1M_CLOSE});

                    $btcwma1d = null;
                    $btcwma1w = null;
                    if (isset($this->data['BTCUSDT'])) {
                        if (isset($this->data['BTCUSDT']['1d']) && isset($this->data['BTCUSDT']['1d'][0])) $btcwma1d = $this->data['BTCUSDT']['1d'][0]->{LAB_CANDLE_1D_RSI_WMA};
                        if (isset($this->data['BTCUSDT']['1w']) && isset($this->data['BTCUSDT']['1w'][0])) $btcwma1w = $this->data['BTCUSDT']['1w'][0]->{LAB_CANDLE_1W_RSI_WMA};
                    }

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
                        LAB_RESULT_ORDER_PHASE => 0,
                        LAB_RESULT_STRATEGY => $strategy,
                        LAB_RESULT_START_REASON => $startReason,
                        LAB_RESULT_FLOW => $flow,
                        LAB_RESULT_BTC_WMA45_1D => $btcwma1d,
                        LAB_RESULT_BTC_WMA45_1W => $btcwma1w,
                        LAB_RESULT_ACCOUNT => $this->account->{LAB_ACCOUNT_ID},
                        LAB_RESULT_CONTAINER => $container,
                        LAB_RESULT_MATCHED_QTY => 0,
                        LAB_RESULT_MATCHED_PRICE => 0,

                    ];

                    $this->eventModel->add([$addData]);

                    // Load event
                    $event =  $this->eventModel->read([[
                        [LAB_RESULT_CAMPAIGN, '=', $this->campaign->{LAB_CAMPAIGN_ID}],
                        [LAB_RESULT_PENDING, '=', 1]
                    ]]);
                    if (!$event['result'] || !isset($event['data'][0])) {
                        return Reply::make(true, 'No Pending Event', false);
                    }

                    $event = $event['data'][0];
                    $this->event = $event;


                    $this->enterBase = $closePrice;

                    $this->log('Check condition OK ' . $closePrice, $time);

                    $this->isTelegram && Telegram::send(TELE_ICON_WAITTING
                        . " [" .  $this->campaign->{LAB_CAMPAIGN_NAME} . "] #" . $this->symbol
                        . " Waitting for " . ($type == LAB_RESULT_TYPE_LONG ? 'Long' : 'Short') . " Order"
                        . "\n- Time: " . date("d/m/Y H:i:s", $time / 1000)
                        . "\n- Close Price: " . $closePrice, TELE_SIMULATE);
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
        //Get Event
        if ($this->event) {
            if ($this->event->{LAB_RESULT_PENDING} == 0) {
                return Reply::make(true, 'No Pending Event', false);
            }
        }

        if (!$this->event) {
            $event =  $this->eventModel->read([[
                [LAB_RESULT_CAMPAIGN, '=', $this->campaign->{LAB_CAMPAIGN_ID}],
                [LAB_RESULT_PENDING, '=', 1]
            ]]);
            if (!$event['result']) return $event;
            if (!isset($event['data'][0])) {
                $this->event = (object)[
                    LAB_RESULT_PENDING => 0
                ];
                return Reply::make(true, 'No Pending Event', false);
            }
            $event = $event['data'][0];
            $this->event = $event;
        } else {
            $event = $this->event;
        }


        //Load some default frame
        // $khung15m = $this->data[$this->symbol]['15m'];
        // $khung3m = $this->data[$this->symbol]['3m'];
        $khung1m = $this->data[$this->symbol]['1m'];

        $closePrice = doubleval($khung1m[0]->{LAB_CANDLE_1M_CLOSE});
        $high = doubleval($khung1m[0]->{LAB_CANDLE_1M_HIGH});
        $low = doubleval($khung1m[0]->{LAB_CANDLE_1M_LOW});
        $openTime = doubleval($khung1m[0]->{LAB_CANDLE_1M_OPEN_TIME});
        $closeTime = doubleval($khung1m[0]->{LAB_CANDLE_1M_CLOSE_TIME});
        $time = doubleval($khung1m[0]->{LAB_CANDLE_1M_TIME});

        // $this->orderData = json_decode($event->{LAB_RESULT_BASE}, true);
        // if (json_last_error() != JSON_ERROR_NONE) return Reply::make(false, 'Can not get Order data');

        $type = $event->{LAB_RESULT_TYPE};
        $status = $event->{LAB_RESULT_STATUS};
        $phase = doubleval($event->{LAB_RESULT_PHASE});
        $nextPhase = doubleval($event->{LAB_RESULT_ORDER_PHASE});
        $flowName = $this->getFlowName($event);

        //Define ema5 type will be used in event
        $ema5 = doubleval($khung1m[0]->{LAB_CANDLE_1M_EMA5});
        $cfgBackprofitBaseon = $this->getFlowData($flowName, 'baseprofit_baseon');
        // if ($cfgBackprofitBaseon == 'ema5_3m') {
        //     $ema5 = doubleval($khung3m[0]->{LAB_CANDLE_3M_EMA5});
        // }
        // if ($cfgBackprofitBaseon == 'ema5_15m') {
        //     $ema5 = doubleval($khung15m[0]->{LAB_CANDLE_15M_EMA5});
        // }

        // get condition and condition of the next phase
        $condition = $this->getMatchCondition($flowName, $phase);
        $nextCondition = $this->getMatchCondition($flowName, $nextPhase);

        //Process status

        $cfgBaseProfit = doubleval(get($condition['baseprofit'], $this->getFlowData($flowName, 'baseprofit')));

        if ($status == LAB_RESULT_STATUS_MATCHED || $status == LAB_RESULT_STATUS_MATCHED_PART) {
            if ($this->matchedParamsPhase !== $phase) {
                $this->matchedParamsPhase = $phase;
                // Reste max profit and set phase 0 base profit
                $this->maker = null;
                $this->maxOrderProfit = 0;
                $this->baseProfit = $cfgBaseProfit;
            }
        }

        $market = false;
        if ($status == LAB_RESULT_STATUS_PENDING || $status == LAB_RESULT_STATUS_PHASE_PENDING) {

            $enterPrice = doubleval($event->{LAB_RESULT_ORDER_PRICE});
            $price = $this->getCheckPendingPrice($event, $closePrice, $high, $low, $openTime);
            $isMatched = false;

            $isTaker = false;
            if (!$this->maker) {
                $matchedPrice = $closePrice;
                $isTaker = true;
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
                    $this->log('avgprice: ' . $matchedPriceAvg);
                    $editData = [
                        LAB_RESULT_STATUS => $nextPhase == ($this->getMatchLeng($flowName) - 1) ? LAB_RESULT_STATUS_MATCHED : LAB_RESULT_STATUS_MATCHED_PART,
                        LAB_RESULT_MATCHED_PRICE => $matchedPriceAvg,
                        LAB_RESULT_MATCHED_TIME => $time,
                        LAB_RESULT_MATCHED_QTY => $totalQty,
                        LAB_RESULT_MATCHED_EMA5 => $ema5,
                        LAB_RESULT_LOW => $khung1m[0]->{LAB_CANDLE_1M_LOW},
                        LAB_RESULT_HIGH => $khung1m[0]->{LAB_CANDLE_1M_HIGH},
                        LAB_RESULT_BASEPROFIT => $cfgBaseProfit,
                        LAB_RESULT_PHASE => $nextPhase,
                        LAB_RESULT_LAST_PRICE => $matchedPrice
                    ];
                    if ($event->{LAB_RESULT_FIRST_PRICE} == null) $editData[LAB_RESULT_FIRST_PRICE] = $matchedPrice;

                    $this->updateEvent([
                        DATA_KEY => [[[LAB_RESULT_ID, '=', $event->{LAB_RESULT_ID}]]],
                        DATA_EDITOR => $editData,
                    ]);


                    $isMatched = true;
                }
            } else if ($type == LAB_RESULT_TYPE_SHORT) {

                if ($market || $price >= $enterPrice) {

                    $totalQty = doubleval($this->event->{LAB_RESULT_MATCHED_QTY}) + doubleval($this->event->{LAB_RESULT_ORDER_QTY});
                    $matchedPriceAvg = ($matchedPrice * doubleval($this->event->{LAB_RESULT_ORDER_QTY}) + doubleval($this->event->{LAB_RESULT_MATCHED_PRICE}) * doubleval($this->event->{LAB_RESULT_MATCHED_QTY})) / $totalQty;

                    $editData = [
                        LAB_RESULT_STATUS => $nextPhase == ($this->getMatchLeng($flowName) - 1) ? LAB_RESULT_STATUS_MATCHED : LAB_RESULT_STATUS_MATCHED_PART,
                        LAB_RESULT_MATCHED_PRICE => $matchedPriceAvg,
                        LAB_RESULT_MATCHED_QTY => $totalQty,
                        LAB_RESULT_MATCHED_TIME => $time,
                        LAB_RESULT_MATCHED_EMA5 => $ema5,
                        LAB_RESULT_LOW => $khung1m[0]->{LAB_CANDLE_1M_LOW},
                        LAB_RESULT_HIGH => $khung1m[0]->{LAB_CANDLE_1M_HIGH},
                        LAB_RESULT_BASEPROFIT => $cfgBaseProfit,
                        LAB_RESULT_PHASE => $nextPhase,
                        LAB_RESULT_LAST_PRICE => $matchedPrice
                    ];
                    if ($event->{LAB_RESULT_FIRST_PRICE} == null) $editData[LAB_RESULT_FIRST_PRICE] = $matchedPrice;

                    $this->updateEvent([
                        DATA_KEY => [[[LAB_RESULT_ID, '=', $event->{LAB_RESULT_ID}]]],
                        DATA_EDITOR => $editData
                    ]);

                    $isMatched = true;
                }
            }

            $timelife = $this->getFlowData($flowName, 'timelife');
            if (!$isMatched) {
                $this->log("Pending");
                $startTime = doubleval($event->{LAB_RESULT_ORDER_TIME});
                if ((doubleval($time) - $startTime) >= $timelife * 60000) {
                    $this->updateEvent([
                        DATA_KEY => [[[LAB_RESULT_ID, '=', $event->{LAB_RESULT_ID}]]],
                        DATA_EDITOR => [
                            LAB_RESULT_STATUS => doubleval($event->{LAB_RESULT_MATCHED_QTY}) > 0 ? LAB_RESULT_STATUS_MATCHED_PART : LAB_RESULT_STATUS_CANCLE,
                            LAB_RESULT_PENDING => doubleval($event->{LAB_RESULT_MATCHED_QTY}) > 0 ? 1 : 0,
                            LAB_RESULT_PARAMS => "Got the timelife $timelife"
                        ]
                    ], true);
                    $this->isTelegram && Telegram::send(TELE_ICON_CANCEL . " [" . $this->campaign->{LAB_CAMPAIGN_NAME} . "] #" . $this->symbol . " Cancel \n- Time:" . date("d/m/Y H:i:s", $time / 1000), TELE_SIMULATE);
                    return Reply::make(true, 'Pending Event', true);
                }
            } else {

                $commitPercent = $isTaker ? 0.04 : 0.02;
                $commit = $commitPercent * $matchedPrice * doubleval($this->event->{LAB_RESULT_ORDER_QTY}) / 100;
                /** Log oder to oder table */
                $this->eventOrder->add([[
                    LAB_ORDER_ACTION => $this->event->{LAB_RESULT_ID},
                    LAB_ORDER_TIME => $time,
                    LAB_ORDER_PRICE => $matchedPrice,
                    LAB_ORDER_SYMBOL => $this->symbol,
                    LAB_ORDER_QTY =>  doubleval($this->event->{LAB_RESULT_ORDER_QTY}),
                    LAB_ORDER_TYPE => $type,
                    LAB_ORDER_PHASE => $nextPhase,
                    LAB_ORDER_COMMIT => $commit,
                ]]);

                //Cal event profit
                $this->updateEvent([
                    DATA_KEY => [[[LAB_RESULT_ID, '=', $event->{LAB_RESULT_ID}]]],
                    DATA_EDITOR => [
                        LAB_RESULT_EVENT_PROFIT => $this->calEventProfit(),
                    ]
                ], true);

                $this->log("Pending finish closeprice: $matchedPrice", $time);

                $this->isTelegram && Telegram::send(
                    TELE_ICON_MATCHED . " [" . $this->campaign->{LAB_CAMPAIGN_NAME} . "] #" . $this->symbol . " Matched phase $nextPhase"
                        . " \n- Time:" . date("d/m/Y H:i:s", $time / 1000)
                        . "\n- Matched Price:" . $matchedPrice,
                    TELE_SIMULATE
                );

                return Reply::make(true, 'Pending Event', true);
            }
        }

        if (doubleval($event->{LAB_RESULT_MATCHED_QTY}) > 0 && $status != LAB_STATUS_STOP_PENDING) {

            $matchedPrice = doubleval($event->{LAB_RESULT_MATCHED_PRICE});
            $matchedEma5 = doubleval($event->{LAB_RESULT_MATCHED_EMA5});

            $price = $this->getCheckMatchedPrice($event, $closePrice, $high, $low, $openTime);

            if ($type == LAB_TYPE_LONG) {

                $maxProfitReal = ($price['max'] - $matchedPrice) * 100 / $matchedPrice;
                $minProfitReal = ($price['min'] - $matchedPrice) * 100 / $matchedPrice;
                $profitReal = ($closePrice - $matchedPrice) * 100 / $matchedPrice;

                if ($cfgBackprofitBaseon == 'close') {

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

                if ($cfgBackprofitBaseon == 'close') {

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
            $releasePercent = 100;
            $releaseIndex = null;
            $releaseQty = null;

            //Check liquid
            if ($this->account->{LAB_ACCOUNT_MARGIN_TYPE} == 'ISOLATE') {
                if ($this->checkLiquidation()) {
                    $editData = [
                        LAB_RESULT_STATUS => LAB_RESULT_STATUS_STOP_PENDING,
                        LAB_RESULT_PARAMS => 'Liquidation'
                    ];
                    $finished = true;
                }
            }

            //Check stoploss and takeprofit
            if (!$finished) {

                $stoploss = get($condition['stoploss'], $this->getFlowData($flowName, 'stoploss'));
                $takeprofit = get($condition['takeprofit'], $this->getFlowData($flowName, 'takeprofit'));

                if ($takeprofit > 0 && $maxProfitReal >= $takeprofit) {
                    $takeprofit = doubleval($takeprofit);
                    $editData = [
                        LAB_RESULT_STATUS => LAB_RESULT_STATUS_STOP_PENDING,
                        LAB_RESULT_PARAMS => 'Profit >= ' . $takeprofit
                    ];
                    $finished = true;
                    $isTakeprofit = true;
                }

                if ($stoploss > 0 && $minProfitReal <= -$stoploss) {
                    $stoploss = doubleval($stoploss);
                    $editData = [
                        LAB_RESULT_STATUS => LAB_RESULT_STATUS_STOP_PENDING,
                        LAB_RESULT_PARAMS => 'Profit <= -' . $stoploss
                    ];
                    $finished = true;
                    $isTakeprofit = true;
                }
            }

            //Check base profit
            if (!$finished) {

                $stepprofit = doubleval(get($condition['step_profit'], $this->getFlowData($flowName, 'step_profit')));
                $backprofit = doubleval(get($condition['back_profit'], $this->getFlowData($flowName, 'back_profit')));

                if ($maxProfit > $this->maxOrderProfit) {
                    $this->maxOrderProfit = $maxProfit;
                }

                if ($stepprofit > 0 && $this->maxOrderProfit > ($this->baseProfit + $stepprofit)) {
                    $this->baseProfit = $this->baseProfit + floor(($this->maxOrderProfit - $this->baseProfit) / $stepprofit) * $stepprofit;
                }

                if ($this->baseProfit > 0 && $this->maxOrderProfit > $this->baseProfit && $profit < $this->baseProfit - $backprofit) {

                    $editData = [
                        LAB_RESULT_STATUS => LAB_RESULT_STATUS_STOP_PENDING,
                        LAB_RESULT_PARAMS => 'Profit <= Base profit (' . $this->baseProfit . ') - back Step Profit(' . $backprofit . ')'
                    ];
                    $finished = true;
                }
            }

            // Price Rule for stop
            if (!$finished) {

                $runningRelease = $event->{LAB_RESULT_ORDER_RELEASE};

                $stops = $this->getStopConditions($flowName);
                if ($stops != null) {
                    foreach ($stops as $key => $stop) {

                        if ($runningRelease !== null && $runningRelease <= $key) continue;

                        $condition = $stop['condition'];
                        $result = $this->compareOr($condition);

                        if (!$result['result']) return $result;
                        if ($result['data']) {
                            
                            $editData = [
                                LAB_RESULT_PARAMS => $result['message'],
                                LAB_RESULT_ORDER_PHASE => get($stop['phase_update'], $phase),
                                LAB_RESULT_ORDER_RELEASE => $key,
                            ];
                            $finished = true;
                            $releasePercent = get($stop['release_percent'], 100);
                            $releaseIndex = $key;

                            if ($releasePercent < 100) {
                                $qty = $event->{LAB_RESULT_MATCHED_QTY};
                                $releaseQty = $qty * $releasePercent / 100;
                                $pre = $this->getPrecision($this->symbol);
                                $preQty = $pre['quantity'];
                                $releaseQty = round($releaseQty * (10 ** $preQty)) / 10 ** $preQty;
                            }

                            break;
                        }
                    }
                }
            }


            if ($finished) {
                
                if ($releaseIndex === null) {
                    $this->log("matched -> stoppending eventprofit: " . $this->event->{LAB_RESULT_EVENT_PROFIT} . " close: " . $closePrice . " profit: " . $this->event->{LAB_RESULT_PROFIT} . " lastprice: " . $this->event->{LAB_RESULT_LAST_PRICE} . "high: " . $high);
                    $editData[LAB_RESULT_STATUS] = LAB_RESULT_STATUS_STOP_PENDING;
                } else {
                    $this->log("matched -> releaseWaitting eventprofit: " . $this->event->{LAB_RESULT_EVENT_PROFIT} . " close: " . $closePrice . " profit: " . $this->event->{LAB_RESULT_PROFIT} . " lastprice: " . $this->event->{LAB_RESULT_LAST_PRICE} . "high: " . $high);
                    $editData[LAB_RESULT_STATUS] = LAB_RESULT_STATUS_RELEASE_WAITTING;
                    $editData[LAB_RESULT_ORDER_QTY] = $releaseQty;
                    $this->releaseBase = $profitReal;
                }
            }else{
                // $this->log("matched eventprofit: " . $this->event->{LAB_RESULT_EVENT_PROFIT} . " close: " . $closePrice . " profit: " . $this->event->{LAB_RESULT_PROFIT} . " lastprice: " . $this->event->{LAB_RESULT_LAST_PRICE} . "high: " . $high);
            }

            $editData[LAB_RESULT_BASEPROFIT] = $this->baseProfit;
            $editData[LAB_RESULT_PROFIT] = $profitReal;

            $this->updateEvent([
                DATA_KEY => [[[LAB_RESULT_ID, '=', $event->{LAB_RESULT_ID}]]],
                DATA_EDITOR => $editData
            ], $finished);



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

                if ($isTakeprofit) {
                    $this->labPendingStop = $time + 0.25 * 1000;
                } else {
                    $this->labPendingStop = $time + 0.5 * 1000;
                }
                $this->isTelegram && Telegram::send(TELE_ICON_STOP . " [" . $this->campaign->{LAB_CAMPAIGN_NAME} . "] #" . $this->symbol
                    . " Stop \n- Reason: " . $editData[LAB_RESULT_PARAMS], TELE_SIMULATE);

                return Reply::make(true, 'Pending Event', true);
            }
        }


        if ($status == LAB_RESULT_STATUS_STOP_PENDING) {

            if ($time < $this->labPendingStop) {
                return Reply::make(true, 'Pending Event', true);
            }

            $matchedPrice = doubleval($event->{LAB_RESULT_MATCHED_PRICE});
            $price = $closePrice;

            $commitPercent = 0.04;
            $commit = $commitPercent * $price * doubleval($this->event->{LAB_RESULT_MATCHED_QTY}) / 100;
            if ($type == LAB_RESULT_TYPE_LONG) {
                $pnl = ($price - $matchedPrice) * doubleval($this->event->{LAB_RESULT_MATCHED_QTY});
            } else {
                $pnl = ($matchedPrice - $price) * doubleval($this->event->{LAB_RESULT_MATCHED_QTY});
            }

            $this->eventOrder->add([[
                LAB_ORDER_ACTION => $this->event->{LAB_RESULT_ID},
                LAB_ORDER_TIME => $time,
                LAB_ORDER_PRICE => $price,
                LAB_ORDER_SYMBOL => $this->symbol,
                LAB_ORDER_QTY =>  doubleval($this->event->{LAB_RESULT_MATCHED_QTY}),
                LAB_ORDER_TYPE => $type == LAB_RESULT_TYPE_LONG ? LAB_RESULT_TYPE_SHORT : LAB_RESULT_TYPE_LONG,
                LAB_ORDER_PHASE => $phase,
                LAB_ORDER_COMMIT => $commit,
                LAB_ORDER_PNL => $pnl,
            ]]);

            $pnlData = $this->calCommit($this->event);
            $commit = $pnlData['commit'];
            $pnl = $pnlData['pnl'];
            $isProfit = $pnl > $commit;
            $package = $this->event->{LAB_RESULT_BUDGET};
            $realPNL = $pnl - $commit;
            $realProfit = ($realPNL) * 100 / $package;
            $invest = doubleval($this->event->{LAB_RESULT_MATCHED_QTY}) * doubleval($this->event->{LAB_RESULT_MATCHED_PRICE});
            $profit = $realPNL * 100 / $invest;

            $editData = [
                LAB_RESULT_PENDING => '0',
                LAB_RESULT_STATUS => $isProfit ? LAB_RESULT_STATUS_TAKEPROFIT : LAB_RESULT_STATUS_STOPLOSS,
                LAB_RESULT_SELL_PRICE => $price,
                LAB_RESULT_SELL_TIME => $time,
                LAB_RESULT_REAL_PROFIT => $realProfit,
                LAB_RESULT_EVENT_PROFIT => $profit,
                LAB_RESULT_INTERVAL => $time - $this->event->{LAB_RESULT_CHART},
                LAB_RESULT_REAL_PNL => $realPNL,
            ];

            $this->updateEvent([
                DATA_KEY => [[[LAB_RESULT_ID, '=', $event->{LAB_RESULT_ID}]]],
                DATA_EDITOR => $editData
            ], true);

            $this->labPendingTime = $time;

            if (isset($this->params[LAB_CAMPAIGN_PARAMS_LOG_ORDER]) && $this->params[LAB_CAMPAIGN_PARAMS_LOG_ORDER] == 1) {
                $this->eventLog->add([[

                    LAB_ELOG_TIME => $time,
                    LAB_ELOG_CAMPAIGN => $this->campaign->{LAB_CAMPAIGN_ID},
                    LAB_ELOG_SYMBOL => $this->symbol,
                    LAB_ELOG_MATCHED => $type,
                    LAB_ELOG_CHART => $khung1m[0]->{LAB_CANDLE_1M_OPEN_TIME},
                    LAB_ELOG_RESULT => json_encode([
                        'Status' => $isProfit ? 'Take profit' : 'Stoploss',
                    ]),
                    LAB_ELOG_PROFIT => $this->event->{LAB_RESULT_PROFIT},
                    LAB_ELOG_BASE => json_encode($this->data)
                ]]);
            }

            $this->isTelegram && Telegram::send(
                "============================="
                    . "\n" . ($isProfit ? TELE_ICON_TAKEPROFIT : TELE_ICON_STOPLOSS) . " " . $this->campaign->{LAB_CAMPAIGN_NAME} . " - TỔNG KẾT"
                    . "\nSymbol: " . $this->symbol
                    . "\nBắt đầu: " . date("d/m/Y H:i:s", $event->{LAB_RESULT_CHART} / 1000)
                    . "\nKết thúc: " . date("d/m/Y H:i:s", $time / 1000)
                    . "\nLoại vị thế: " . ($type == LAB_TYPE_LONG ? "Long" : "Short")
                    . "\nVốn đầu tư: " . $event->{LAB_RESULT_BUDGET}
                    . "\nPhase tối đa: " . $event->{LAB_RESULT_PHASE}
                    . "\nLợi nhuận trên vốn: " . $realProfit . " %"
                    . "\nLợi nhuận ròng: " . $realPNL . " USDT"
                    . "\n=============================",
                TELE_SIMULATE
            );

            $this->updateProfit($realPNL);
            $arrangeResult = $this->autoArrange($realPNL);
            if (!$arrangeResult['result']) {
                $ms = TELE_ICON_WARNING . " [" . $this->account->{TESTNET_ACCOUNT_NAME} . "] " . $arrangeResult['message'];
                $this->isTelegram && Telegram::send($ms, TELE_SIMULATE);
            }

            $this->log('stoppending -> finished: close ' . $price, $time);

            return Reply::make(true, 'No Pending Event', false);
        }

        if ($status == LAB_RESULT_STATUS_ENTER_WAITTING) {

            $isMakeOrder = false;
            $isCancle = false;
            $cancleReason = '';

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
                $enterPrice = doubleval($event->{LAB_RESULT_ENTER_PRICE});

                if ($enterStep > 0) {

                    $checkPrice = $this->getCheckWaitingPrice($event, $closePrice, $high, $low, $openTime);
                    $enterPrice = doubleval($event->{LAB_RESULT_ENTER_PRICE});

                    if ($type == LAB_RESULT_TYPE_LONG) {

                        $down = ($enterPrice - $checkPrice['min']) * 100 / $enterPrice;
                        $downBase = ($enterPrice - $this->enterBase) * 100 / $enterPrice;
                        $currentDown = ($enterPrice - $closePrice) * 100 / $enterPrice;

                        if ($down > ($downBase + $enterStep)) {
                            $downBase = floor($down / $enterStep) * $enterStep;
                            $this->enterBase = $enterPrice - ($enterPrice *  $downBase / 100);
                        }

                        if ($downBase - $currentDown >= $enterBack) {
                            if ($currentDown >= 0 || $this->getFlowData($flowName, 'allow_negative_price_rate')) {
                                $isMakeOrder = true;
                                $this->log("Waiting -> enterpending down: $down downbase: $downBase currentDown: $currentDown enterback:$enterBack");
                            } else {
                                $isCancle = true;
                                $cancleReason = 'Do not allow negative price rate';
                            }
                        }else{
                            $this->log("Waiting down: $down downbase: $downBase currentDown: $currentDown enterback:$enterBack");
                        }
                    } else if ($type == LAB_RESULT_TYPE_SHORT) {

                        $up = ($checkPrice['max'] - $enterPrice) * 100 / $enterPrice;
                        $upBase = ($this->enterBase - $enterPrice) * 100 / $enterPrice;
                        $currentUp = ($closePrice - $enterPrice) * 100 / $enterPrice;

                        if ($up > ($upBase + $enterStep)) {
                            $upBase = floor($up / $enterStep) * $enterStep;
                            $this->enterBase = $enterPrice + ($enterPrice * $upBase / 100);
                        }

                        if ($upBase - $currentUp >= $enterBack) {

                            if ($currentUp >= 0 || $this->getFlowData($flowName, 'allow_negative_price_rate')) {
                                $isMakeOrder = true;
                            } else {
                                $isCancle = true;
                                $cancleReason = 'Do not allow negative price rate';
                            }
                        }
                    }

                    // $ms = "\n" . date("d/m/Y H:i:s", $time / 1000) . " enter price: " . (isset($enterPrice) ? $enterPrice : '');
                    // $ms .= "\n" . date("d/m/Y H:i:s", $time / 1000) . " enter base: " . $this->enterBase;
                    // $ms .= "\n" . date("d/m/Y H:i:s", $time / 1000) . " close price: " . $closePrice;
                    // $ms .= "\n" . date("d/m/Y H:i:s", $time / 1000) . " max change: " . (isset($up) ? $up : $down);
                    // $ms .= "\n" . date("d/m/Y H:i:s", $time / 1000) . " base change: " . (isset($upBase) ? $upBase : $downBase);
                    // $ms .= "\n" . date("d/m/Y H:i:s", $time / 1000) . " current change: " . (isset($currentUp) ? $currentUp : $currentDown);
                    // echo $ms;
                    // echo "\n===================\n";
                }
            }


            //Check max trade open limit

            if ($nextPhase == 0 && $isMakeOrder) {
                $freePossition = $this->getFreePosition($flowName);
                if (!is_null($freePossition) && $freePossition <= 0) {
                    $isCancle = true;
                    $isMakeOrder = false;
                    $cancleReason = 'Position limit. Free Position ' . $freePossition;
                }
                $freeSlot = $this->getFreeSlot($flowName);
                if (!is_null($freeSlot) && $freeSlot <= 0) {
                    $isCancle = true;
                    $isMakeOrder = false;
                    $cancleReason = 'Slot limit. Free slot ' . $freeSlot;
                }

                if ($isMakeOrder) {
                    $checkPossitionPriority = $this->checkPositionPriority($flowName, $freePossition);
                    if (!$checkPossitionPriority['result']) return $checkPossitionPriority;
                    if (!$checkPossitionPriority['data']) {
                        $isMakeOrder = false;
                    }
                }

                if ($isMakeOrder) {
                    $checkSlotPriority = $this->checkSlotPriority($flowName, $freeSlot);
                    if (!$checkSlotPriority['result']) return $checkSlotPriority;
                    if (!$checkSlotPriority['data']) {
                        $isMakeOrder = false;
                    }
                }
            }


            if ($isMakeOrder) {
                $this->makeOrder($event, $closePrice, $nextPhase, $time);
                return Reply::make(true, 'Pending Event', true);
            }

            if ($isCancle) {
                $this->updateEvent([
                    DATA_KEY => [[[LAB_RESULT_ID, '=', $event->{LAB_RESULT_ID}]]],
                    DATA_EDITOR => [
                        LAB_RESULT_STATUS => doubleval($event->{LAB_RESULT_MATCHED_QTY}) > 0 ? LAB_RESULT_STATUS_MATCHED_PART : LAB_RESULT_STATUS_CANCLE,
                        LAB_RESULT_PENDING => doubleval($event->{LAB_RESULT_MATCHED_QTY}) > 0 ? 1 : 0,
                        LAB_RESULT_PARAMS => $cancleReason,
                    ]
                ], true);

                $this->labPendingTime = $time;
                $this->isTelegram && Telegram::send(TELE_ICON_CANCEL
                    . " [" .  $this->campaign->{LAB_CAMPAIGN_NAME} . "] #"
                    . $this->symbol . " Cancel waitting order phase $nextPhase"
                    . " \n- Time:" . date("d/m/Y H:i:s", $time / 1000), TELE_SIMULATE);

                return Reply::make(true, 'Pending Event', $event->{LAB_RESULT_MATCHED_QTY} > 0);
            }
        }

        if ($status == LAB_RESULT_STATUS_MATCHED_PART) {

            if ($phase < ($this->getMatchLeng($flowName) - 1)) {

                $afterPhase = $this->getNextPhase($condition, $phase);
                if (!$afterPhase['result']) return $afterPhase;
                $afterPhase = $afterPhase['data'];

                $afterCondition = $this->getMatchCondition($flowName, $afterPhase);

                $checkResult = $this->compareOr($afterCondition['condition']);
                if (!$checkResult['result']) return $checkResult;
                if ($checkResult['data']) {

                    $this->log("matchedpart -> Waitting for phase: " . $afterPhase);

                    $enterStep = get($afterCondition['enter_step'], 0);
                    $enterRule = get($afterCondition['enter_rule'], null);

                    $closePrice = doubleval($khung1m[0]->{LAB_CANDLE_1M_CLOSE});

                    $baseonData = json_decode($event->{LAB_RESULT_BASE}, true);
                    $baseonData[$afterPhase] = $this->data;

                    $addData = [
                        LAB_RESULT_ENTER_TIME => $time,
                        LAB_RESULT_ENTER_PRICE => $closePrice,
                        LAB_RESULT_LOW => $khung1m[0]->{LAB_CANDLE_1M_LOW},
                        LAB_RESULT_HIGH => $khung1m[0]->{LAB_CANDLE_1M_HIGH},
                        LAB_RESULT_BASE => json_encode($baseonData),
                        LAB_RESULT_STATUS => LAB_RESULT_STATUS_ENTER_WAITTING,
                        LAB_RESULT_ORDER_PHASE => $afterPhase
                    ];

                    $this->updateEvent([
                        DATA_KEY => [[[LAB_RESULT_ID, '=', $event->{LAB_RESULT_ID}]]],
                        DATA_EDITOR => $addData
                    ], true);

                    if ($enterStep <= 0 && $enterRule === null) {
                        $this->makeOrder($event, $closePrice, $afterPhase, $time);
                    } else {
                        #set enter base then go to watting
                        $this->enterBase = $closePrice;
                        $ms = " [" .  $this->campaign->{LAB_CAMPAIGN_NAME} . "] #" . $this->symbol  . " Waitting for " . ($type == LAB_RESULT_TYPE_LONG ? 'Long' : 'Short') . " Order Pharse " . ($afterPhase)
                            . "\n-Time: " . date("d/m/Y H:i:s", $time / 1000)
                            . " \n- Close Price: " . $closePrice;

                        $this->isTelegram && Telegram::send(
                            TELE_ICON_WAITTING . $ms,
                            TELE_SIMULATE
                        );
                    }
                }
            } else {
                $this->updateEvent([
                    DATA_KEY => [[[LAB_RESULT_ID, '=', $event->{LAB_RESULT_ID}]]],
                    DATA_EDITOR => [
                        LAB_RESULT_STATUS => LAB_RESULT_STATUS_MATCHED,
                    ]
                ], true);
            }
        }

        if ($status == LAB_RESULT_STATUS_RELEASE_WAITTING) {

            $this->log('Release waitting closeprice:' . $closePrice);

            $releaseCondition = $this->getStopCondition($flowName, $event->{LAB_RESULT_ORDER_RELEASE});

            $isRelease = true;
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
                    // echo "check release step" . $this->releaseBase . "\n";
                    $matchedPrice = doubleval($event->{LAB_RESULT_MATCHED_PRICE});

                    if ($type == LAB_RESULT_TYPE_LONG) {
                        $maxProfit = ($high - $matchedPrice) * 100 / $matchedPrice;
                        $profit = ($closePrice - $matchedPrice) * 100 / $matchedPrice;
                    } else if ($type == LAB_RESULT_TYPE_SHORT) {
                        $maxProfit = ($matchedPrice - $low) * 100 / $matchedPrice;
                        $profit = ($matchedPrice - $closePrice) * 100 / $matchedPrice;
                    }

                    if ($maxProfit > ($this->releaseBase + $releaseStep)) {
                        $this->releaseBase = floor($maxProfit / $releaseStep) * $releaseStep;
                    }

                    if ($this->releaseBase - $profit > $releaseBack) {
                        $isRelease = true;
                    } else {
                        $isRelease = false;
                    }
                }
            }

            if ($isRelease) {

                if ($this->event->{LAB_RESULT_ORDER_QTY} == null) {
                    $releaseQty =  doubleval($this->event->{LAB_RESULT_MATCHED_QTY});
                } else {
                    $releaseQty =  doubleval($this->event->{LAB_RESULT_ORDER_QTY});
                }
                $totalQty = doubleval($this->event->{LAB_RESULT_MATCHED_QTY}) - $releaseQty;

                $this->updateEvent([
                    DATA_KEY => [[[LAB_RESULT_ID, '=', $event->{LAB_RESULT_ID}]]],
                    DATA_EDITOR => [
                        LAB_RESULT_STATUS => $totalQty > 0 ? LAB_RESULT_STATUS_RELEASE_PENDING : LAB_RESULT_STATUS_STOP_PENDING
                    ]
                ], true);

                $this->labPendingStop = $time + 0.25 * 1000;
            } else if ($isCancle) {

                $this->updateEvent([
                    DATA_KEY => [[[LAB_RESULT_ID, '=', $event->{LAB_RESULT_ID}]]],
                    DATA_EDITOR => [
                        LAB_RESULT_STATUS => doubleval($event->{LAB_RESULT_MATCHED_QTY}) > 0 ? LAB_RESULT_STATUS_MATCHED_PART : LAB_RESULT_STATUS_CANCLE,
                        LAB_RESULT_PENDING => doubleval($event->{LAB_RESULT_MATCHED_QTY}) > 0 ? 1 : 0,
                        LAB_RESULT_ORDER_RELEASE => NULL
                    ]
                ], true);
                $this->labPendingTime = $time;
                $this->isTelegram && Telegram::send(TELE_ICON_CANCEL . " [" . $this->campaign->{LAB_CAMPAIGN_NAME} . "] #" . $this->symbol . " Cancel waitting Release Phase $phase \n- Time:" . date("d/m/Y H:i:s"), TELE_SIMULATE);
            }
            return Reply::make(true, 'Pending Event', true);
        }

        if ($status == LAB_RESULT_STATUS_RELEASE_PENDING) {
            $this->log('Release pending closeprice:' . $closePrice);
            //Delay
            if ($time < $this->labPendingStop) {
                return Reply::make(true, 'Pending Event', true);
            }
            $matchedPrice = doubleval($this->event->{LAB_RESULT_MATCHED_PRICE});

            $commitPercent = 0.04;
            $commit = $commitPercent * $closePrice * doubleval($this->event->{LAB_RESULT_ORDER_QTY}) / 100;
            if ($type == LAB_RESULT_TYPE_LONG) {
                $pnl = ($closePrice - $matchedPrice) * doubleval($this->event->{LAB_RESULT_ORDER_QTY});
            } else {
                $pnl = ($matchedPrice - $closePrice) * doubleval($this->event->{LAB_RESULT_ORDER_QTY});
            }

            $releaseProfit = $pnl - $commit;

            $this->eventOrder->add([[
                LAB_ORDER_ACTION => $this->event->{LAB_RESULT_ID},
                LAB_ORDER_TIME => $time,
                LAB_ORDER_PRICE => $closePrice,
                LAB_ORDER_SYMBOL => $this->symbol,
                LAB_ORDER_QTY =>  doubleval($this->event->{LAB_RESULT_ORDER_QTY}),
                LAB_ORDER_TYPE => $type == LAB_RESULT_TYPE_LONG ? LAB_RESULT_TYPE_SHORT : LAB_RESULT_TYPE_LONG,
                LAB_ORDER_PHASE => $nextPhase,
                LAB_ORDER_COMMIT => $commit,
                LAB_ORDER_PNL => $pnl,
            ]]);



            $totalQty = doubleval($this->event->{LAB_RESULT_MATCHED_QTY}) - doubleval($this->event->{LAB_RESULT_ORDER_QTY});

            $this->event->{LAB_RESULT_MATCHED_QTY} = $totalQty;
            $this->updateEvent([
                DATA_KEY => [[[LAB_RESULT_ID, '=', $event->{LAB_RESULT_ID}]]],
                DATA_EDITOR => [
                    LAB_RESULT_STATUS => $nextPhase == ($this->getMatchLeng($flowName) - 1) ? LAB_RESULT_STATUS_MATCHED : LAB_RESULT_STATUS_MATCHED_PART,
                    LAB_RESULT_MATCHED_QTY => $totalQty,
                    LAB_RESULT_BASEPROFIT => $cfgBaseProfit,
                    LAB_RESULT_PHASE => $nextPhase,
                    LAB_RESULT_ORDER_RELEASE => NULL,
                    LAB_RESULT_EVENT_PROFIT => $this->calEventProfit(),
                    LAB_RESULT_LAST_PRICE => $closePrice
                ]
            ], true);

            // $this->updateProfit($releaseProfit);



            $this->isTelegram && Telegram::send(($pnl > $commit ? TELE_ICON_TAKEPROFIT : TELE_ICON_STOPLOSS)
                    . " [" . $this->campaign->{LAB_CAMPAIGN_NAME} . "] #" . $this->symbol . " Release and comeback phase $nextPhase"
                    . "\n- Type: " . ($type == LAB_RESULT_TYPE_LONG ? "Short" : "Long")
                    . "\n- Time: " . date("d/m/Y H:i:s", $time / 1000)
                    . "\n- Price: " . $closePrice
                    . "\n- Real Profit: " . ($releaseProfit),
                TELE_SIMULATE
            );
        }



        return Reply::make(true, 'Pending Event', true);
    }


    private function getNextPhase($condition, $currentPhase)
    {
        if (!isset($condition['next_phase'])) return Reply::make(true, 'next phase is not configured', $currentPhase + 1);
        $nextPhase = $this->caculateElement($condition['next_phase']);
        return $nextPhase;
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
        $this->log("Make an order " . $closePrice, $time);
        $pre = $this->getPrecision($this->symbol);
        $this->maker = false;
        $type = $action->{LAB_RESULT_TYPE};
        $flowName = $this->getFlowName($action);
        $condition = $this->getMatchCondition($flowName, $phase);

        $enterPriceSetting = get($condition['enter_price'], 'market');
        $margin = get($condition['margin'], $this->getFlowData($flowName, 'margin'));

        if ($margin < doubleval($action->{LAB_RESULT_MARGIN})) {
            return Reply::make(false, 'Can not reduce margin');
        }

        if (is_numeric($enterPriceSetting)) {
            $enterPrice = $closePrice * $enterPriceSetting / 100;
        } else {
            $enterPrice = $closePrice;
        }

        if (isset($pre['tickSize'])) {
            $enterPrice = round($enterPrice / $pre['tickSize']) * $pre['tickSize'];
        }

        $budget = $this->getInvestBudget();
        $phaseBudget = $budget * get($condition['enter_package'], 100) / 100;
        $qty = $phaseBudget / $enterPrice;
        $qty = $qty * $margin;
        $preQty = $pre['quantity'];
        $qty = round($qty * (10 ** $preQty)) / 10 ** $preQty;

        $this->updateEvent(
            [
                DATA_KEY => [[[LAB_RESULT_ID, '=', $action->{LAB_RESULT_ID}]]],
                DATA_EDITOR => [
                    LAB_RESULT_ORDER_PRICE => $enterPrice,
                    LAB_RESULT_ORDER_TIME => $time,
                    LAB_RESULT_ORDER_QTY => $qty,
                    LAB_RESULT_ORDER_PHASE => $phase,
                    LAB_RESULT_STATUS => $phase == 0 ? LAB_RESULT_STATUS_PENDING : LAB_RESULT_STATUS_PHASE_PENDING,
                    LAB_RESULT_LOW => $this->data[$this->symbol]['1m'][0]->{LAB_CANDLE_1M_LOW},
                    LAB_RESULT_HIGH => $this->data[$this->symbol]['1m'][0]->{LAB_CANDLE_1M_HIGH},
                    LAB_RESULT_MARGIN => $margin,
                    LAB_RESULT_BUDGET => $budget,
                ]
            ],
            true
        );
        $this->isTelegram && Telegram::send(
            ($type == LAB_RESULT_TYPE_SHORT ? TELE_ICON_SHORT : TELE_ICON_LONG) . " [" . $this->campaign->{LAB_CAMPAIGN_NAME} . "] #" . $this->symbol . " " . ($type == LAB_RESULT_TYPE_SHORT ? 'Short' : 'Long') . " Order Pharse $phase "
                . "\n- Time:" . date("d/m/Y H:i:s", $time / 1000)
                . "\n- Close Price:" . $closePrice
                . "\n- Enter Price:" . $enterPrice,
            TELE_SIMULATE
        );
    }


    private function getCheckWaitingPrice($event, $price, $high, $low, $open_time)
    {
        if ($open_time > $event->{LAB_RESULT_ENTER_TIME}) return ['max' => $high, 'min' => $low];
        $max = $price;
        $min = $price;
        if ($high != $event->{LAB_RESULT_HIGH}) $max = $high;
        if ($low != $event->{LAB_RESULT_LOW}) $min = $low;

        return ['max' => $max, 'min' => $min];
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

    private function calCommit($event)
    {
        $id = $event->{LAB_RESULT_ID};
        $type = $event->{LAB_RESULT_TYPE};

        $commit = 0;
        $PNL = 0;

        $postitionQty = 0;
        $avgPrice = 0;

        $result = $this->eventOrder->read([[[LAB_ORDER_ACTION, '=', $id]]]);
        if ($result['result']) {
            foreach ($result['data'] as $data) {
                $commit += doubleval($data->{LAB_ORDER_COMMIT});
                $PNL += doubleval($data->{LAB_ORDER_PNL});
                if ($type == $data->{LAB_ORDER_TYPE}) {
                    $avgPrice = ($postitionQty * $avgPrice + doubleval($data->{LAB_ORDER_QTY}) * doubleval($data->{LAB_ORDER_PRICE})) / ($postitionQty + doubleval($data->{LAB_ORDER_QTY}));
                    $postitionQty += doubleval($data->{LAB_ORDER_QTY});
                } else {
                    $postitionQty -= doubleval($data->{LAB_ORDER_QTY});
                }
            }
        }
        $this->log("Call commit " . json_encode(['commit' => $commit, "pnl" => $PNL, 'position_qty' => $postitionQty, 'position_price' => $avgPrice]));
        return ['commit' => $commit, "pnl" => $PNL, 'position_qty' => $postitionQty, 'position_price' => $avgPrice];
    }

    private function calEventProfit()
    {
        $event = $this->event;
        $commit = $this->calCommit($event);
        $realPNL = $commit['pnl'] - $commit['commit'];
        $budget = $commit['position_qty'] * $commit['position_price'];
        $eventProfit = 0;
        if ($budget > 0) {
            $eventProfit = ($realPNL) * 100 / $budget;
        }
        return $eventProfit;
    }


    //=============================================


    private function updateProfit($profit)
    {

        if ($profit > 0) {
            $this->accountModel->db()->where(LAB_ACCOUNT_ID, '=', $this->account->{LAB_ACCOUNT_ID})->increment(LAB_ACCOUNT_BALANCE, $profit);
        } else {
            $this->accountModel->db()->where(LAB_ACCOUNT_ID, '=', $this->account->{LAB_ACCOUNT_ID})->decrement(LAB_ACCOUNT_BALANCE, -$profit);
        }
        $this->log("Update profit: " . $profit);
    }

    private function autoArrange($profit = 0)
    {

        $startTime = microtime(true);

        $account = $this->accountModel->read([[[LAB_ACCOUNT_ID, '=', $this->account->{LAB_ACCOUNT_ID}]]]);

        if (!$account['result'] || !isset($account['data'][0])) {
            return Reply::make(false, 'No account');
        }
        $account = $account['data'][0];

        if ($account->{LAB_ACCOUNT_COMPOUND} == 1) {

            $campaigns = $this->campaignModel->read([[[LAB_CAMPAIGN_ACCOUNT, '=', $account->{LAB_ACCOUNT_ID}]]]);
            if (!$campaigns['result']) return $campaigns;
            $campaigns = $campaigns['data'];

            $reserve = get($account->{LAB_ACCOUNT_RESERVE}, 0);

            $used = 0;

            foreach ($campaigns as $campaign) {
                $used += doubleval($campaign->{LAB_CAMPAIGN_BUDGET});
            }

            $balance = doubleval($account->{LAB_ACCOUNT_BALANCE});
            $balance = $balance * (100 - $reserve) / 100;

            $free = $balance - $used;

            if ($free <= 0) {
                $ms = TELE_ICON_WARNING . " [" . $this->campaign->{LAB_CAMPAIGN_NAME} . "] auto arrange fail"
                    . "\n- Symbol: " . $this->symbol
                    . "\n- Free: " . round($free * 1000) / 1000 . " $"
                    . "\n- Time: " . date("d/m/Y H:i:s");
                // echo $ms . "\n";
                $this->isTelegram && Telegram::send($ms, TELE_SIMULATE);

                return Reply::make(true, 'Free less than 0');
            }

            $added = floor($free * 1000 / count($campaigns)) / 1000;

            foreach ($campaigns as $campaign) {
                $result = $this->campaignModel->edit([
                    DATA_KEY => [[[LAB_CAMPAIGN_ID, '=', $campaign->{LAB_CAMPAIGN_ID}]]],
                    DATA_EDITOR => [LAB_CAMPAIGN_BUDGET => doubleval($campaign->{LAB_CAMPAIGN_BUDGET}) + $added]
                ]);
                if (!$result['result']) return $result;
            }

            $ms = TELE_ICON_WARNING . " [" . $this->campaign->{LAB_CAMPAIGN_NAME} . "] auto arrange successfully"
                . "\n- Symbol: " . $this->symbol
                . "\n- Free: " . round($free * 1000) / 1000 . " $"
                . "\n- Added: " . round($added * 1000) / 1000 . " $"
                . "\n- Excute Time: " . round((microtime(true) - $startTime) * 100) / 100 . ' s'
                . "\n- Time: " . date("d/m/Y H:i:s");
            // echo $ms . "\n";
            $this->isTelegram && Telegram::send($ms, TELE_SIMULATE);

            $this->log("Auto arrange: blance $balance free: $free added: $added");
            return Reply::make(true, 'Success');
        } else {

            if ($this->campaign->{LAB_CAMPAIGN_COMPOUND} == 1) {

                if ($profit > 0) {
                    $this->campaignModel->db()->where(LAB_CAMPAIGN_ID, '=', $this->campaign->{LAB_CAMPAIGN_ID})->increment(LAB_CAMPAIGN_BUDGET, $profit);
                } else {
                    $this->campaignModel->db()->where(LAB_CAMPAIGN_ID, '=', $this->campaign->{LAB_CAMPAIGN_ID})->decrement(LAB_CAMPAIGN_BUDGET, -$profit);
                }

                $ms = TELE_ICON_WARNING . " [" . $this->campaign->{LAB_CAMPAIGN_NAME} . "] update budget successfully"
                    . "\n- Symbol: " . $this->symbol
                    . "\n- Added: " . round($profit * 1000) / 1000 . " $"
                    . "\n- Excute Time: " . round((microtime(true) - $startTime) * 100) / 100 . ' s'
                    . "\n- Time: " . date("d/m/Y H:i:s");
                // echo $ms . "\n";
                $this->isTelegram && Telegram::send($ms, TELE_SIMULATE);

                return Reply::make(true, 'Success');
            }
        }

        return Reply::make(true, 'Compound is diabled');
    }



    private function getInvestBudget()
    {

        $campaignData = $this->campaignModel->read([[[LAB_CAMPAIGN_ID, '=', $this->campaign->{LAB_CAMPAIGN_ID}]]]);
        if (!$campaignData['result'] || !isset($campaignData['data'][0])) {
            return 0;
        }

        $campaignData = $campaignData['data'][0];
        $this->campaign = $campaignData;
        return doubleval($campaignData->{LAB_CAMPAIGN_BUDGET}) * doubleval($campaignData->{LAB_CAMPAIGN_ACTIVE_BUDGET}) / 100;
    }


    /**
     * @return String FlowName
     */
    private function getFlowName($event)
    {
        $flow = $event->{LAB_RESULT_FLOW};
        $strategy = $event->{LAB_RESULT_STRATEGY};
        $flowName = $strategy . "--" . $flow;
        return $flowName;
    }


    private function getFreePosition($flowName)
    {
        $maxTrades = $this->getFlowData($flowName, 'max_open_trades');
        if (is_null($maxTrades) || $maxTrades == '') return null;
        $taken = $this->countPosition();
        $freeSlot = $maxTrades - $taken;
        return $freeSlot;
    }

    private function getFreeSlot($flowName)
    {
        $maxTrades = $this->getFlowData($flowName, 'strategy_slot');
        if (is_null($maxTrades) || $maxTrades == '') return null;
        $taken = $this->countSlot($flowName);
        $freeSlot = $maxTrades - $taken;
        return $freeSlot;
    }


    /**
     * @return Int Number of slot of strategy is taken
     */
    private function countSlot($flowName)
    {
        $strategyId = $this->getFlowData($flowName, 'strategy');
        $openTrades = $this->eventModel->count([[
            [LAB_RESULT_PENDING, '=', 1],
            [LAB_RESULT_ACCOUNT, '=', $this->account->{LAB_ACCOUNT_ID}],
            [LAB_RESULT_STRATEGY, '=', $strategyId]
        ]]);
        if (!$openTrades['result']) return 0;
        $openTrades = intval($openTrades['data']);

        $waittingTrades = $this->eventModel->count([[
            [LAB_RESULT_PENDING, '=', 1],
            [LAB_RESULT_ACCOUNT, '=', $this->account->{LAB_ACCOUNT_ID}],
            [LAB_RESULT_STRATEGY, '=', $strategyId],
            [LAB_RESULT_STATUS, '=', LAB_RESULT_STATUS_ENTER_WAITTING],
            [LAB_RESULT_MATCHED_QTY, '=', 0]
        ]]);
        if (!$waittingTrades['result']) return 0;
        $waittingTrades = intval($waittingTrades['data']);

        return $openTrades - $waittingTrades;
    }

    /**
     * @return Int Number of postion opened
     */
    private function countPosition()
    {
        $openTrades = $this->eventModel->count([[
            [LAB_RESULT_PENDING, '=', 1],
            [LAB_RESULT_ACCOUNT, '=', $this->account->{LAB_ACCOUNT_ID}]
        ]]);
        if (!$openTrades['result']) return 0;
        $openTrades = intval($openTrades['data']);

        $waittingTrades = $this->eventModel->count([[
            [LAB_RESULT_PENDING, '=', 1],
            [LAB_RESULT_ACCOUNT, '=', $this->account->{LAB_ACCOUNT_ID}],
            [LAB_RESULT_STATUS, '=', LAB_RESULT_STATUS_ENTER_WAITTING],
            [LAB_RESULT_MATCHED_QTY, '=', 0]
        ]]);
        if (!$waittingTrades['result']) return 0;
        $waittingTrades = intval($waittingTrades['data']);

        return $openTrades - $waittingTrades;
    }

    /**
     * @return Array symbol and priority
     */

    private function getPriorityIndex()
    {
        $campaigns = $this->campaignModel->read([[[LAB_CAMPAIGN_ACCOUNT, '=', $this->account->{LAB_ACCOUNT_ID}]]]);
        if (!$campaigns['result']) return $campaigns;
        $campaigns = $campaigns['data'];
        $priorityIndex = [];
        foreach ($campaigns as $campaign) {
            $priorityIndex[$campaign->{LAB_CAMPAIGN_SYMBOL}] = doubleval($campaign->{LAB_CAMPAIGN_PRIORITY});
        }
        return Reply::make(true, 'success', $priorityIndex);
    }

    /**
     * Check if the symbol is allowed to make order check max_open_trades
     */
    private function checkPositionPriority($flowName, $freeSlot = null)
    {

        if (is_null($freeSlot)) $freeSlot = $this->getFreePosition($flowName);
        if (is_null($freeSlot)) {
            return Reply::make(true, 'success', true);
        }

        $priority = get($this->priority[$this->symbol], 0);
        $waittingTrades = $this->eventModel->read([[
            [LAB_RESULT_PENDING, '=', 1],
            [LAB_RESULT_STATUS, '=', LAB_RESULT_STATUS_ENTER_WAITTING],
            [LAB_RESULT_ACCOUNT, '=', $this->account->{LAB_ACCOUNT_ID}],

        ]]);

        if (!$waittingTrades['result']) return $waittingTrades;
        $waittingTrades = $waittingTrades['data'];
        $takenSlot = 0;
        foreach ($waittingTrades as $waitting) {
            $symbol = $waitting->{LAB_RESULT_SYMBOL};
            $otherPriority = get($this->priority[$symbol], 0);
            if (intval($otherPriority) > intval($priority)) {
                $takenSlot++;
            }
        }
        return Reply::make(true, 'success', $freeSlot > $takenSlot);
    }

    /**
     * Check if the symbol is allowed to make order check strategy_slot
     */
    private function checkSlotPriority($flowName, $freeSlot = null)
    {

        if (is_null($freeSlot)) $freeSlot = $this->getFreeSlot($flowName);
        if (is_null($freeSlot)) {
            return Reply::make(true, 'success', true);
        }

        $strategyId = $this->getFlowData($flowName, 'strategy');
        $priority = get($this->priority[$this->symbol], 0);
        $waittingTrades = $this->eventModel->read([[
            [LAB_RESULT_PENDING, '=', 1],
            [LAB_RESULT_STATUS, '=', LAB_RESULT_STATUS_ENTER_WAITTING],
            [LAB_RESULT_ACCOUNT, '=', $this->account->{LAB_ACCOUNT_ID}],
            [LAB_RESULT_STRATEGY, '=', $strategyId]
        ]]);

        if (!$waittingTrades['result']) return $waittingTrades;
        $waittingTrades = $waittingTrades['data'];
        $takenSlot = 0;
        foreach ($waittingTrades as $waitting) {
            $symbol = $waitting->{LAB_RESULT_SYMBOL};
            $otherPriority = get($this->priority[$symbol], 0);
            if (intval($otherPriority) > intval($priority)) {
                $takenSlot++;
            }
        }
        return Reply::make(true, 'success', $freeSlot > $takenSlot);
    }

    private function checkBlacklist($flowName)
    {
        $blacklist = $this->getFlowData($flowName, 'blacklist');
        if (!is_array($blacklist)) return true;
        $symbol = $this->campaign->{LAB_CAMPAIGN_SYMBOL};
        return !in_array($symbol, $blacklist);
    }

    private function checkLiquidation()
    {
        $khung1m = $this->data[$this->symbol]['1m'];
        $high = doubleval($khung1m[0]->{LAB_CANDLE_1M_HIGH});
        $low = doubleval($khung1m[0]->{LAB_CANDLE_1M_LOW});
        $event = $this->event;
        $matchedQty = doubleval($event->{LAB_RESULT_MATCHED_QTY});
        $matchedPrice = doubleval($event->{LAB_RESULT_MATCHED_PRICE});
        $margin = doubleval($event->{LAB_RESULT_MARGIN});
        if ($margin == 0) $margin = 1;

        $invest = $matchedQty * $matchedPrice / $margin;
        if ($event->{LAB_RESULT_TYPE} == LAB_RESULT_TYPE_LONG) {
            $worstPrice = $low;
            $loss = ($matchedPrice - $worstPrice) * $matchedQty;
        } else {
            $worstPrice = $high;
            $loss = ($high - $matchedPrice) * $matchedQty;
        }

        $liquid = $loss > ($invest * 90 / 100);

        return $liquid;
    }

    private $needUpdateEvent = 0;
    private function updateEvent($editData, $force = true)
    {
        if ($this->event) {
            $dataEditor = $editData[DATA_EDITOR];
            foreach ($dataEditor as $key => $value) {
                $this->event->{$key} = $value;
            }
        }
        if ($force || $this->needUpdateEvent <= 0) {
            $this->needUpdateEvent = 200;
            return $this->eventModel->edit($editData);
        } else {
            $this->needUpdateEvent--;
        }
        return Reply::make(true, 'success', $this->event);
    }


    private function log($mess, $time = null)
    {
        return;
        if($this->symbol != 'AAVEUSDT') return;
        if(is_null($time)) $time = $this->time;
        $name = $this->campaign->{LAB_CAMPAIGN_NAME};
        echo date('m/d/Y H:i:s', floor($time / 1000)) . ": [$name] $mess\n";
    }
}

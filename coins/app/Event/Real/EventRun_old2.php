<?php

namespace App\Event\Real;

use App\Event\EventFunc;
use App\Helpers\Admin\Binancer;
use App\Helpers\Admin\Telegram;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;

class EventRun_old2
{

    use EventFunc;

    function __construct($symbol, $account)
    {
        try {
            //code...
            date_default_timezone_set('Asia/Ho_Chi_Minh');
            $this->symbol = $symbol;
            $this->account = $account;

            // count number of makeorder fault
            $this->makeOrderFault = 0;

            $this->Candle1hModel = Models::get('Admin/Candle_1h');
            $this->Candle15mModel = Models::get('Admin/Candle_15m');
            $this->Candle3mModel = Models::get('Admin/Candle_3m');
            $this->Candle1mModel = Models::get('Admin/Candle_1m');
            $this->tradesModel = Models::get('Admin/Trades');
            $this->eventModel = Models::get('Admin/Actions');
            $this->paramModel = Models::get('Admin/Params');

            $this->StrategyModel = Models::get('Admin/Strategies');
            $this->altsCoinModel = Models::get('Admin/Change_24h');

            $this->enterBaseModel = Models::get('Admin/Log_enterbase');
            $this->profitBaseModel = Models::get('Admin/Log_profitbase');

            $this->volatilityModel = Models::get('Admin/Volatility');
            $this->volatilityData = [
                'data' => null,
                'time' => 0,
            ];

            $this->binancer = new Binancer($account);
            $this->binancer->getPrecision('');
            $result = $this->binancer->setMarginType($this->symbol);

            //Telegram bot

            $this->teleBot = get($this->binancer->getAccount()->{ACCOUNT_TELE_BOT}, null);
            $this->teleGrNotice = get($this->binancer->getAccount()->{ACCOUNT_TELE_GR_NOTICE}, null);
            $this->teleGrError = get($this->binancer->getAccount()->{ACCOUNT_TELE_GR_ERROR}, TELE_REAL_ERROR);
            $this->teleGrSummary = get($this->binancer->getAccount()->{ACCOUNT_TELE_GR_SUMMARY}, null);
            if ($this->teleGrSummary != null) $this->teleGrSummary = explode(',', $this->teleGrSummary);

            // get Trade data

            $tradeData = $this->tradesModel->read([[[TRADE_SYMBOL, '=', $symbol], [TRADE_ACCOUNT, '=', $account]]]);
            if (!$tradeData['result'] || !isset($tradeData['data'][0])) {
                $ms = " [ ERROR ] " . $this->binancer->getAccount()->{ACCOUNT_NAME} . " #" . $this->symbol  . " No Trade Data";
                echo $ms . "\n";
                Telegram::send(TELE_ICON_ERROR . $ms, $this->teleGrError, $this->teleBot);
                return;
            }

            $tradeData = $tradeData['data'][0];
            $this->tradeData = $tradeData;

            $params = $tradeData->{TRADE_PARAM};
            $params = json_decode($params, true);
            if (!$params) $params = [];
            $this->params = $params;

            $strategyId = $tradeData->{TRADE_STRATEGY};
            $strategyDB = $this->StrategyModel->read([[[STRATEGY_ID, '=', $strategyId]]]);
            $this->strategyId = $strategyId;
            if (!$strategyDB['result']) Reply::finish($strategyDB);
            if (!isset($strategyDB['data'][0])) Reply::finish(false, 'Can not find any Strategy');

            $strategyDB = $strategyDB['data'][0];
            $strategyData = json_decode($strategyDB->{STRATEGY_CONTENT}, true);
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

            $this->data[$this->symbol]['1m'] = [];

            $this->frame = [];
            $this->event = null;

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
            $this->side = get($tradeData->{TRADE_SIDE}, 'BOTH');

            //save priority indexed
            $this->priority = [];
        } catch (\Exception $th) {
            $ms = $th->getFile() . " " . $th->getLine() . " " . $th->getMessage();
            echo $ms . "\n";
            Telegram::send(TELE_ICON_ERROR . $ms, $this->teleGrError, $this->teleBot);
            $this->stopService();
        }
    }


    private function getTotalBudget()
    {
        $tradeData = $this->tradesModel->read([[[TRADE_ACCOUNT, '=', $this->account]]]);
        if (!$tradeData['result']) {
            $ms = " [ ERROR ] " . $this->binancer->getAccount()->{ACCOUNT_NAME} . " #" . $this->symbol  . " Can not get total budget";
            echo $ms . "\n";
            Telegram::send(TELE_ICON_ERROR . $ms, $this->teleGrError, $this->teleBot);
            return;
        }
        $tradeData = $tradeData['data'];
        $total = 0;
        foreach ($tradeData as $trade) {
            $total += doubleval($trade->{TRADE_BUDGET});
        }
        return $total;
    }


    private function checkTakeStop()
    {
        $labEvent =  $this->eventModel->read([[
            [ACTION_SYMBOL, '=', $this->symbol],
            [ACTION_PENDING, '=', 1],
            [ACTION_ACCOUNT, '=', $this->account]
        ]]);
        if (!$labEvent['result'] || !isset($labEvent['data'][0])) {
            return Reply::make(true, 'No Pending Event', false);
        }

        $labEvent = $labEvent['data'][0];
        $this->event = $labEvent;

        $condition = $this->getMatchCondition($labEvent->{ACTION_FLOW}, $labEvent->{ACTION_PHASE});

        $stoploss = get($condition['stoploss'], $this->cfgStoploss);
        $takeprofit = get($condition['takeprofit'], $this->cfgTakeprofit);

        $stopTakeResult = $this->binancer->createTakeStop(
            $this->symbol,
            $labEvent->{ACTION_MATCHED_PRICE},
            $labEvent->{ACTION_TYPE} == ACTION_TYPE_LONG ? 'BUY' : 'SELL',
            $stoploss,
            $takeprofit
        );

        return $stopTakeResult;
    }

    private function getVolatility()
    {
        $crTime = time();
        if ($this->volatilityData['data'] == null || ($crTime - $this->volatilityData['time']) > 30) {
            $data = $this->volatilityModel->read([[[VOLATILITY_SYMBOL, '=', $this->symbol]]]);
            if (!$data['result']) return $data;
            if (!isset($data['data'][0])) return Reply::make(true, 'Can not find any volatility data', null);
            $this->volatilityData['data'] = $data['data'][0];
            $this->volatilityData['time'] = $crTime;
        }

        return Reply::make(true, 'success', $this->volatilityData['data']);
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
        //     if (!isset($altCoinData['data'][0])) return Reply::make(false, 'No Alts Coin Data at ' . date("d/m/Y H:i:s", $time / 1000));
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
                return Reply::make(true, $struct, doubleval($this->event->{ACTION_MATCHED_TIME}));
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
            $column = 'action_' . $column;
            $percent = doubleval(get($struct['percent'], 100));
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

            for ($i = 0; $i <= $index; $i++) {
                $isStop = $this->compareOr($condition, $i);
                if ($isStop) {
                    $data = $data = $this->data;
                    if (!isset($data[$symbol])) return Reply::make(false, 'Can not get Data ' . $symbol);
                    if (!isset($data[$symbol][$frame])) return Reply::make(false, "Can not get Data $symbol $frame");
                    if (!isset($data[$symbol][$frame][$i])) return Reply::make(false, "Can not get Data $symbol $frame $i");
                    if (!isset($data[$symbol][$frame][$i]->{$column})) return Reply::make(false, "Can not get Data $symbol $frame $i $column");;

                    if (is_numeric($data[$symbol][$frame][$i]->{$column}))
                        return Reply::make(true, $des, doubleval($data[$symbol][$frame][$i]->{$column}) * $percent / 100);
                    return Reply::make(true, $des, $data[$symbol][$frame][$i]->{$column});
                }
            }
            return Reply::make(true, $des, false);
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

                if (is_array($stop)) {
                    $isStop = $this->compareOr($stop, $i);
                    if (!$isStop['result']) return $isStop;


                    if ($isStop['data']) {
                        // print_r($isStop);
                        // echo date("d/m/Y H:i:s", time()) ."_stop_". $needStop. "_". $cross . "\n";
                        return Reply::make(true, $des, $cross);
                    }
                }

                $newValue1 = doubleval($frameData[$i - 1]->{$column1});
                $newValue2 = doubleval($frameData[$i - 1]->{$column2});

                $oldValue1 = doubleval($frameData[$i]->{$column1});
                $oldValue2 = doubleval($frameData[$i]->{$column2});

                if (($newValue1 - $newValue2) * ($oldValue1 - $oldValue2) <= 0) {
                    $cross++;
                    $needStop = 0;
                } else {

                    if (is_numeric($thresold)) {
                        $needStop++;
                        if ($needStop >= $thresold) {
                            // echo date("d/m/Y H:i:s", time()) ."_thresold_". $needStop. "_". $cross . "\n";
                            return Reply::make(true, $des, $cross);
                        }
                    }
                }
            }

            // echo date("d/m/Y H:i:s", time()) ."_". $cross . "\n";

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

        if ($type == 'volatility') {
            $frame = get($struct['frame'], null);
            $volatility = get($struct['volatility'], null);
            $avg = get($struct['avg'], null);
            $object = get($struct['object'], null);
            if ($frame == null || $volatility == null || $avg == null || $object == null) return Reply::make(false, 'Please define Frame, Volatility, Avg, Object');
            $colName = 'volatility_' . $frame . "_" . $volatility . "_avg" . $avg . "_" . $object;
            $volData = $this->getVolatility();
            $des = "Volatility $frame $volatility avg in $avg $object";
            if (!$volData['result']) return $volData;
            if ($volData['data'] === null) return Reply::make(true, $des, null);
            $volData = $volData['data'];
            if (isset($volData->{$colName})) {
                return Reply::make(true, $des, doubleval($volData->{$colName}));
            } else {
                Reply::make(false, 'Can not calculate ' . $des);
            }
        }

        Reply::make(false, 'Can not caculate ' . json_encode($struct));
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


    public function check()
    {

        $this->checkTakeStop();

        //Cal priority
        $priority = $this->getPriorityIndex();
        if (!$priority['result']) return $priority;
        $this->priority = $priority['data'];

        while (true) {

            usleep(250000);

            $time_start = microtime(true);
            $time = round($time_start * 1000);

            // Check package loss or not
            if ($this->packageLost > 1000) {
                $this->packageLost = 0;
                // $this->binancer->stopService($this->symbol);
                Telegram::send(TELE_ICON_ERROR . " [ ERROR ] " . $this->binancer->getAccount()->{ACCOUNT_NAME} . " #" . $this->symbol  . " package loss", $this->teleGrError, $this->teleBot);
            }

            // Get all data for checking
            $result = $this->getData($time);
            if (!$result['result']) {
                // echo $result['message'] . "\n";
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

                //Set margin of next phase
                $type = $this->event->{ACTION_TYPE};
                $phase = $this->event->{ACTION_PHASE};
                $status = $this->event->{ACTION_STATUS};
                $flow = $this->event->{ACTION_FLOW};
                if ($status == ACTION_STATUS_MATCHED || $status == ACTION_STATUS_MATCHED_PART) {
                    $condition = $this->getMatchCondition($flow, $phase);
                    if ($condition) {
                        $afterPhase = get($condition['next_phase'], $phase + 1);
                        $afterCondition = $this->getMatchCondition($flow, $afterPhase);
                        if ($afterCondition) {
                            $margin = get($afterCondition['margin'], $this->cfgMargin);
                            $result = $this->binancer->setMargin($this->symbol, $margin);
                            if (!$result['result']) return $result;
                        }
                    }
                }
                continue;
            }



            // Check long/short condition
            $type = 0;
            $flow = null;
            $longResult = null;
            $shortResult = null;
            $startReason = '';
            $condition = null;

            if ($this->side != 'NONE') {
                foreach ($this->cfgStrategy as $flowName => $flowData) {
                    if (!isset($flowData['type'])) continue;
                    $flowType = $flowData['type'];
                    if ($flowType == 'LONG') {
                        if ($this->side == 'LONG' || $this->side == 'BOTH') {
                            if ($type == 0) {
                                $condition = $this->getMatchCondition($flowName, 0);
                                if ($condition != null) {
                                    $longResult = $this->compareOr($condition['condition']);
                                    if (!$longResult['result']) return $longResult;
                                    $startReason = $longResult['message'];
                                    if ($longResult['data']) {
                                        $type = ACTION_TYPE_LONG;
                                        $flow = $flowName;
                                        break;
                                    }
                                }
                            }
                        }
                    } else if ($flowType == 'SHORT') {
                        if ($this->side == 'SHORT' || $this->side == 'BOTH') {
                            $condition = $this->getMatchCondition($flowName, 0);
                            if ($condition != null) {
                                $shortResult = $this->compareOr($condition['condition']);
                                if (!$shortResult['result']) return $shortResult;
                                $startReason = $shortResult['message'];
                                if ($shortResult['data']) {
                                    $type = ACTION_TYPE_SHORT;
                                    $flow = $flowName;
                                    break;
                                }
                            }
                        }
                    }
                }
            }


            // Set margin for first phase if not yet;
            if ($condition != null) {
                $margin = get($condition['margin'], $this->cfgMargin);
                $result = $this->binancer->setMargin($this->symbol, $margin);
                if (!$result['result']) return $result;
            }



            if ($type != 0) {

                // Reste max profit and set phase 0 base profit
                $this->maxOrderProfit = 0;
                $this->baseProfit = doubleval(get($condition['baseprofit'], $this->cfgBaseprofit));

                // Get last action to check interval between action
                $interval = $this->cfgInterval;
                $LabPendingTime = 0;
                $this->matchedParamsPhase = null;


                if ($interval > 0) {

                    //get last time
                    $lastAction = $this->eventModel->read([
                        [
                            [ACTION_ACCOUNT, '=', $this->account],
                            [ACTION_SYMBOL, '=', $this->symbol],
                            [ACTION_PENDING, '=', '0']
                        ]
                    ], function ($db) {
                        $db->orderBy(ACTION_ENTER_TIME, 'DESC')->limit(1);
                    });

                    if (!$lastAction['result']) return $lastAction;
                    if (isset($lastAction['data'][0])) $LabPendingTime = doubleval($lastAction['data'][0]->{ACTION_SELL_TIME});
                }

                if ($time - $LabPendingTime >= ($interval * 60000)) {


                    //Check max trade open limit
                    if ($this->maxTradesOpen > 0) {
                        $openTrades = $this->countPosition();
                        if ($this->maxTradesOpen <= $openTrades) {
                            continue;
                        }
                    }

                    $this->getInvestBudget();
                    $enterPackage = get($condition['enter_package'], 100);

                    $candle1m = $this->data[$this->symbol]['1m'][0];

                    $closePrice = doubleval($candle1m->{CANDLE_1M_CLOSE});
                    $actionBudget = doubleval($this->tradeData->{TRADE_BUDGET}) * doubleval($this->tradeData->{TRADE_ACTION_BUDGET}) / 100;
                    $qty = $actionBudget / $closePrice;

                    $qty = $qty * $enterPackage / 100;


                    $addData = [

                        ACTION_ENTER_TIME => $time,
                        ACTION_ENTER_QTY => $qty,
                        ACTION_ENTER_PRICE => $closePrice,
                        ACTION_TYPE => $type,
                        ACTION_CHART => $time,
                        ACTION_SYMBOL => $this->symbol,
                        ACTION_ACCOUNT => $this->account,
                        ACTION_LOW => $candle1m->{CANDLE_1M_LOW},
                        ACTION_HIGH => $candle1m->{CANDLE_1M_HIGH},
                        ACTION_EVENT_DATA => json_encode(['0' => $this->data]),
                        ACTION_PENDING => 1,
                        ACTION_STATUS => ACTION_STATUS_ENTER_WAITTING,
                        ACTION_BUDGET => $this->tradeData->{TRADE_BUDGET},
                        ACTION_MATCHED_QTY => 0,
                        ACTION_MATCHED_PRICE => 0,
                        ACTION_ORDER_PHASE => 0,
                        ACTION_PROFIT => 0,
                        ACTION_BUDGET_USED => $this->getTotalBudget(),
                        ACTION_BUDGET_ACTIVE => $actionBudget,
                        ACTION_START_REASON => $startReason,
                        ACTION_FLOW => $flow

                    ];

                    $result = $this->eventModel->addGetId([$addData]);

                    if (!$result['result']) return $result;

                    $id = $result['data'][0];

                    $addData[ACTION_ID] = $id;

                    // Checking if has enter_rule and enter_step or not
                    $enterStep = get($condition['enter_step'], 0);
                    $enterRule = get($condition['enter_rule'], null);

                    if ($enterStep <= 0 && $enterRule === null) {
                        $this->makeOrder((object)$addData, $closePrice, 0, $time);
                    } else {
                        //Set enterbase and 
                        $this->enterBase = $closePrice;
                        $this->enterBaseModel->add([[
                            LOG_ENTERBASE_ACTION => $id,
                            LOG_ENTERBASE_TIME => $time,
                            LOG_ENTERBASE_EVENT => LOG_ENTERBASE_EVENT_WAITTING,
                            LOG_ENTERBASE_VALUE => $closePrice,
                            LOG_ENTERBASE_PRICE => $closePrice,
                            LOG_ENTERBASE_SYMBOL => $this->symbol,
                        ]]);

                        Telegram::send(
                            TELE_ICON_WAITTING . " [" . $this->binancer->getAccount()->{ACCOUNT_NAME} . "] #"
                                . $this->symbol  . " Waitting for " . ($type == ACTION_TYPE_LONG ? 'Long' : 'Short') . " Phase 0 Order"
                                . "\n- Close Price: " . $closePrice
                                . "\n- Flow: " . $flow
                                . "\n- Time: " . date("d/m/Y H:i:s", $time / 1000)
                                . "\n- Enter Package: " . $enterPackage . "%"
                                . "\n- From getting Data -> waitting order " . (microtime(true) * 1000 - $time) . "ms",
                            $this->teleGrNotice,
                            $this->teleBot
                        );
                    }
                }
            }

            // echo "Event check Real " . $this->symbol . " Excute time " . (microtime(true) - $time_start) . " second\n";

        }

        return Reply::make(false, "[" . $this->binancer->getAccount()->{ACCOUNT_NAME} . "] Service Stopped");
    }

    /**
     * Create Action manualy
     */
    public function makeAction($type, $userName, $flow)
    {

        $time = round(microtime(true) * 1000);

        if ($this->eventModel->is_exist([[[ACTION_PENDING, '=', 1], [ACTION_ACCOUNT, '=', $this->account], [ACTION_SYMBOL, '=', $this->symbol]]])) {
            return Reply::make(false, 'Can not make Position. Position ' . $this->symbol . ' is Pending');
        }

        $candle1m = $this->Candle1mModel->read([[[CANDLE_1M_SYMBOL, '=', $this->symbol]]], function ($db) {
            $db->orderBy(CANDLE_1M_CLOSE_TIME, 'DESC')->limit(1);
        });

        if (!$candle1m['result']) return $candle1m;
        if (!isset($candle1m['data'][0])) return Reply::make(false, 'Can not get 1m data');
        $candle1m = $candle1m['data'][0];

        $condition = $this->getMatchCondition($flow, 0);
        //Check max trade open limit
        if ($this->maxTradesOpen > 0) {
            $openTrades = $this->countPosition();
            if ($this->maxTradesOpen <= $openTrades) {
                return Reply::make(false, 'You can not open more than ' . $this->maxTradesOpen . ' Positions');
            }
        }


        $closePrice = doubleval($candle1m->{CANDLE_1M_CLOSE});
        $enterPackage = get($condition['enter_package'], 100);
        $actionBudget = doubleval($this->tradeData->{TRADE_BUDGET}) * doubleval($this->tradeData->{TRADE_ACTION_BUDGET}) / 100;
        $qty = $actionBudget / $closePrice;

        $qty = $qty * $enterPackage / 100;


        $addData = [

            ACTION_ENTER_TIME => $time,
            ACTION_ENTER_QTY => $qty,
            ACTION_ENTER_PRICE => $closePrice,
            ACTION_TYPE => $type,
            ACTION_CHART => $time,
            ACTION_SYMBOL => $this->symbol,
            ACTION_ACCOUNT => $this->account,
            ACTION_LOW => $candle1m->{CANDLE_1M_LOW},
            ACTION_HIGH => $candle1m->{CANDLE_1M_HIGH},
            ACTION_EVENT_DATA => json_encode(['0' => $this->data]),
            ACTION_PENDING => 1,
            ACTION_STATUS => ACTION_STATUS_ENTER_WAITTING,
            ACTION_BUDGET => $this->tradeData->{TRADE_BUDGET},
            ACTION_MATCHED_QTY => 0,
            ACTION_MATCHED_PRICE => 0,
            ACTION_ORDER_PHASE => 0,
            ACTION_PROFIT => 0,
            ACTION_BUDGET_USED => $this->getTotalBudget(),
            ACTION_BUDGET_ACTIVE => $actionBudget,
            ACTION_START_REASON => $userName . ' make position',
            ACTION_FLOW => $flow,

        ];

        $result = $this->eventModel->addGetId([$addData]);

        if (!$result['result']) return $result;

        $id = $result['data'][0];

        $addData[ACTION_ID] = $id;

        // Checking if has enter_rule and enter_step or not
        $enterStep = get($condition['enter_step'], 0);
        $enterRule = get($condition['enter_rule'], null);

        if ($enterStep <= 0 && $enterRule === null) {
            $this->makeOrder((object)$addData, $closePrice, 0, $time);
        } else {
            //Set enterbase and 
            $this->enterBase = $closePrice;
            $this->enterBaseModel->add([[
                LOG_ENTERBASE_ACTION => $id,
                LOG_ENTERBASE_TIME => $time,
                LOG_ENTERBASE_EVENT => LOG_ENTERBASE_EVENT_WAITTING,
                LOG_ENTERBASE_VALUE => $closePrice,
                LOG_ENTERBASE_PRICE => $closePrice,
                LOG_ENTERBASE_SYMBOL => $this->symbol,
            ]]);

            Telegram::send(
                TELE_ICON_WAITTING . " [" . $this->binancer->getAccount()->{ACCOUNT_NAME} . "] #"
                    . $this->symbol  . " Waitting for " . ($type == ACTION_TYPE_LONG ? 'Long' : 'Short') . " Order Phase 0 by " . $userName
                    . "\n-Time: " . date("d/m/Y H:i:s", $time / 1000)
                    . "\n- Close Price: " . $closePrice
                    . "\n- Flow: " . $flow
                    . "\n- Enter Package: " . $enterPackage . "%",
                $this->teleGrNotice,
                $this->teleBot
            );
        }

        return Reply::make(true, 'success');
    }

    /**
     * Go to next phase manualy
     * 
     */
    public function gotoNextPhase($userName)
    {

        $time = round(microtime(true) * 1000);

        $labEvent =  $this->eventModel->read([[
            [ACTION_SYMBOL, '=', $this->symbol],
            [ACTION_PENDING, '=', 1],
            [ACTION_ACCOUNT, '=', $this->account]
        ]]);
        if (!$labEvent['result'] || !isset($labEvent['data'][0])) {
            return Reply::make(false, 'Position has been closed');
        }

        $labEvent = $labEvent['data'][0];
        $phase = $labEvent->{ACTION_PHASE};
        $type = $labEvent->{ACTION_TYPE};
        $flow = $labEvent->{ACTION_FLOW};

        $condition = $this->getMatchCondition($flow, $phase);

        if ($phase >= ($this->getMatchLeng($flow) - 1)) return Reply::make(false, 'This is the last phase');

        $candle1m = $this->Candle1mModel->read([[[CANDLE_1M_SYMBOL, '=', $this->symbol]]], function ($db) {
            $db->orderBy(CANDLE_1M_CLOSE_TIME, 'DESC')->limit(1);
        });

        if (!$candle1m['result']) return $candle1m;
        if (!isset($candle1m['data'][0])) return Reply::make(false, 'Can not get 1m data');
        $candle1m = $candle1m['data'][0];
        $closePrice = doubleval($candle1m->{CANDLE_1M_CLOSE});

        $afterPhase = get($condition['next_phase'], $phase + 1);
        $afterCondition = $this->getMatchCondition($flow, $afterPhase);

        $enterPackage = get($afterCondition['enter_package'], 100);

        $actionBudget = doubleval($this->tradeData->{TRADE_BUDGET}) * doubleval($this->tradeData->{TRADE_ACTION_BUDGET}) / 100;
        $qty = $actionBudget / $closePrice;
        $qty = $qty * $enterPackage / 100;

        $addData = [
            ACTION_ENTER_TIME => $time,
            ACTION_ENTER_PRICE => $closePrice,
            ACTION_ENTER_QTY => $qty,
            ACTION_LOW => $candle1m->{CANDLE_1M_LOW},
            ACTION_HIGH => $candle1m->{CANDLE_1M_HIGH},
            ACTION_STATUS => ACTION_STATUS_ENTER_WAITTING,
            ACTION_ORDER_PHASE => $afterPhase
        ];

        $this->eventModel->edit([
            DATA_KEY => [[[ACTION_ID, '=', $labEvent->{ACTION_ID}]]],
            DATA_EDITOR => $addData
        ]);

        $this->enterBaseModel->add([[
            LOG_ENTERBASE_ACTION => $labEvent->{ACTION_ID},
            LOG_ENTERBASE_TIME => $time,
            LOG_ENTERBASE_EVENT => LOG_ENTERBASE_EVENT_WAITTING,
            LOG_ENTERBASE_VALUE => $closePrice,
            LOG_ENTERBASE_PRICE => $closePrice,
            LOG_ENTERBASE_SYMBOL => $this->symbol,
        ]]);

        Telegram::send(
            TELE_ICON_WAITTING . " [" .  $this->binancer->getAccount()->{ACCOUNT_NAME} . "] #" . $this->symbol
                . " Waitting for " . ($type == ACTION_TYPE_LONG ? 'Long' : 'Short') . " Order Phase " . ($afterPhase) . " by " . $userName
                . "\n-Time: " . date("d/m/Y H:i:s", $time / 1000)
                . "\n- Flow: " . $flow
                . "\n- Close Price: " . $closePrice
                . "\n- Enter Package: " . $enterPackage . "%",
            $this->teleGrNotice,
            $this->teleBot
        );

        return Reply::make(true, 'success');
    }


    private function canclePosition($action, $qty = null)
    {
        $startTime = microtime(true);
        $result = $this->binancer->canclePosition($this->symbol, $qty);
        $interval = microtime(true) - $startTime;
        if (!$result['result']) {
            Telegram::send(TELE_ICON_ERROR . " ERROR Stop " . $this->symbol . " " . $result['message'], $this->teleGrError, $this->teleBot);
            $this->eventModel->edit([
                DATA_KEY => [[[ACTION_ID, '=', $action->{ACTION_ID}]]],
                DATA_EDITOR => [
                    ACTION_LOG => $result['message'],
                    ACTION_STATUS => ACTION_STATUS_MATCHED_PART,
                ]
            ]);
        } else {
            Telegram::send(TELE_ICON_STOP . " [" . $this->binancer->getAccount()->{ACCOUNT_NAME} . "] #"
                . $this->symbol . " Stop \n- Reason: " . $action->{ACTION_STOP_REASON} . "\n- Delay: $interval", $this->teleGrNotice, $this->teleBot);
        }
        return $result;
    }

    private function getEma5()
    {
        $khung15m = $this->data[$this->symbol]['15m'];
        $khung3m = $this->data[$this->symbol]['3m'];
        $khung1m = $this->data[$this->symbol]['1m'];

        $ema5 = doubleval($khung1m[0]->{CANDLE_1M_EMA5});
        if ($this->cfgBackprofitBaseon == 'ema5_3m') {
            $ema5 = doubleval($khung3m[0]->{CANDLE_3M_EMA5});
        }
        if ($this->cfgBackprofitBaseon == 'ema5_15m') {
            $ema5 = doubleval($khung15m[0]->{CANDLE_15M_EMA5});
        }
        return $ema5;
    }


    private function compareQty($number1, $logic, $number2)
    {
        $pre = $this->binancer->getPrecision($this->symbol);
        $preQty = $pre['quantity'];
        $number1 = round($number1 * (10 ** $preQty)) / 10 ** $preQty;
        $number2 = round($number2 * (10 ** $preQty)) / 10 ** $preQty;
        if ($logic == "==") return $number1 == $number2;
        if ($logic == ">=") return $number1 >= $number2;
        if ($logic == "<=") return $number1 <= $number2;
        if ($logic == ">") return $number1 > $number2;
        if ($logic == "<") return $number1 < $number2;
    }

    private function makeOrder($action, $closePrice, $phase, $time)
    {

        $pre = $this->binancer->getPrecision($this->symbol);

        $type = $action->{ACTION_TYPE};
        $qty = $action->{ACTION_ENTER_QTY};
        $flow = $action->{ACTION_FLOW};

        $matchedQty = doubleval($action->{ACTION_MATCHED_QTY});
        $matchedPrice = doubleval($action->{ACTION_MATCHED_PRICE});

        $condition = $this->getMatchCondition($flow, $phase);

        $stoploss = get($condition['stoploss'], $this->cfgStoploss);
        $takeprofit = get($condition['takeprofit'], $this->cfgTakeprofit);

        $enterPackage = get($condition['enter_package'], 100);

        // Calculate order price;
        $enterPriceSetting = get($condition['enter_price'], 'market');

        if (is_numeric($enterPriceSetting)) {
            $enterPrice = $closePrice * $enterPriceSetting / 100;
        } else {
            $enterPrice = $closePrice;
        }

        if (isset($pre['tickSize'])) {
            $enterPrice = round($enterPrice / $pre['tickSize']) * $pre['tickSize'];
        }

        $orderPrice = $enterPrice;
        if ($enterPriceSetting == 'market') {
            $orderPrice = 'market';
        }

        //calculate quantity
        $margin = get($condition['margin'], $this->cfgMargin);
        $preQty = $pre['quantity'];
        $qty = round($qty * $margin * (10 ** $preQty)) / 10 ** $preQty;

        $totalQty = $matchedQty + $qty;
        $totalQty = round($totalQty * (10 ** $preQty)) / 10 ** $preQty;


        $this->eventModel->edit(
            [
                DATA_KEY => [[[ACTION_ID, '=', $action->{ACTION_ID}]]],
                DATA_EDITOR => [
                    ACTION_STATUS => $phase == 0 ? ACTION_STATUS_PENDING : ACTION_STATUS_PHASE_PENDING,
                    ACTION_ORDER_QTY => $qty,
                    ACTION_ORDER_TIME => $time,
                    ACTION_ORDER_PRICE => $enterPrice,
                    ACTION_ORDER_PHASE => $phase,
                    ACTION_MARGIN => $margin,
                    ACTION_MATCHED_EXPECTED_QTY => $totalQty,
                ]
            ]
        );

        $ms = ($type == ACTION_TYPE_LONG ? TELE_ICON_LONG : TELE_ICON_SHORT) . " [" . $this->binancer->getAccount()->{ACCOUNT_NAME} . "] #"
            . $this->symbol . " " . ($type == ACTION_TYPE_SHORT ? "SHORT" : "LONG") . " Order Phase $phase"
            . "\n- Time: " . date("d/m/Y H:i:s")
            . "\n- Price: " . $enterPrice
            . "\n- Flow: " . $flow
            . "\n- Enter Package: " . $enterPackage . "%"
            . "\n- Quantity: " . $qty
            . "\n- From getting waitting Data -> make order " . (microtime(true) * 1000 - $time) . "ms";

        Telegram::send($ms, $this->teleGrNotice, $this->teleBot);

        // if($this->teleGrSummary != null){
        //     foreach($this->teleGrSummary as $gr){
        //         Telegram::send($ms, $gr, $this->teleBot);
        //     }
        // }


        try {

            $beforeMakeOrder = microtime(true) * 1000;

            $result = $this->binancer->makeOrder($this->symbol, $qty, $orderPrice, $type == ACTION_TYPE_LONG ? 'BUY' : 'SELL', $takeprofit, $stoploss, $matchedQty, $matchedPrice);

            if (!$result['result']) {
                Telegram::send(TELE_ICON_ERROR . " ERROR Make Order " . $this->symbol . " " . $result['message'], $this->teleGrError, $this->teleBot);
                $this->eventModel->edit(
                    [
                        DATA_KEY => [[[ACTION_ID, '=', $action->{ACTION_ID}]]],
                        DATA_EDITOR => [
                            ACTION_ORDER_QTY => $qty,
                            ACTION_ORDER_TIME => $time,
                            ACTION_ORDER_PRICE => $enterPrice,
                            ACTION_ORDER_PHASE => $phase,
                            ACTION_MATCHED_EXPECTED_QTY => $totalQty,
                            ACTION_LOG => $result['message'],
                            ACTION_STATUS => $matchedQty > 0 ? ACTION_STATUS_MATCHED_PART : ACTION_STATUS_CANCLE,
                            ACTION_PENDING => $matchedQty > 0 ? 1 : 0
                        ]
                    ]
                );

                $this->makeOrderFault++;
                if ($this->makeOrderFault > 3) {
                    Telegram::send(TELE_ICON_ERROR .  " [" . $this->binancer->getAccount()->{ACCOUNT_NAME} . "] #" . $this->symbol . " Stop service after 3 make order fault ", $this->teleGrError, $this->teleBot);
                    $this->stopService();
                }
                return $result;
            } else {
                $this->makeOrderFault = 0;
            }

            $makeOrderResult = $result['data'];

            if (isset($makeOrderResult['matched']) && $makeOrderResult['matched']) {

                $matchedPrice = doubleval($makeOrderResult['matched_price']);
                $matchedPriceAvg = ($matchedPrice * $qty + doubleval($action->{ACTION_MATCHED_PRICE}) * doubleval($action->{ACTION_MATCHED_QTY})) / $totalQty;

                $editData = [
                    ACTION_ORDER_QTY => $qty,
                    ACTION_ORDER_TIME => $time,
                    ACTION_ORDER_PRICE => $enterPrice,
                    ACTION_ORDER_PHASE => $phase,
                    ACTION_MATCHED_TIME => $makeOrderResult['matched_time'],
                    ACTION_MATCHED_PRICE => $matchedPriceAvg,
                    ACTION_MATCHED_QTY => $totalQty,
                    ACTION_MATCHED_EMA5 => $this->getEma5(),
                    ACTION_MATCHED_EXPECTED_QTY => $totalQty,
                    ACTION_PHASE => $phase,
                    ACTION_STATUS => $phase == 0 ? ACTION_STATUS_PENDING : ACTION_STATUS_PHASE_PENDING,
                    ACTION_LAST_PRICE => $matchedPrice
                ];

                // Telegram::send(TELE_ICON_WARNING . "[" . $this->symbol . "] "
                // . "From make order -> success: " . (doubleval($makeOrderResult['matched_time']) - $beforeMakeOrder) . " ms"
                // , $this->teleGrNotice, $this->teleBot);

                if ($this->event->{ACTION_FIRST_PRICE} == null) $editData[ACTION_FIRST_PRICE] = $matchedPrice;

                $this->eventModel->edit(
                    [
                        DATA_KEY => [[[ACTION_ID, '=', $action->{ACTION_ID}]]],
                        DATA_EDITOR => $editData
                    ]
                );
            } else {

                $this->eventModel->edit(
                    [
                        DATA_KEY => [[[ACTION_ID, '=', $action->{ACTION_ID}]]],
                        DATA_EDITOR => [
                            ACTION_ORDER_QTY => $qty,
                            ACTION_ORDER_TIME => $time,
                            ACTION_ORDER_PRICE => $enterPrice,
                            ACTION_ORDER_PHASE => $phase,
                            ACTION_MATCHED_EXPECTED_QTY => $totalQty,
                            ACTION_STATUS => $phase == 0 ? ACTION_STATUS_PENDING : ACTION_STATUS_PHASE_PENDING,
                        ]
                    ]
                );
            }
        } catch (\Exception $th) {
            $msg = $th->getFile() . ' ' . $th->getLine() . ' ' . $th->getMessage();
            echo $msg . "\n";
            Telegram::send(TELE_ICON_ERROR . " ERROR Make Order " . $this->symbol . " " . $msg, $this->teleGrError, $this->teleBot);
            $this->binancer->stopService($this->symbol);
            return Reply::make(false, $msg);
        }
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


        $time = round(microtime(true) * 1000);

        $labEvent =  $this->eventModel->read([[
            [ACTION_SYMBOL, '=', $this->symbol],
            [ACTION_PENDING, '=', 1],
            [ACTION_ACCOUNT, '=', $this->account]
        ]]);
        if (!$labEvent['result'] || !isset($labEvent['data'][0])) {
            return Reply::make(true, 'No Pending Event', false);
        }

        $labEvent = $labEvent['data'][0];
        $this->event = $labEvent;

        $this->orderData = json_decode($labEvent->{ACTION_EVENT_DATA}, true);
        if (json_last_error() != JSON_ERROR_NONE) return Reply::make(false, 'Can not get Order data');

        $stepprofit = $this->cfgStepprofit;
        $backprofit = $this->cfgBackprofit;
        $timelife = $this->cfgTimelife;
        $baseprofit = $this->cfgBaseprofit;

        $type = $labEvent->{ACTION_TYPE};
        $status = $labEvent->{ACTION_STATUS};
        $flow = $labEvent->{ACTION_FLOW};

        $phase = doubleval($labEvent->{ACTION_PHASE});
        $nextPhase = doubleval($labEvent->{ACTION_ORDER_PHASE});

        $condition = $this->getMatchCondition($flow, $phase);
        $nextCondition = $this->getMatchCondition($flow, $nextPhase);


        if ($status == ACTION_STATUS_MATCHED || $status == ACTION_STATUS_MATCHED_PART) {

            if ($this->matchedParamsPhase !== $phase) {
                $this->matchedParamsPhase = $phase;
                // Reste max profit and set phase 0 base profit
                $this->maxOrderProfit = 0;
                $this->baseProfit = doubleval(get($condition['baseprofit'], $this->cfgBaseprofit));

                $liqui = null;
                $position = $this->binancer->getPosition($this->symbol);
                if ($position['result'] && isset($position['data'][0])) {
                    $liqui = $position['data'][0]['liquidationPrice'];
                }

                $afterPhase = get($condition['next_phase'], $phase + 1);
                $afterCondition = $this->getMatchCondition($flow, $afterPhase);

                if ($afterCondition) {
                    $this->eventModel->edit([
                        DATA_KEY => [[[ACTION_ID, '=', $labEvent->{ACTION_ID}]]],
                        DATA_EDITOR => [
                            ACTION_NEXTPHASE_NOTE => get($afterCondition['note'], ''),
                            ACTION_PHASE_NOTE => get($condition['note'], ''),
                            ACTION_LIQUIDATION => $liqui
                        ]
                    ]);
                }
            }
        }

        if ($status == ACTION_STATUS_PENDING || $status == ACTION_STATUS_PHASE_PENDING) {

            if ($this->compareQty($labEvent->{ACTION_MATCHED_EXPECTED_QTY}, "<=", $labEvent->{ACTION_MATCHED_QTY})) {
                $this->eventModel->edit([
                    DATA_KEY => [[[ACTION_ID, '=', $labEvent->{ACTION_ID}]]],
                    DATA_EDITOR => [
                        ACTION_STATUS => $nextPhase == ($this->getMatchLeng($flow) - 1) ? ACTION_STATUS_MATCHED : ACTION_STATUS_MATCHED_PART,
                        ACTION_MATCHED_EMA5 => $this->getEma5(),
                        ACTION_LOW => $khung1m[0]->{CANDLE_1M_LOW},
                        ACTION_HIGH => $khung1m[0]->{CANDLE_1M_HIGH},
                        ACTION_PHASE => $nextPhase
                    ]
                ]);
                return Reply::make(true, 'Pending Event', true);
            }

            $startTime = doubleval($labEvent->{ACTION_ORDER_TIME});
            if ((doubleval($time) - $startTime) >= $timelife * 60 * 1000) {
                $cancelResult = $this->binancer->cancleAllOrder($this->symbol);
                if (!$cancelResult['result']) {
                    Telegram::send(TELE_ICON_ERROR . " [" . $this->binancer->getAccount()->{ACCOUNT_NAME} . "] #" . $this->symbol . " Error Cancel \n- Time:" . date("d/m/Y H:i:s"), $this->teleGrError, $this->teleBot);
                } else {

                    $this->eventModel->edit([
                        DATA_KEY => [[[ACTION_ID, '=', $labEvent->{ACTION_ID}]]],
                        DATA_EDITOR => [
                            ACTION_STATUS => doubleval($labEvent->{ACTION_MATCHED_QTY}) > 0 ? ACTION_STATUS_MATCHED_PART : ACTION_STATUS_CANCLE,
                            ACTION_PENDING => doubleval($labEvent->{ACTION_MATCHED_QTY}) > 0 ? 1 : 0,
                        ]
                    ]);
                    Telegram::send(TELE_ICON_CANCEL . " [" . $this->binancer->getAccount()->{ACCOUNT_NAME} . "] #" . $this->symbol . " Cancel Phase $phase \n- Time:" . date("d/m/Y H:i:s"), $this->teleGrNotice, $this->teleBot);
                }

                return Reply::make(true, 'Pending Event', true);
            }
        }

        if (doubleval($labEvent->{ACTION_MATCHED_QTY}) > 0 && $status != ACTION_STATUS_STOP_PENDING) {

            $matchedPrice = doubleval($labEvent->{ACTION_MATCHED_PRICE});
            $matchedEma5 = doubleval($labEvent->{ACTION_MATCHED_EMA5});

            $price = $this->getCheckMatchedPrice($labEvent, $closePrice, $high, $low, $openTime);
            $ema5 = $this->getEma5();

            if ($type == ACTION_TYPE_LONG) {

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

            $this->event->{ACTION_PROFIT} = $profitReal;

            $editData = [];

            $finished = false;
            $releasePercent = 100;
            $releaseIndex = null;

            // Price Rule for stop

            if (!$finished) {

                $runningRelease = $labEvent->{ACTION_ORDER_RELEASE};

                $stops = $this->getStopConditions($flow);
                if ($stops != null) {
                    foreach ($stops as $key => $stop) {

                        if ($runningRelease !== null && $runningRelease <= $key) continue;

                        $stopCondition = $stop['condition'];
                        $result = $this->compareOr($stopCondition);
                        if (!$result['result']) return $result;
                        if ($result['data']) {
                            $editData = [
                                ACTION_STOP_REASON => $result['message'],
                                ACTION_ORDER_PHASE => get($stop['phase_update'], $phase),
                                ACTION_ORDER_RELEASE => $key,
                            ];
                            $finished = true;
                            $releasePercent = get($stop['release_percent'], 100);
                            $releaseIndex = $key;
                            break;
                        }
                    }
                }
            }

            if (!$finished) {

                $stepprofit = doubleval(get($condition['stepprofit'], $this->cfgStepprofit));
                $backprofit = doubleval(get($condition['backprofit'], $this->cfgBackprofit));

                if ($maxProfit > $this->maxOrderProfit) {
                    if ($maxProfit > $this->baseProfit && $this->maxOrderProfit < $this->baseProfit) {
                        $this->profitBaseModel->add([[
                            LOG_PROFITBASE_ACTION => $this->event->{ACTION_ID},
                            LOG_PROFITBASE_TIME => $time,
                            LOG_PROFITBASE_EVENT => LOG_PROFITBASE_EVENT_WAITTING,
                            LOG_PROFITBASE_VALUE => $this->baseProfit,
                            LOG_PROFITBASE_PRICE => $closePrice,
                            LOG_PROFITBASE_SYMBOL => $this->symbol,
                        ]]);
                    }
                    $this->maxOrderProfit = $maxProfit;
                }

                if ($stepprofit > 0 && $this->maxOrderProfit > ($this->baseProfit + $stepprofit)) {
                    $this->baseProfit = $this->baseProfit + floor(($this->maxOrderProfit - $this->baseProfit) / $stepprofit) * $stepprofit;
                    $this->profitBaseModel->add([[
                        LOG_PROFITBASE_ACTION => $this->event->{ACTION_ID},
                        LOG_PROFITBASE_TIME => $time,
                        LOG_PROFITBASE_EVENT => LOG_PROFITBASE_EVENT_MAKESTEP,
                        LOG_PROFITBASE_VALUE => $this->baseProfit,
                        LOG_PROFITBASE_PRICE => $closePrice,
                        LOG_PROFITBASE_SYMBOL => $this->symbol,
                    ]]);
                }

                if ($this->baseProfit > 0 && $this->maxOrderProfit > $this->baseProfit && $profit < ($this->baseProfit - $backprofit)) {
                    $editData = [
                        ACTION_STOP_REASON => "Profit <= Base profit ($this->baseProfit) - back Step Profit ($backprofit)"
                    ];
                    $finished = true;
                    $this->profitBaseModel->add([[
                        LOG_PROFITBASE_ACTION => $this->event->{ACTION_ID},
                        LOG_PROFITBASE_TIME => $time,
                        LOG_PROFITBASE_EVENT => LOG_PROFITBASE_EVENT_MAKEORDER,
                        LOG_PROFITBASE_VALUE => $this->baseProfit,
                        LOG_PROFITBASE_PRICE => $closePrice,
                        LOG_PROFITBASE_SYMBOL => $this->symbol,
                    ]]);
                }
            }


            $editData[ACTION_PROFIT] = $profitReal;
            $editData[ACTION_BASEPROFIT] = $this->baseProfit;

            if ($releasePercent == 100) {
                $releaseQty = NULL;
            } else {
                $qty = $labEvent->{ACTION_MATCHED_QTY};
                $releaseQty = $qty * $releasePercent / 100;
                $pre = $this->binancer->getPrecision($this->symbol);
                $preQty = $pre['quantity'];
                $releaseQty = round($releaseQty * (10 ** $preQty)) / 10 ** $preQty;
            }

            if ($finished) {
                if ($releaseIndex === null) {
                    $editData[ACTION_STATUS] = ACTION_STATUS_STOP_PENDING;
                } else {
                    $editData[ACTION_STATUS] = ACTION_STATUS_RELEASE_WAITTING;
                    $editData[ACTION_ORDER_QTY] = $releaseQty;
                    $this->releaseBase = $profitReal;
                }
            }

            $this->eventModel->edit([
                DATA_KEY => [[[ACTION_ID, '=', $labEvent->{ACTION_ID}]]],
                DATA_EDITOR => $editData
            ]);

            if ($finished) {
                $labEvent->{ACTION_STOP_REASON} = $editData[ACTION_STOP_REASON];
                if ($releaseIndex === null) {
                    $this->canclePosition($labEvent);
                } else {
                    $this->releasePosition($labEvent,  $editData[ACTION_ORDER_PHASE], $releaseIndex, $releaseQty);
                }
            }
        }

        if ($status == ACTION_STATUS_ENTER_WAITTING) {

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
                    $checkPrice = $this->getCheckWaitingPrice($labEvent, $closePrice, $high, $low, $openTime);
                    $enterPrice = doubleval($labEvent->{ACTION_ENTER_PRICE});

                    if ($type == ACTION_TYPE_LONG) {

                        $down = ($enterPrice - $checkPrice['min']) * 100 / $enterPrice;
                        $downBase = ($enterPrice - $this->enterBase) * 100 / $enterPrice;
                        $currentDown = ($enterPrice - $closePrice) * 100 / $enterPrice;

                        if ($down > ($downBase + $enterStep)) {
                            $downBase = floor($down / $enterStep) * $enterStep;
                            $this->enterBase = $enterPrice - ($enterPrice *  $downBase / 100);
                            $this->enterBaseModel->add([[
                                LOG_ENTERBASE_ACTION => $labEvent->{ACTION_ID},
                                LOG_ENTERBASE_TIME => $time,
                                LOG_ENTERBASE_EVENT => LOG_ENTERBASE_EVENT_MAKESTEP,
                                LOG_ENTERBASE_VALUE => $this->enterBase,
                                LOG_ENTERBASE_PRICE => $closePrice,
                                LOG_ENTERBASE_SYMBOL => $this->symbol,
                            ]]);
                        }

                        if ($downBase - $currentDown >= $enterBack) {
                            if ($currentDown >= 0 || $this->allowNegativeWaittingPriceLong) {
                                $isMakeOrder = true;
                            } else {
                                $isCancle = true;
                                $this->enterBaseModel->add([[
                                    LOG_ENTERBASE_ACTION => $labEvent->{ACTION_ID},
                                    LOG_ENTERBASE_TIME => $time,
                                    LOG_ENTERBASE_EVENT => LOG_ENTERBASE_EVENT_CANCLE,
                                    LOG_ENTERBASE_VALUE => $this->enterBase,
                                    LOG_ENTERBASE_PRICE => $closePrice,
                                    LOG_ENTERBASE_SYMBOL => $this->symbol,
                                ]]);
                            }
                        }
                    } else if ($type == ACTION_TYPE_SHORT) {

                        $up = ($checkPrice['max'] - $enterPrice) * 100 / $enterPrice;
                        $upBase = ($this->enterBase - $enterPrice) * 100 / $enterPrice;
                        $currentUp = ($closePrice - $enterPrice) * 100 / $enterPrice;

                        if ($up > ($upBase + $enterStep)) {
                            $upBase = floor($up / $enterStep) * $enterStep;
                            $this->enterBase = $enterPrice + ($enterPrice * $upBase / 100);
                            $this->enterBaseModel->add([[
                                LOG_ENTERBASE_ACTION => $labEvent->{ACTION_ID},
                                LOG_ENTERBASE_TIME => $time,
                                LOG_ENTERBASE_EVENT => LOG_ENTERBASE_EVENT_MAKESTEP,
                                LOG_ENTERBASE_VALUE => $this->enterBase,
                                LOG_ENTERBASE_PRICE => $closePrice,
                                LOG_ENTERBASE_SYMBOL => $this->symbol,
                            ]]);
                        }

                        if ($upBase - $currentUp >= $enterBack) {

                            if ($currentUp >= 0 || $this->allowNegativeWaittingPriceShort) {
                                $isMakeOrder = true;
                            } else {
                                $isCancle = true;
                                $this->enterBaseModel->add([[
                                    LOG_ENTERBASE_ACTION => $labEvent->{ACTION_ID},
                                    LOG_ENTERBASE_TIME => $time,
                                    LOG_ENTERBASE_EVENT => LOG_ENTERBASE_EVENT_CANCLE,
                                    LOG_ENTERBASE_VALUE => $this->enterBase,
                                    LOG_ENTERBASE_PRICE => $closePrice,
                                    LOG_ENTERBASE_SYMBOL => $this->symbol,
                                ]]);
                            }
                        }
                    }
                }
            }

            //Check max trade open limit
            $freeSlot = 0;
            if ($nextPhase == 0 && $this->maxTradesOpen > 0) {
                $openTrades = $this->countPosition();
                if ($this->maxTradesOpen <= $openTrades) {
                    $isCancle = true;
                    $isMakeOrder = false;
                } else {
                    $freeSlot = $this->maxTradesOpen - intval($openTrades);
                }
            }

            if ($isMakeOrder) {
                //Check priority
                if ($nextPhase == 0 && $this->maxTradesOpen > 0) {
                    $checkPriority = $this->checkPriority($freeSlot);
                    if (!$checkPriority['result']) return $checkPriority;
                    $checkPriority = $checkPriority['data'];
                    if ($checkPriority) {
                        $this->enterBaseModel->add([[
                            LOG_ENTERBASE_ACTION => $labEvent->{ACTION_ID},
                            LOG_ENTERBASE_TIME => $time,
                            LOG_ENTERBASE_EVENT => LOG_ENTERBASE_EVENT_MAKEORDER,
                            LOG_ENTERBASE_VALUE => $this->enterBase,
                            LOG_ENTERBASE_PRICE => $closePrice,
                            LOG_ENTERBASE_SYMBOL => $this->symbol,
                        ]]);
                        $this->makeOrder($labEvent, $closePrice, $nextPhase, $time);
                    } else {
                        echo "Can not make order " . $this->symbol . " because of low priority\n";
                    }
                } else {
                    $this->makeOrder($labEvent, $closePrice, $nextPhase, $time);
                }

                return Reply::make(true, 'Pending Event', true);
            }

            if ($isCancle) {
                $this->eventModel->edit([
                    DATA_KEY => [[[ACTION_ID, '=', $labEvent->{ACTION_ID}]]],
                    DATA_EDITOR => [
                        ACTION_STATUS => doubleval($labEvent->{ACTION_MATCHED_QTY}) > 0 ? ACTION_STATUS_MATCHED_PART : ACTION_STATUS_CANCLE,
                        ACTION_PENDING => doubleval($labEvent->{ACTION_MATCHED_QTY}) > 0 ? 1 : 0,
                    ]
                ]);
                Telegram::send(TELE_ICON_CANCEL . " [" . $this->binancer->getAccount()->{ACCOUNT_NAME} . "] #"
                    . $this->symbol . " Cancel waitting order Phase $nextPhase \n- Time:" . date("d/m/Y H:i:s"), $this->teleGrNotice, $this->teleBot);
                return Reply::make(true, 'Pending Event', $labEvent->{ACTION_MATCHED_QTY} > 0);
            }
        }

        if ($status == ACTION_STATUS_MATCHED_PART) {

            if ($phase < ($this->getMatchLeng($flow) - 1)) {
                $afterPhase = get($condition['next_phase'], $phase + 1);
                $afterCondition = $this->getMatchCondition($flow, $afterPhase);
                $checkResult = $this->compareOr($afterCondition['condition']);
                if (!$checkResult['result']) return $checkResult;
                if ($checkResult['data']) {

                    $enterStep = get($afterCondition['enter_step'], 0);
                    $enterRule = get($afterCondition['enter_rule'], null);
                    $enterPackage = get($afterCondition['enter_package'], 100);

                    $this->getInvestBudget();

                    $actionBudget = doubleval($this->tradeData->{TRADE_BUDGET}) * doubleval($this->tradeData->{TRADE_ACTION_BUDGET}) / 100;
                    $qty = $actionBudget / $closePrice;
                    $qty = $qty * $enterPackage / 100;

                    $closePrice = doubleval($khung1m[0]->{CANDLE_1M_CLOSE});

                    $baseonData = $this->orderData;
                    $baseonData[$afterPhase] = $this->data;

                    $addData = [
                        ACTION_ENTER_TIME => $time,
                        ACTION_ENTER_PRICE => $closePrice,
                        ACTION_ENTER_QTY => $qty,
                        ACTION_LOW => $khung1m[0]->{CANDLE_1M_LOW},
                        ACTION_HIGH => $khung1m[0]->{CANDLE_1M_HIGH},
                        ACTION_EVENT_DATA => json_encode($baseonData),
                        ACTION_STATUS => ACTION_STATUS_ENTER_WAITTING,
                        ACTION_ORDER_PHASE => $afterPhase
                    ];

                    $this->eventModel->edit([
                        DATA_KEY => [[[ACTION_ID, '=', $labEvent->{ACTION_ID}]]],
                        DATA_EDITOR => $addData
                    ]);

                    if ($enterStep <= 0 && $enterRule === null) {
                        $this->makeOrder($labEvent, $closePrice, $afterPhase, $time);
                    } else {

                        // Set enter base and log to db
                        $this->enterBase = $closePrice;

                        $this->enterBaseModel->add([[
                            LOG_ENTERBASE_ACTION => $labEvent->{ACTION_ID},
                            LOG_ENTERBASE_TIME => $time,
                            LOG_ENTERBASE_EVENT => LOG_ENTERBASE_EVENT_WAITTING,
                            LOG_ENTERBASE_VALUE => $closePrice,
                            LOG_ENTERBASE_PRICE => $closePrice,
                            LOG_ENTERBASE_SYMBOL => $this->symbol,
                        ]]);

                        Telegram::send(
                            TELE_ICON_WAITTING . " [" .  $this->binancer->getAccount()->{ACCOUNT_NAME} . "] #" . $this->symbol
                                . " Waitting for " . ($type == ACTION_TYPE_LONG ? 'Long' : 'Short') . " Order Phase " . ($afterPhase)
                                . " \n- Time: " . date("d/m/Y H:i:s", $time / 1000)
                                . " \n- Flow: " . $flow
                                . " \n- Close Price: " . $closePrice
                                . " \n- Enter Package: " . $enterPackage . "%",
                            $this->teleGrNotice,
                            $this->teleBot
                        );
                    }
                }
            } else {
                $this->eventModel->edit([
                    DATA_KEY => [[[ACTION_ID, '=', $labEvent->{ACTION_ID}]]],
                    DATA_EDITOR => [
                        ACTION_STATUS => ACTION_STATUS_MATCHED,
                    ]
                ]);
            }
        }

        if ($status == ACTION_STATUS_RELEASE_WAITTING) {

            $this->releasePosition($labEvent, $nextPhase, $labEvent->{ACTION_ORDER_RELEASE}, $labEvent->{ACTION_ORDER_QTY});
        }

        if ($status == ACTION_STATUS_RELEASE_PENDING) {

            if ($this->compareQty($labEvent->{ACTION_MATCHED_EXPECTED_QTY}, ">=", $labEvent->{ACTION_MATCHED_QTY})) {
                $this->eventModel->edit([
                    DATA_KEY => [[[ACTION_ID, '=', $labEvent->{ACTION_ID}]]],
                    DATA_EDITOR => [
                        ACTION_STATUS => $nextPhase == ($this->getMatchLeng($flow) - 1) ? ACTION_STATUS_MATCHED : ACTION_STATUS_MATCHED_PART,
                        ACTION_PHASE => $nextPhase,
                        ACTION_ORDER_RELEASE => NULL
                    ]
                ]);
                Telegram::send(
                    TELE_ICON_MATCHED
                        . " [" . $this->binancer->getAccount()->{ACCOUNT_NAME} . "] #" . $this->symbol . " Release and comeback phase $nextPhase"
                        . "\n- Time: " . date("d/m/Y H:i:s", $time / 1000)
                        . "\n- Qty: " . $labEvent->{ACTION_ORDER_QTY},

                    $this->teleGrNotice,
                    $this->teleBot
                );
                return Reply::make(true, 'Pending Event', true);
            }
        }

        return Reply::make(true, 'Pending Event', true);
    }


    private function getCheckMatchedPrice($labEvent, $price, $high, $low, $open_time)
    {

        if ($open_time > $labEvent->{ACTION_MATCHED_TIME}) return ['max' => $high, 'min' => $low];
        $max = $price;
        $min = $price;
        if ($high != $labEvent->{ACTION_HIGH}) $max = $high;
        if ($low != $labEvent->{ACTION_LOW}) $min = $low;

        return ['max' => $max, 'min' => $min];
    }

    private function releasePosition($action, $nextPhase, $releaseIndex, $releaseQty)
    {
        $khung1m = $this->data[$this->symbol]['1m'];

        $closePrice = doubleval($khung1m[0]->{CANDLE_1M_CLOSE});
        $high = doubleval($khung1m[0]->{CANDLE_1M_HIGH});
        $low = doubleval($khung1m[0]->{CANDLE_1M_LOW});

        $type = $action->{ACTION_TYPE};
        $flow = $action->{ACTION_FLOW};
        $nextCondition = $this->getMatchCondition($flow, $nextPhase);
        $releaseCondition = $this->getStopCondition($flow, $releaseIndex);

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

                $matchedPrice = doubleval($action->{ACTION_MATCHED_PRICE});

                if ($type == ACTION_TYPE_LONG) {
                    $maxProfit = ($high - $matchedPrice) * 100 / $matchedPrice;
                    $profit = ($closePrice - $matchedPrice) * 100 / $matchedPrice;
                } else if ($type == ACTION_TYPE_SHORT) {
                    $maxProfit = ($matchedPrice - $low) * 100 / $matchedPrice;
                    $profit = ($matchedPrice - $closePrice) * 100 / $matchedPrice;
                }

                if ($maxProfit > ($this->releaseBase + $releaseStep)) {
                    $this->releaseBase = floor($maxProfit / $releaseStep) * $releaseStep;
                    $this->profitBaseModel->add([[
                        LOG_PROFITBASE_ACTION => $this->event->{ACTION_ID},
                        LOG_PROFITBASE_TIME => round(microtime(true) * 1000),
                        LOG_PROFITBASE_EVENT => LOG_PROFITBASE_EVENT_MAKESTEP,
                        LOG_PROFITBASE_VALUE => $this->releaseBase,
                        LOG_PROFITBASE_PRICE => $closePrice,
                        LOG_PROFITBASE_SYMBOL => $this->symbol,
                    ]]);
                }

                if ($this->releaseBase - $profit > $releaseBack) {
                    $isRelease = true;
                    echo $this->releaseBase . " " . $profit . "\n";
                } else {
                    $isRelease = false;
                }
            }
        }

        if ($isRelease) {

            if ($releaseQty == null) {
                $expectQuantity = 0;
            } else {
                $expectQuantity = doubleval($action->{ACTION_MATCHED_QTY}) - $releaseQty;
            }

            $this->eventModel->edit([
                DATA_KEY => [[[ACTION_ID, '=', $action->{ACTION_ID}]]],
                DATA_EDITOR => [
                    ACTION_STATUS => $expectQuantity > 0 ? ACTION_STATUS_RELEASE_PENDING : ACTION_STATUS_STOP_PENDING,
                    ACTION_MATCHED_EXPECTED_QTY => $expectQuantity
                ]
            ]);

            $result = $this->canclePosition($action, $releaseQty);
            if ($result['result']) {

                if ($releaseQty !== NULL) {
                    $stoploss = get($nextCondition['stoploss'], $this->cfgStoploss);
                    $takeprofit = get($nextCondition['takeprofit'], $this->cfgTakeprofit);

                    $stopTakeResult = $this->binancer->createTakeStop(
                        $this->symbol,
                        $action->{ACTION_MATCHED_PRICE},
                        $type == ACTION_TYPE_LONG ? 'BUY' : 'SELL',
                        $stoploss,
                        $takeprofit
                    );

                    if (!$stopTakeResult['result']) {
                        $ms =  " [" . $this->binancer->getAccount()->{ACCOUNT_NAME} . "] #" . $this->symbol
                            . " Can not update takeprofit and stoploss back to phase $nextPhase \n- Time:" . date("d/m/Y H:i:s");
                        echo $ms . "\n";
                        Telegram::send(TELE_ICON_ERROR . $ms, $this->teleGrError, $this->teleBot);
                    }
                }
            } else {

                $this->eventModel->edit([
                    DATA_KEY => [[[ACTION_ID, '=', $action->{ACTION_ID}]]],
                    DATA_EDITOR => [
                        ACTION_STATUS => ACTION_STATUS_MATCHED_PART,
                        ACTION_LOG => $result['message'],
                        ACTION_ORDER_RELEASE => NULL
                    ]
                ]);

                $ms =  " [" . $this->binancer->getAccount()->{ACCOUNT_NAME} . "] #" . $this->symbol
                    . " Can not release position phase $nextPhase  \n- Time:" . date("d/m/Y H:i:s");
                echo $ms . "\n";
                Telegram::send(TELE_ICON_ERROR . $ms, $this->teleGrError, $this->teleBot);
            }
        } else if ($isCancle) {

            $this->eventModel->edit([
                DATA_KEY => [[[ACTION_ID, '=', $action->{ACTION_ID}]]],
                DATA_EDITOR => [
                    ACTION_STATUS => doubleval($action->{ACTION_MATCHED_QTY}) > 0 ? ACTION_STATUS_MATCHED_PART : ACTION_STATUS_CANCLE,
                    ACTION_PENDING => doubleval($action->{ACTION_MATCHED_QTY}) > 0 ? 1 : 0,
                    ACTION_ORDER_RELEASE => NULL
                ]
            ]);
            Telegram::send(TELE_ICON_CANCEL . " [" . $this->binancer->getAccount()->{ACCOUNT_NAME} . "] #"
                . $this->symbol . " Cancel waitting Release back to Phase $nextPhase \n- Time:" . date("d/m/Y H:i:s"), $this->teleGrNotice, $this->teleBot);
        }
    }


    public function stopService()
    {
        return $this->binancer->stopService($this->symbol);
    }


    private function getCheckWaitingPrice($event, $price, $high, $low, $open_time)
    {
        if ($open_time > $event->{ACTION_ENTER_TIME}) return ['max' => $high, 'min' => $low];
        $max = $price;
        $min = $price;
        if ($high != $event->{ACTION_HIGH}) $max = $high;
        if ($low != $event->{ACTION_LOW}) $min = $low;

        return ['max' => $max, 'min' => $min];
    }


    /**
     * @return Number of free slot
     */
    private function countPosition()
    {

        $openTrades = $this->eventModel->count([[[ACTION_PENDING, '=', 1], [ACTION_ACCOUNT, '=', $this->account]]]);
        if (!$openTrades['result']) return $this->maxTradesOpen;
        $openTrades = intval($openTrades['data']);

        $waittingTrades = $this->eventModel->count([[[ACTION_PENDING, '=', 1], [ACTION_ACCOUNT, '=', $this->account], [ACTION_STATUS, '=', ACTION_STATUS_ENTER_WAITTING], [ACTION_MATCHED_QTY, '=', 0]]]);
        if (!$waittingTrades['result']) return $this->maxTradesOpen;
        $waittingTrades = intval($waittingTrades['data']);

        return $openTrades - $waittingTrades;
    }

    /**
     * @return symbol and priority
     */

    private function getPriorityIndex()
    {
        $trades = $this->tradesModel->read([[[TRADE_ACCOUNT, '=', $this->account]]]);
        if (!$trades['result']) return $trades;
        $trades = $trades['data'];
        $tradeIndex = [];
        foreach ($trades as $trade) {
            $tradeIndex[$trade->{TRADE_SYMBOL}] = doubleval($trade->{TRADE_PRIORITY});
        }
        return Reply::make(true, 'success', $tradeIndex);
    }


    /**
     * Check if the symbol is allowed to make order
     */
    private function checkPriority($freeSlot)
    {

        $priority = get($this->priority[$this->symbol], 0);
        $waittingTrades = $this->eventModel->read([[[ACTION_PENDING, '=', 1], [ACTION_STATUS, '=', ACTION_STATUS_ENTER_WAITTING], [ACTION_ACCOUNT, '=', $this->account]]]);
        if (!$waittingTrades['result']) return $waittingTrades;
        $waittingTrades = $waittingTrades['data'];
        $takenSlot = 0;
        foreach ($waittingTrades as $waitting) {
            $symbol = $waitting->{ACTION_SYMBOL};
            $otherPriority = get($this->priority[$symbol], 0);
            if (intval($otherPriority) > intval($priority)) {
                $takenSlot++;
            }
        }
        return Reply::make(true, 'success', $freeSlot > $takenSlot);
    }



    private function getInvestBudget()
    {
        $tradeData = $this->tradesModel->read([[[TRADE_SYMBOL, '=', $this->symbol], [TRADE_ACCOUNT, '=', $this->account]]]);
        if (!$tradeData['result'] || !isset($tradeData['data'][0])) {
            return 0;
        }

        $tradeData = $tradeData['data'][0];
        $this->tradeData = $tradeData;
        return doubleval($tradeData->{TRADE_BUDGET});
    }
}

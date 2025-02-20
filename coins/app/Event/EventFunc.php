<?php

namespace App\Event;

use App\Helpers\Control\Ctrl;
use App\Helpers\DB\Models;
use App\Helpers\Request\Query;
use App\Helpers\Request\Reply;

/**
 * 
 */
trait EventFunc
{
    public function calNeedMetadataData($strategy)
    {
        $needData = [
            $this->symbol => ['1m' => 0]
        ];

        foreach ($strategy as $flowData) {
            if (is_array($flowData)) {
                foreach ($flowData as $val) {
                    $this->scandNeedMetaData($val, $needData);
                }
            }
        }

        return $needData;
    }

    private function scandNeedMetaData($or, &$needData)
    {
        if (!is_array($or)) return;
        foreach ($or as $and) {
            if (!is_array($and)) continue;
            foreach ($and as $item) {
                if (!is_array($item)) continue;

                if (count($item) == 3 && in_array($item[1], ['<', '>', '=', '>=', '<='])) {

                    //Compare item
                    $firstEle = $item[0];
                    $secondEle = $item[2];

                    if (is_array($firstEle)) {
                        $symbol = $this->symbol;
                        if (isset($firstEle['symbol'])) $symbol = $firstEle['symbol'];
                        $frame = get($firstEle['frame'], '');
                        $index = get($firstEle['index'], '');

                        if ($symbol != '' && $frame != '' && $index !== '') {
                            if (!isset($needData[$symbol])) $needData[$symbol] = [];
                            if (!isset($needData[$symbol][$frame])) {
                                $needData[$symbol][$frame] =  doubleval($index);
                            } else {
                                if ($needData[$symbol][$frame] > doubleval($index))
                                    $needData[$symbol][$frame] = doubleval($index);
                            }
                        }
                    }

                    if (is_array($secondEle)) {
                        $symbol = $this->symbol;
                        if (isset($secondEle['symbol'])) $symbol = $secondEle['symbol'];
                        $frame = get($secondEle['frame'], '');
                        $index = get($secondEle['index'], '');

                        if ($symbol != '' && $frame != '' && $index !== '') {
                            if (!isset($needData[$symbol])) $needData[$symbol] = [];
                            if (!isset($needData[$symbol][$frame])) {
                                $needData[$symbol][$frame] =  doubleval($index);
                            } else {
                                if ($needData[$symbol][$frame] > doubleval($index))
                                    $needData[$symbol][$frame] = doubleval($index);
                            }
                        }
                    }
                } else {
                    // or item
                    $this->scandNeedMetaData($item, $needData);
                }
            }
        }
    }


    public function compare($element, $dynamicIndex = null)
    {
        $firstNumber = $this->caculateElement($element[0], $dynamicIndex);
        $formula = $element[1];
        $secondsNumber = $this->caculateElement($element[2], $dynamicIndex);



        if (!$firstNumber['result']) return $firstNumber;
        if (!$secondsNumber['result']) return $secondsNumber;

        $log = $firstNumber['message'] . " " . $formula . " " . $secondsNumber['message'];

        if ($firstNumber['data'] === null || $secondsNumber['data'] === null || $firstNumber['data'] === '' || $secondsNumber['data'] === '') return Reply::make(true, $log, null);

        if ($formula == '=') return Reply::make(true, $log, $firstNumber['data'] == $secondsNumber['data']);
        if ($formula == '>') return Reply::make(true, $log, $firstNumber['data'] > $secondsNumber['data']);
        if ($formula == '<') return Reply::make(true, $log, $firstNumber['data'] < $secondsNumber['data']);
        if ($formula == '>=') return Reply::make(true, $log, $firstNumber['data'] >= $secondsNumber['data']);
        if ($formula == '<=') return Reply::make(true, $log, $firstNumber['data'] <= $secondsNumber['data']);

        return Reply::make(false, 'Please define Formula ' . $formula);
    }


    public function compareAnd($conditions, $dynamicIndex = null)
    {
        $log = [];
        foreach ($conditions as $condition) {

            if (is_array($condition)) {
                if (count($condition) == 3 && in_array($condition[1], ['<', '>', '=', '>=', '<='])) {
                    $result = $this->compare($condition, $dynamicIndex);
                    if (!$result['result']) return $result;
                } else {
                    $result = $this->compareOr($condition, $dynamicIndex);
                    if (!$result['result']) return $result;
                }

                $log[] = $result['message'];
                if ($result['data'] === null) return Reply::make(true, implode(" AND ", $log), null);
                if (!$result['data']) return Reply::make(true, implode(" AND ", $log), false);
            } else {
                return Reply::make(false, 'And condition must be an array');
            }
        }

        return Reply::make(true, implode(" AND ", $log), true);
    }

    public function compareOr($conditions, $dynamicIndex = null)
    {
        $log = [];
        foreach ($conditions as $condition) {
            $result = $this->compareAnd($condition, $dynamicIndex);
            if (!$result['result']) return $result;
            $log[] = $result['message'];
            if ($result['data'] === null) return Reply::make(true, implode(" OR ", $log), null);
            if ($result['data']) return Reply::make(true, implode(" OR ", $log), true);
        }
        return Reply::make(true, implode(" OR ", $log), false);
    }


    public function calIndicate($periodData, $data, $frame, $type)
    {
        $colPrefix = 'candle_' . $frame . '_';
        if ($type == 'lab') $colPrefix = 'lab_candle_' . $frame . '_';

        foreach ([5, 9, 12, 13, 26] as $N) {
            $colName = $colPrefix . 'ema' . $N;
            $K = 2 / ($N + 1);
            $data->{$colName} = doubleval($periodData->{$colName}) * (1 - $K) + doubleval($data->{$colPrefix . 'close'}) * $K;

            if ($N == 13 && $frame == '15m') {

                $data->{$colPrefix . 'macd'} = doubleval($data->{$colPrefix . 'ema5'}) - $data->{$colName};
            }
            if ($N == 26 && $frame != '15m') {
                $data->{$colPrefix . 'macd'} = doubleval($data->{$colPrefix . 'ema12'}) - $data->{$colName};
            }
        }

        foreach ([9, 2, 3, 4, 5] as $N) {
            $signalCol = $colPrefix . 'signal' . ($N == 9 ? '' : $N);
            $histoCol = $colPrefix . 'histogram' . ($N == 9 ? '' : $N);
            $K = 2 / ($N + 1);
            $data->{$signalCol} = doubleval($periodData->{$signalCol}) * (1 - $K) + $data->{$colPrefix . 'macd'} * $K;
            $data->{$histoCol} = doubleval($data->{$colPrefix . 'macd'}) - $data->{$signalCol};
        }

        if ($frame == '15m' || $frame == '1h' || $frame == '4h') {
            foreach ([14] as $N) {

                $close = doubleval($data->{$colPrefix . 'close'});
                $periodClose = doubleval($periodData->{$colPrefix . 'close'});
                $Ut = 0;
                $Dt = 0;
                if ($close > $periodClose) {
                    $Ut = $close - $periodClose;
                } else if ($close < $periodClose) {
                    $Dt = $periodClose - $close;
                }
                $avgUCol = $colPrefix . 'avgu' . $N;
                $avgDCol = $colPrefix . 'avgd' . $N;
                $rsiCol = $colPrefix . 'rsi' . $N;
                $avgU = 1 / $N * $Ut + (1 - 1 / $N) * doubleval($periodData->{$avgUCol});
                $avgD = 1 / $N * $Dt + (1 - 1 / $N) * doubleval($periodData->{$avgDCol});
                if ($avgD != 0) {
                    $RS = $avgU / $avgD;
                    $RSI = 100 - 100 / (1 + $RS);
                    $data->{$avgUCol} = $avgU;
                    $data->{$avgDCol} = $avgD;
                    $data->{$rsiCol} = $RSI;
                }
            }
            foreach ([9, 5, 4] as $N) {
                $colName = $colPrefix . 'rsi_ema' . $N;
                $K = 2 / ($N + 1);
                $data->{$colName} = doubleval($periodData->{$colName}) * (1 - $K) + doubleval($data->{$colPrefix . 'rsi14'}) * $K;
            }
        }

        return $data;
    }


    /**
     * @return null attribute of a flow by flow's name
     */
    private function getFlowData($flowName, $key)
    {
        $default = [
            'timelife' => 6,
            'interval' => 0,
            'takeprofit' => false,
            'stoploss' => false,
            'step_profit' => 0.1,
            'back_profit' => 0.1,
            'baseprofit' => 0.8,
            'baseprofit_baseon' => 'close',
            'margin' => 1,
            'allow_negative_price_rate' => true,
        ];

        $flowData = $this->cfgStrategy[$flowName];
        return get($flowData[$key], get($default[$key], null));
    }

    private function processStrategy($id)
    {
        $strategyModel = Models::get('Admin/Strategies');
        $strategy = $strategyModel->read([[[STRATEGY_ID, '=', $id]]]);
        if (!$strategy['result'] || !isset($strategy['data'][0])) return Reply::make(false, 'Can not find strategy ' . $id);
        $strategy = $strategy['data'][0];

        if ($strategy->{STRATEGY_CONTAINER}) {
            $flows = [];
            $conatinerModel = Models::get('Admin/Strategy_container');
            $children = $conatinerModel->read([[[STRA_CON_CONTAINER, '=', $id]]], function ($db) {
                $db->orderBy(STRA_CON_WEIGHT, 'ASC');
            });
            if (!$children['result']) return $children;
            $children = $children['data'];

            foreach ($children as $child) {
                $childFlows = $this->processChildStrategy($child->{STRA_CON_CHILD});
                if (!$childFlows['result']) return $childFlows;
                $childFlows = (object)$childFlows['data'];
                foreach ($childFlows as $name => $flow) {
                    $flow['container'] = $id;
                    $flow['strategy_slot'] = $child->{STRA_CON_SLOT};
                    $flow['blacklist'] = json_decode($child->{STRA_CON_BLACKLIST}, true);
                    $flows[$name] = $flow;
                }
            }

            foreach ($flows as $name => $flow) {
                if (!isset($flow['takeprofit'])) $flows[$name]['takeprofit'] = $strategy->{STRATEGY_TAKEPROFIT};
                if (!isset($flow['stoploss'])) $flows[$name]['stoploss'] = $strategy->{STRATEGY_STOPLOSS};
                if (!isset($flow['baseprofit'])) $flows[$name]['baseprofit'] = $strategy->{STRATEGY_BASEPROFIT};
                if (!isset($flow['step_profit'])) $flows[$name]['step_profit'] = $strategy->{STRATEGY_STEPPROFIT};
                if (!isset($flow['back_profit'])) $flows[$name]['back_profit'] = $strategy->{STRATEGY_BACKPROFIT};
                if (!isset($flow['baseprofit_baseon'])) $flows[$name]['baseprofit_baseon'] = $strategy->{STRATEGY_BASEPROFIT_BASEON};
                if (!isset($flow['timelife'])) $flows[$name]['timelife'] = $strategy->{STRATEGY_TIMELIFE};
                if (!isset($flow['interval'])) $flows[$name]['interval'] = $strategy->{STRATEGY_INTERVAL};
                if (!isset($flow['margin'])) $flows[$name]['margin'] = $strategy->{STRATEGY_MARGIN};
            }

            return Reply::make(true, 'Success', $flows);
        } else {
            return $this->processChildStrategy($id);
        }
    }


    private function processChildStrategy($id)
    {

        $strategyModel = Models::get('Admin/Strategies');
        $strategy = $strategyModel->read([[[STRATEGY_ID, '=', $id]]]);
        if (!$strategy['result'] || !isset($strategy['data'][0])) return Reply::make(false, 'Can not find strategy ' . $id);
        $strategy = $strategy['data'][0];

        $content = $strategy->{STRATEGY_CONTENT};
        $content = json_decode($content, true);
        if (!$content) return Reply::make(false, 'Can not decode content of strategy ' . $id);

        $flows = [];

        foreach ($content as $key => $val) {
            if (isset($val['type'])) {
                $val['name'] = $key;
                $flows[$id . '--' . $key] = $val;
            }
        }

        foreach ($content as $key => $val) {
            if (!isset($val['type'])) {
                foreach ($flows as $name => $flow) {
                    if (!isset($flow[$key])) $flows[$name][$key] = $val;
                }
            }
        }

        foreach ($flows as $name => $flow) {
            $flows[$name]['strategy'] = $id;
            if (!isset($flow['takeprofit'])) $flows[$name]['takeprofit'] = $strategy->{STRATEGY_TAKEPROFIT};
            if (!isset($flow['stoploss'])) $flows[$name]['stoploss'] = $strategy->{STRATEGY_STOPLOSS};
            if (!isset($flow['baseprofit'])) $flows[$name]['baseprofit'] = $strategy->{STRATEGY_BASEPROFIT};
            if (!isset($flow['step_profit'])) $flows[$name]['step_profit'] = $strategy->{STRATEGY_STEPPROFIT};
            if (!isset($flow['back_profit'])) $flows[$name]['back_profit'] = $strategy->{STRATEGY_BACKPROFIT};
            if (!isset($flow['baseprofit_baseon'])) $flows[$name]['baseprofit_baseon'] = $strategy->{STRATEGY_BASEPROFIT_BASEON};
            if (!isset($flow['timelife'])) $flows[$name]['timelife'] = $strategy->{STRATEGY_TIMELIFE};
            if (!isset($flow['interval'])) $flows[$name]['interval'] = $strategy->{STRATEGY_INTERVAL};
            if (!isset($flow['margin'])) $flows[$name]['margin'] = $strategy->{STRATEGY_MARGIN};
        }

        return Reply::make(true, 'Success', $flows);
    }




    private function processLabStrategy($id)
    {
        $strategyModel = Models::get('Admin/Lab_strategies');
        $strategy = $strategyModel->read([[[LAB_STRATEGY_ID, '=', $id]]]);
        if (!$strategy['result'] || !isset($strategy['data'][0])) return Reply::make(false, 'Can not find strategy ' . $id);
        $strategy = $strategy['data'][0];

        if ($strategy->{LAB_STRATEGY_CONTAINER}) {
            $flows = [];
            $conatinerModel = Models::get('Admin/Lab_strategy_container');
            $children = $conatinerModel->read([[[LAB_STRA_CON_CONTAINER, '=', $id]]], function ($db) {
                $db->orderBy(LAB_STRA_CON_WEIGHT, 'ASC');
            });
            if (!$children['result']) return $children;
            $children = $children['data'];

            foreach ($children as $child) {
                $childFlows = $this->processLabChildStrategy($child->{LAB_STRA_CON_CHILD});
                if (!$childFlows['result']) return $childFlows;
                $childFlows = (object)$childFlows['data'];
                foreach ($childFlows as $name => $flow) {
                    $flow['container'] = $id;
                    $flow['strategy_slot'] = $child->{LAB_STRA_CON_SLOT};
                    $flow['blacklist'] = json_decode($child->{LAB_STRA_CON_BLACKLIST}, true);
                    $flows[$name] = $flow;
                }
            }

            foreach ($flows as $name => $flow) {
                if (!isset($flow['takeprofit'])) $flows[$name]['takeprofit'] = $strategy->{LAB_STRATEGY_TAKEPROFIT};
                if (!isset($flow['stoploss'])) $flows[$name]['stoploss'] = $strategy->{LAB_STRATEGY_STOPLOSS};
                if (!isset($flow['baseprofit'])) $flows[$name]['baseprofit'] = $strategy->{LAB_STRATEGY_BASEPROFIT};
                if (!isset($flow['step_profit'])) $flows[$name]['step_profit'] = $strategy->{LAB_STRATEGY_STEPPROFIT};
                if (!isset($flow['back_profit'])) $flows[$name]['back_profit'] = $strategy->{LAB_STRATEGY_BACKPROFIT};
                if (!isset($flow['baseprofit_baseon'])) $flows[$name]['baseprofit_baseon'] = $strategy->{LAB_STRATEGY_BASEPROFIT_BASEON};
                if (!isset($flow['timelife'])) $flows[$name]['timelife'] = $strategy->{LAB_STRATEGY_TIMELIFE};
                if (!isset($flow['interval'])) $flows[$name]['interval'] = $strategy->{LAB_STRATEGY_INTERVAL};
                if (!isset($flow['margin'])) $flows[$name]['margin'] = $strategy->{LAB_STRATEGY_MARGIN};
            }

            return Reply::make(true, 'Success', $flows);
        } else {
            return $this->processLabChildStrategy($id);
        }
    }


    private function processLabChildStrategy($id)
    {

        $strategyModel = Models::get('Admin/Lab_strategies');
        $strategy = $strategyModel->read([[[LAB_STRATEGY_ID, '=', $id]]]);
        if (!$strategy['result'] || !isset($strategy['data'][0])) return Reply::make(false, 'Can not find strategy ' . $id);
        $strategy = $strategy['data'][0];

        $content = $strategy->{LAB_STRATEGY_CONTENT};
        $content = json_decode($content, true);
        if (!$content) return Reply::make(false, 'Can not decode content of strategy ' . $id);

        $flows = [];

        foreach ($content as $key => $val) {
            if (isset($val['type'])) {
                $val['name'] = $key;
                $flows[$id . '--' . $key] = $val;
            }
        }

        foreach ($content as $key => $val) {
            if (!isset($val['type'])) {
                foreach ($flows as $name => $flow) {
                    if (!isset($flow[$key])) $flows[$name][$key] = $val;
                }
            }
        }

        foreach ($flows as $name => $flow) {
            $flows[$name]['strategy'] = $id;
            if (!isset($flow['takeprofit'])) $flows[$name]['takeprofit'] = $strategy->{LAB_STRATEGY_TAKEPROFIT};
            if (!isset($flow['stoploss'])) $flows[$name]['stoploss'] = $strategy->{LAB_STRATEGY_STOPLOSS};
            if (!isset($flow['baseprofit'])) $flows[$name]['baseprofit'] = $strategy->{LAB_STRATEGY_BASEPROFIT};
            if (!isset($flow['step_profit'])) $flows[$name]['step_profit'] = $strategy->{LAB_STRATEGY_STEPPROFIT};
            if (!isset($flow['back_profit'])) $flows[$name]['back_profit'] = $strategy->{LAB_STRATEGY_BACKPROFIT};
            if (!isset($flow['baseprofit_baseon'])) $flows[$name]['baseprofit_baseon'] = $strategy->{LAB_STRATEGY_BASEPROFIT_BASEON};
            if (!isset($flow['timelife'])) $flows[$name]['timelife'] = $strategy->{LAB_STRATEGY_TIMELIFE};
            if (!isset($flow['interval'])) $flows[$name]['interval'] = $strategy->{LAB_STRATEGY_INTERVAL};
            if (!isset($flow['margin'])) $flows[$name]['margin'] = $strategy->{LAB_STRATEGY_MARGIN};
        }

        return Reply::make(true, 'Success', $flows);
    }




    private $getPrecisionResult = null;
    private function getPrecision($symbol)
    {
        if ($this->getPrecisionResult == null) {

            $precision = Ctrl::get('getPrecisionResult', null, true);
            if ($precision == null || intval($precision['time']) < (time() - 86400)) {
                $this->getPrecisionResult = [];
                echo "Get exchangeInfo \n";
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

                    Ctrl::set('getPrecisionResult', json_encode([
                        'time' => time(),
                        'data' => $this->getPrecisionResult
                    ]));
                }
            }else{
                $this->getPrecisionResult = $precision['data'];
            }
        }

        if (isset($this->getPrecisionResult[$symbol])) return $this->getPrecisionResult[$symbol];
        return false;
    }
}

<?php

namespace App\Crawler\Caculator;

use App\Helpers\DB\Models;
use App\Helpers\Request\Query;
use App\Helpers\Request\Reply;

class RsiRealtime
{

    function __construct()
    {
    }

    public static function caculate($symbol, $interval, $N = 14, &$startObjectIndex, &$restObjectIndex = null, $setStartPoint = false, $clone=false)
    {

        $index = 'rsi_' . $interval . '_' . $N;

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
            'CANDLE_MACD' => "candle_" . $interval . "_macd",
            'CANDLE_SIGNAL' => "candle_" . $interval . "_signal",
            'CANDLE_HISTOGRAM' => "candle_" . $interval . "_histogram",
            'CANDLE_SIGNAL7' => 'candle_' . $interval . '_signal7',
            'CANDLE_HISTOGRAM7' => 'candle_' . $interval . '_histogram7',
            'CANDLE_SIGNAL4' => 'candle_' . $interval . '_signal4',
            'CANDLE_HISTOGRAM4' => 'candle_' . $interval . '_histogram4',
            'CANDLE_SIGNAL2' => 'candle_' . $interval . '_signal2',
            'CANDLE_HISTOGRAM2' => 'candle_' . $interval . '_histogram2',
            'CANDLE_SIGNAL3' => 'candle_' . $interval . '_signal3',
            'CANDLE_HISTOGRAM3' => 'candle_' . $interval . '_histogram3',
            'CANDLE_SIGNAL5' => 'candle_' . $interval . '_signal5',
            'CANDLE_HISTOGRAM5' => 'candle_' . $interval . '_histogram5',
            'CANDLE_SIGNAL6' => 'candle_' . $interval . '_signal6',
            'CANDLE_HISTOGRAM6' => 'candle_' . $interval . '_histogram6',
            'CANDLE_AVGU' => 'candle_' . $interval . '_avgu' . $N,
            'CANDLE_AVGD' => 'candle_' . $interval . '_avgd' . $N,
            'CANDLE_RSI' => 'candle_' . $interval . '_rsi' . $N,
            'CANDLE_RSI_EMA9' => 'candle_' . $interval . '_rsi_ema9',
            'CANDLE_RSI_EMA5' => 'candle_' . $interval . '_rsi_ema5',
            'CANDLE_RSI_EMA4' => 'candle_' . $interval . '_rsi_ema4',
        ];

        if ($clone) {
            $model = Models::clone('Admin/Candle_' . $interval);
        } else {
            $model = Models::get('Admin/Candle_' . $interval);
        }

        if (!isset($startObjectIndex[$index]) || $startObjectIndex[$index] == null) {

            echo "Caculate start object for signal $index\n";

            $firstData = $model->read([[[$columnName['CANDLE_SYMBOL'], '=', $symbol], [$columnName['CANDLE_AVGU'], '<>', 0]]], function ($db) use ($columnName) {
                $db->orderBy($columnName['CANDLE_CLOSE_TIME'], 'DESC')->limit(1);
            });

            if (!$firstData['result']) return $firstData;

            if (isset($firstData['data'][0])) {
                $startObjectIndex[$index] = $firstData['data'][0];
            }

            if (!isset($startObjectIndex[$index])) {

                $firstData = $model->read([[[$columnName['CANDLE_SYMBOL'], '=', $symbol]]], function ($db) use ($columnName, $N) {
                    $db->orderBy($columnName['CANDLE_CLOSE_TIME'], 'ASC')->limit($N + 1);
                });

                $firstData = $firstData['data'];

                if (count($firstData) == $N + 1) {
                    $sumU = 0;
                    $sumD = 0;
                    foreach ($firstData as $key => $item) {

                        if (isset($firstData[$key + 1])) {
                            $periodDelta = doubleval($firstData[$key + 1]->{$columnName['CANDLE_CLOSE']}) - doubleval($firstData[$key]->{$columnName['CANDLE_CLOSE']});
                            if ($periodDelta > 0) {
                                $sumU += $periodDelta;
                            } else if ($periodDelta < 0) {
                                $sumD -= $periodDelta;
                            }
                        }
                    }

                    $firstAvgU = $sumU / $N;
                    $firstAvgD = $sumD / $N;
                    $RS = $firstAvgU / $firstAvgD;
                    $firstRSI = 100 - 100 / (1 + $RS);

                    $startObjectIndex[$index] = $firstData[$N];

                    $model->edit([
                        DATA_KEY => [[[$columnName['CANDLE_ID'], '=', $startObjectIndex[$index]->{$columnName['CANDLE_ID']}]]],
                        DATA_EDITOR => [
                            $columnName['CANDLE_AVGU'] => $firstAvgU,
                            $columnName['CANDLE_AVGD'] => $firstAvgD,
                            $columnName['CANDLE_RSI'] => $firstRSI
                        ]
                    ]);

                    $startObjectIndex[$index]->{$columnName['CANDLE_AVGU']} = $firstAvgU;
                    $startObjectIndex[$index]->{$columnName['CANDLE_AVGD']} = $firstAvgD;
                    $startObjectIndex[$index]->{$columnName['CANDLE_RSI']} = $firstRSI;
                }
            }
        }

        if (!isset($startObjectIndex[$index])) return Reply::make(false, 'Can not get start object');

        $firstAvgU = $startObjectIndex[$index]->{$columnName['CANDLE_AVGU']};
        $firstAvgD = $startObjectIndex[$index]->{$columnName['CANDLE_AVGD']};

        $startPoint = $startObjectIndex[$index]->{$columnName['CANDLE_CLOSE_TIME']};

        if ($firstAvgU === null || $firstAvgD === null) return Reply::make(false, 'Can not caculate Fist AVG');

        if ($restObjectIndex == null) {

            echo "Caculate rest object for RSI $index\n";

            $restObjects = $model->read([[
                [$columnName['CANDLE_SYMBOL'], '=', $symbol],
                [$columnName['CANDLE_CLOSE_TIME'], '>', $startPoint],
                [$columnName['CANDLE_AVGU'], '=', null]

            ]], function ($db) use ($columnName) {
                $db->orderBy($columnName['CANDLE_CLOSE_TIME'], 'ASC');
            });
            if (!$restObjects['result']) return $restObjects;

            $restObjects = $restObjects['data'];

            $periodAvgU = $firstAvgU;
            $periodAvgD = $firstAvgD;
            $periodClose = doubleval($startObjectIndex[$index]->{$columnName['CANDLE_CLOSE']});

            foreach ($restObjects as $key => $restObject) {
                $close = doubleval($restObject->{$columnName['CANDLE_CLOSE']});
                $open = doubleval($restObject->{$columnName['CANDLE_OPEN']});
                $Ut = 0;
                $Dt = 0;
                if ($close > $periodClose) {
                    $Ut = $close - $periodClose;
                } else if ($close < $periodClose) {
                    $Dt = $periodClose - $close;
                }

                $avgU = 1 / $N * $Ut + (1 - 1 / $N) * $periodAvgU;
                $avgD = 1 / $N * $Dt + (1 - 1 / $N) * $periodAvgD;
                $RS = $avgU / $avgD;
                $RSI = 100 - 100 / (1 + $RS);

                $result = $model->edit([
                    DATA_KEY => [[[$columnName['CANDLE_ID'], '=', $restObject->{$columnName['CANDLE_ID']}]]],
                    DATA_EDITOR => [
                        $columnName['CANDLE_AVGU'] => $avgU,
                        $columnName['CANDLE_AVGD'] => $avgD,
                        $columnName['CANDLE_RSI'] => $RSI
                    ]
                ]);
                if (!$result['result']) return $result;

                $restObject->{$columnName['CANDLE_AVGU']} = $avgU;
                $restObject->{$columnName['CANDLE_AVGD']} = $avgD;
                $restObject->{$columnName['CANDLE_RSI']} = $RSI;

                $restObjects[$key] = $restObject;

                $periodAvgU = $avgU;
                $periodAvgD = $avgD;
                $periodClose = $close;
            }

            if (count($restObjects) >= 2) {
                $startObjectIndex[$index] = $restObjects[count($restObjects) - 2];
            }

        } else {

            $close = doubleval($restObjectIndex->{$columnName['CANDLE_CLOSE']});
            $open = doubleval($restObjectIndex->{$columnName['CANDLE_OPEN']});
            $periodClose = doubleval($startObjectIndex[$index]->{$columnName['CANDLE_CLOSE']});
            $periodAvgU = doubleval($startObjectIndex[$index]->{$columnName['CANDLE_AVGU']});
            $periodAvgD = doubleval($startObjectIndex[$index]->{$columnName['CANDLE_AVGD']});

            $Ut = 0;
            $Dt = 0;
            if ($close > $periodClose) {
                $Ut = $close - $periodClose;
            } else if ($close < $periodClose) {
                $Dt = $periodClose - $close;
            }

            $avgU = 1 / $N * $Ut + (1 - 1 / $N) * $periodAvgU;
            $avgD = 1 / $N * $Dt + (1 - 1 / $N) * $periodAvgD;
            $RS = $avgU / $avgD;
            $RSI = 100 - 100 / (1 + $RS);

            $restObjectIndex->{$columnName['CANDLE_AVGU']} = $avgU;
            $restObjectIndex->{$columnName['CANDLE_AVGD']} = $avgD;
            $restObjectIndex->{$columnName['CANDLE_RSI']} = $RSI;

            if ($setStartPoint) {
                $startObjectIndex[$index] = $restObjectIndex;
            }
        }

        return Reply::make(true, 'success');
    }
}

<?php

namespace App\Crawler\Caculator;

use App\Helpers\DB\Models;
use App\Helpers\Request\Query;
use App\Helpers\Request\Reply;

class EmaRealtime
{

    function __construct()
    {
    }

    public static function caculate($symbol, $interval, $N, &$startObjectIndex, &$restObjectIndex = null, $setStartPoint = false, $clone = false)
    {

        $index = $interval . '_' . $N;

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
            'CANDLE_EMA' => "candle_" . $interval . "_ema" . $N,
            'CANDLE_SIGNAL' => "candle_" . $interval . "_signal",
            'CANDLE_HISTOGRAM' => "candle_" . $interval . "_histogram",
        ];

        if($clone){
            $model = Models::clone('Admin/Candle_' . $interval);
        }else{
            $model = Models::get('Admin/Candle_' . $interval);
        }
        

        if (!isset($startObjectIndex[$index])) {

            echo "Caculate start object for $index\n";

            $firstEmas = $model->read([[[$columnName['CANDLE_SYMBOL'], '=', $symbol], [$columnName['CANDLE_EMA'], '>', 0]]], function ($db) use ($N, $columnName) {
                $db->orderBy($columnName['CANDLE_CLOSE_TIME'], 'DESC')->limit(2);
            });

            if (!$firstEmas['result']) return $firstEmas;

            if ($firstEmas['result']) {
                if (isset($firstEmas['data'][1])) {
                    $startObjectIndex[$index] = $firstEmas['data'][1];
                } else if (isset($firstEmas['data'][0])) {
                    $startObjectIndex[$index] = $firstEmas['data'][0];
                }
            }


            if (!isset($startObjectIndex[$index])) {

                $firstEmas = $model->read([[[$columnName['CANDLE_SYMBOL'], '=', $symbol]]], function ($db) use ($N, $columnName) {
                    $db->orderBy($columnName['CANDLE_CLOSE_TIME'], 'ASC')->limit($N);
                });

                $firstEmas = $firstEmas['data'];

                if (count($firstEmas) == $N) {
                    $avg = 0;
                    foreach ($firstEmas as $item) {
                        $avg += (float)$item->{$columnName['CANDLE_CLOSE']} / $N;
                    }
                    $firstEma = $avg;

                    $startObjectIndex[$index] = $firstEmas[$N - 1];

                    $model->edit([
                        DATA_KEY => [[[$columnName['CANDLE_ID'], '=', $startObjectIndex[$index]->{$columnName['CANDLE_ID']}]]],
                        DATA_EDITOR => [$columnName['CANDLE_EMA'] => $firstEma]
                    ]);

                    $startObjectIndex[$index]->{$columnName['CANDLE_EMA']} = $firstEma;
                }
            }


            if ($N == 13 && $interval == '15m') {

                if ($startObjectIndex[$index]->{$columnName['CANDLE_EMA5']} != null) {

                    $fisrtMacd = doubleval($startObjectIndex[$index]->{$columnName['CANDLE_EMA5']}) - doubleval($startObjectIndex[$index]->{$columnName['CANDLE_EMA']});

                    $model->edit([
                        DATA_KEY => [[[$columnName['CANDLE_ID'], '=', $startObjectIndex[$index]->{$columnName['CANDLE_ID']}]]],
                        DATA_EDITOR => [$columnName['CANDLE_MACD'] => $fisrtMacd]
                    ]);

                    $startObjectIndex[$index]->{$columnName['CANDLE_MACD']} = $fisrtMacd;
                }
            }
            if ($N == 26 && $interval != '15m') {

                if ($startObjectIndex[$index]->{$columnName['CANDLE_EMA12']} != null) {

                    $fisrtMacd = doubleval($startObjectIndex[$index]->{$columnName['CANDLE_EMA12']}) - doubleval($startObjectIndex[$index]->{$columnName['CANDLE_EMA']});

                    $model->edit([
                        DATA_KEY => [[[$columnName['CANDLE_ID'], '=', $startObjectIndex[$index]->{$columnName['CANDLE_ID']}]]],
                        DATA_EDITOR => [$columnName['CANDLE_MACD'] => $fisrtMacd]
                    ]);

                    $startObjectIndex[$index]->{$columnName['CANDLE_MACD']} = $fisrtMacd;
                }
            }
        }

        $firstEma = $startObjectIndex[$index]->{$columnName['CANDLE_EMA']};
        $startPoint = $startObjectIndex[$index]->{$columnName['CANDLE_CLOSE_TIME']};

        if (!$firstEma > 0) return Reply::make(false, 'Can not caculate EMA');

        $K = 2 / ($N + 1);

        if ($restObjectIndex == null) {
            echo "Get rest Objects $index\n";
            $restObjectsDB = $model->read([[[$columnName['CANDLE_SYMBOL'], '=', $symbol], [$columnName['CANDLE_CLOSE_TIME'], '>', $startPoint]]], function ($db) use ($columnName) {
                $db->orderBy($columnName['CANDLE_CLOSE_TIME'], 'ASC');
            });
            if (!$restObjectsDB['result']) return $restObjectsDB;

            $restObjectsDB = $restObjectsDB['data'];

            $periodEma = $firstEma;

            foreach ($restObjectsDB as $key => $restObject) {
                $ema = $periodEma * (1 - $K) + $restObject->{$columnName['CANDLE_CLOSE']} * $K;

                $insert = false;

                if ($N == 13 && $interval == '15m') {
                    if ($restObject->{$columnName['CANDLE_EMA5']} != null) {
                        $macd = doubleval($restObject->{$columnName['CANDLE_EMA5']}) - doubleval($ema);

                        $result = $model->edit([
                            DATA_KEY => [[[$columnName['CANDLE_ID'], '=', $restObject->{$columnName['CANDLE_ID']}]]],
                            DATA_EDITOR => [$columnName['CANDLE_MACD'] => $macd, $columnName['CANDLE_EMA'] => $ema]
                        ]);
                        if (!$result['result']) return $result;

                        $restObject->{$columnName['CANDLE_MACD']} = $macd;
                        $restObject->{$columnName['CANDLE_EMA']} = $ema;
                        $insert = true;
                    }
                }
                if ($N == 26 && $interval != '15m') {
                    if ($restObject->{$columnName['CANDLE_EMA12']} != null) {
                        $macd = doubleval($restObject->{$columnName['CANDLE_EMA12']}) - doubleval($ema);

                        $result = $model->edit([
                            DATA_KEY => [[[$columnName['CANDLE_ID'], '=', $restObject->{$columnName['CANDLE_ID']}]]],
                            DATA_EDITOR => [$columnName['CANDLE_MACD'] => $macd, $columnName['CANDLE_EMA'] => $ema]
                        ]);
                        if (!$result['result']) return $result;

                        $restObject->{$columnName['CANDLE_MACD']} = $macd;
                        $restObject->{$columnName['CANDLE_EMA']} = $ema;
                        $insert = true;
                    }
                }

                if (!$insert) {

                    $result = $model->edit([
                        DATA_KEY => [[[$columnName['CANDLE_ID'], '=', $restObject->{$columnName['CANDLE_ID']}]]],
                        DATA_EDITOR => [$columnName['CANDLE_EMA'] => $ema]
                    ]);
                    if (!$result['result']) return $result;

                    $restObject->{$columnName['CANDLE_EMA']} = $ema;
                }

                $periodEma = $ema;
            }

            if (count($restObjectsDB) >= 2) {
                $startObjectIndex[$index] = $restObjectsDB[count($restObjectsDB) - 2];
            }

        } else {

            $ema = $firstEma * (1 - $K) + $restObjectIndex->{$columnName['CANDLE_CLOSE']} * $K;

            $insert = false;

            if ($N == 13 && $interval == '15m') {
                if ($restObjectIndex->{$columnName['CANDLE_EMA5']} != null) {
                    $macd = doubleval($restObjectIndex->{$columnName['CANDLE_EMA5']}) - doubleval($ema);
                    $restObjectIndex->{$columnName['CANDLE_MACD']} = $macd;
                    $restObjectIndex->{$columnName['CANDLE_EMA']} = $ema;
                    $insert = true;
                }
            }
            if ($N == 26 && $interval != '15m') {
                if ($restObjectIndex->{$columnName['CANDLE_EMA12']} != null) {
                    $macd = doubleval($restObjectIndex->{$columnName['CANDLE_EMA12']}) - doubleval($ema);
                    $restObjectIndex->{$columnName['CANDLE_MACD']} = $macd;
                    $restObjectIndex->{$columnName['CANDLE_EMA']} = $ema;
                    $insert = true;
                }
            }

            if (!$insert) {
                $restObjectIndex->{$columnName['CANDLE_EMA']} = $ema;
            }

            if ($setStartPoint) {
                $startObjectIndex[$index] = $restObjectIndex;
            }

        }

        return Reply::make(true, 'success');
    }
}

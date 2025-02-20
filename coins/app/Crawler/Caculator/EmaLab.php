<?php

namespace App\Crawler\Caculator;

use App\Helpers\DB\Models;
use App\Helpers\Request\Query;
use App\Helpers\Request\Reply;

class EmaLab
{

    function __construct()
    {
    }

    public static function caculate($symbol, $interval, $N, &$startObjectIndex, &$restPointIndex=null, $clone = false)
    {
        $columnName = [
            'LAB_CANDLE_ID' => "lab_candle_" . $interval . "_id",
            'LAB_CANDLE_SYMBOL' => "lab_candle_" . $interval . "_symbol",
            'LAB_CANDLE_TIME' => "lab_candle_" . $interval . "_time",
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
            'LAB_CANDLE_MACD' => "lab_candle_" . $interval . "_macd",
            'LAB_CANDLE_EMA' => "lab_candle_" . $interval . "_ema" . $N,
            'LAB_CANDLE_SIGNAL' => "lab_candle_" . $interval . "_signal",
            'LAB_CANDLE_HISTOGRAM' => "lab_candle_" . $interval . "_histogram",
            'LAB_CANDLE_STARTPOINT' => "lab_candle_" . $interval . "_startpoint",
        ];

        if($clone){
            $model = Models::clone('Admin/Lab_candle_' . $interval);
        }else{
            $model = Models::get('Admin/Lab_candle_' . $interval);
        }

        $index = $interval . "_" . $N;

        if (!isset($startObjectIndex[$index]) || $startObjectIndex[$index] == null) {

            echo "Caculate start object for $index\n";

            $firstEmas = $model->read([[[$columnName['LAB_CANDLE_SYMBOL'], '=', $symbol], [$columnName['LAB_CANDLE_STARTPOINT'], '=', 1], [$columnName['LAB_CANDLE_EMA'], '>', 0]]], function ($db) use ($N, $columnName) {
                $db->orderBy($columnName['LAB_CANDLE_CLOSE_TIME'], 'DESC')->limit(1);
            });

            if (!$firstEmas['result']) return $firstEmas;

            if (isset($firstEmas['data'][0])) {
                $startObjectIndex[$index] = $firstEmas['data'][0];
            }

            if (!isset($startObjectIndex[$index])) {

                $firstEmas = $model->read([[[$columnName['LAB_CANDLE_SYMBOL'], '=', $symbol], [$columnName['LAB_CANDLE_STARTPOINT'], '=', 1]]], function ($db) use ($N, $columnName) {
                    $db->orderBy($columnName['LAB_CANDLE_CLOSE_TIME'], 'ASC')->limit($N);
                });

                $firstEmas = $firstEmas['data'];

                if (count($firstEmas) == $N) {
                    $avg = 0;
                    foreach ($firstEmas as $item) {
                        $avg += (float)$item->{$columnName['LAB_CANDLE_CLOSE']} / $N;
                    }
                    $firstEma = $avg;

                    $startObjectIndex[$index] = $firstEmas[$N - 1];

                    $model->edit([
                        DATA_KEY => [[[$columnName['LAB_CANDLE_ID'], '=', $startObjectIndex[$index]->{$columnName['LAB_CANDLE_ID']}]]],
                        DATA_EDITOR => [$columnName['LAB_CANDLE_EMA'] => $firstEma]
                    ]);

                    $startObjectIndex[$index]->{$columnName['LAB_CANDLE_EMA']} = $firstEma;
                }
            }


            if ($N == 13 && $interval == '15m') {

                if ($startObjectIndex[$index]->{$columnName['LAB_CANDLE_EMA5']} != null) {

                    $fisrtMacd = doubleval($startObjectIndex[$index]->{$columnName['LAB_CANDLE_EMA5']}) - doubleval($startObjectIndex[$index]->{$columnName['LAB_CANDLE_EMA']});

                    $model->edit([
                        DATA_KEY => [[[$columnName['LAB_CANDLE_ID'], '=', $startObjectIndex[$index]->{$columnName['LAB_CANDLE_ID']}]]],
                        DATA_EDITOR => [$columnName['LAB_CANDLE_MACD'] => $fisrtMacd]
                    ]);

                    $startObjectIndex[$index]->{$columnName['LAB_CANDLE_MACD']} = $fisrtMacd;
                }
            }


            if ($N == 26 && $interval != '15m') {

                if ($startObjectIndex[$index]->{$columnName['LAB_CANDLE_EMA12']} != null) {

                    $fisrtMacd = doubleval($startObjectIndex[$index]->{$columnName['LAB_CANDLE_EMA12']}) - doubleval($startObjectIndex[$index]->{$columnName['LAB_CANDLE_EMA']});

                    $model->edit([
                        DATA_KEY => [[[$columnName['LAB_CANDLE_ID'], '=', $startObjectIndex[$index]->{$columnName['LAB_CANDLE_ID']}]]],
                        DATA_EDITOR => [$columnName['LAB_CANDLE_MACD'] => $fisrtMacd]
                    ]);

                    $startObjectIndex[$index]->{$columnName['LAB_CANDLE_MACD']} = $fisrtMacd;
                }
            }
        }

        if(!isset($startObjectIndex[$index])) return Reply::make(false, 'Can not get start object');

        $firstEma = $startObjectIndex[$index]->{$columnName['LAB_CANDLE_EMA']};
        $startPoint = $startObjectIndex[$index]->{$columnName['LAB_CANDLE_CLOSE_TIME']};

        if (!$firstEma > 0) return Reply::make(false, 'Can not caculate EMA');

        $K = 2 / ($N + 1);

        if ($restPointIndex == null) {

            $condition = [
                [$columnName['LAB_CANDLE_SYMBOL'], '=', $symbol], 
                [$columnName['LAB_CANDLE_CLOSE_TIME'], '>', $startPoint],
                [$columnName['LAB_CANDLE_EMA'], '=', null],
                
            ];

            $restPoints = $model->read([$condition], function ($db) use ($columnName) {
                $db->orderBy($columnName['LAB_CANDLE_CLOSE_TIME'], 'ASC');
            });

            if (!$restPoints['result']) return $restPoints;

            $restPoints = $restPoints['data'];

            $periodEma = $firstEma;
    
            $ema = null;
            foreach ($restPoints as $restPoint) {
                $ema = $periodEma * (1 - $K) + $restPoint->{$columnName['LAB_CANDLE_CLOSE']} * $K;

                $insert = false;


                if ($N == 13 && $interval == '15m') {
                    if ($restPoint->{$columnName['LAB_CANDLE_EMA5']} != null) {
                        $macd = doubleval($restPoint->{$columnName['LAB_CANDLE_EMA5']}) - doubleval($ema);
                        $result = $model->edit([
                            DATA_KEY => [[[$columnName['LAB_CANDLE_ID'], '=', $restPoint->{$columnName['LAB_CANDLE_ID']}]]],
                            DATA_EDITOR => [$columnName['LAB_CANDLE_MACD'] => $macd, $columnName['LAB_CANDLE_EMA'] => $ema]
                        ]);
                        if (!$result['result']) return $result;
                        $restPoint->{$columnName['LAB_CANDLE_MACD']} = $macd;
                        $restPoint->{$columnName['LAB_CANDLE_EMA']} = $ema;
                        $insert = true;
                    }
                }

                if ($N == 26 && $interval != '15m') {
                    if ($restPoint->{$columnName['LAB_CANDLE_EMA12']} != null) {
                        $macd = doubleval($restPoint->{$columnName['LAB_CANDLE_EMA12']}) - doubleval($ema);
                        $result = $model->edit([
                            DATA_KEY => [[[$columnName['LAB_CANDLE_ID'], '=', $restPoint->{$columnName['LAB_CANDLE_ID']}]]],
                            DATA_EDITOR => [$columnName['LAB_CANDLE_MACD'] => $macd, $columnName['LAB_CANDLE_EMA'] => $ema]
                        ]);
                        if (!$result['result']) return $result;
                        $restPoint->{$columnName['LAB_CANDLE_MACD']} = $macd;
                        $restPoint->{$columnName['LAB_CANDLE_EMA']} = $ema;
                        $insert = true;
                    }
                }

                if (!$insert) {
                    $result = $model->edit([
                        DATA_KEY => [[[$columnName['LAB_CANDLE_ID'], '=', $restPoint->{$columnName['LAB_CANDLE_ID']}]]],
                        DATA_EDITOR => [$columnName['LAB_CANDLE_EMA'] => $ema]
                    ]);
                    if (!$result['result']) return $result;
                    $restPoint->{$columnName['LAB_CANDLE_EMA']} = $ema;
                }

                if (isset($restPoint->{$columnName['LAB_CANDLE_STARTPOINT']}) && $restPoint->{$columnName['LAB_CANDLE_STARTPOINT']} == 1) {
                    $periodEma = $ema;
                    $startObjectIndex[$index] = $restPoint;
                }
            }
        } else {

            $periodEma = $firstEma;

            $ema = $periodEma * (1 - $K) + $restPointIndex->{$columnName['LAB_CANDLE_CLOSE']} * $K;

            $insert = false;

            if ($N == 13 && $interval == '15m') {
                if ($restPointIndex->{$columnName['LAB_CANDLE_EMA5']} != null) {
                    $macd = doubleval($restPointIndex->{$columnName['LAB_CANDLE_EMA5']}) - doubleval($ema);
                    $restPointIndex->{$columnName['LAB_CANDLE_MACD']} = $macd;
                    $restPointIndex->{$columnName['LAB_CANDLE_EMA']} = $ema;
                    $insert = true;
                }
            }

            if ($N == 26 && $interval != '15m') {
                if ($restPointIndex->{$columnName['LAB_CANDLE_EMA12']} != null) {
                    $macd = doubleval($restPointIndex->{$columnName['LAB_CANDLE_EMA12']}) - doubleval($ema);
                    $restPointIndex->{$columnName['LAB_CANDLE_MACD']} = $macd;
                    $restPointIndex->{$columnName['LAB_CANDLE_EMA']} = $ema;
                    $insert = true;
                }
            }

            if (!$insert) {
                $restPointIndex->{$columnName['LAB_CANDLE_EMA']} = $ema;
            }

            if (isset($restPointIndex->{$columnName['LAB_CANDLE_STARTPOINT']}) && $restPointIndex->{$columnName['LAB_CANDLE_STARTPOINT']} == 1) {
                
                $startObjectIndex[$index] = $restPointIndex;
            }
        }

        return Reply::make(true, 'success');
    }
}

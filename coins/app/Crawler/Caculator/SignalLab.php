<?php

namespace App\Crawler\Caculator;

use App\Helpers\DB\Models;
use App\Helpers\Request\Query;
use App\Helpers\Request\Reply;

class SignalLab
{

    function __construct()
    {
        
    }

    public static function caculate($symbol, $interval, $N = 9, &$startObjectIndex, &$restObjectIndex = null, $clone=false)
    {

        $index = 'signal_' . $interval . '_' . $N;

        $columnName = [
            'LAB_CANDLE_ID' => "lab_candle_" . $interval . "_id",
            'LAB_CANDLE_TIME' => "lab_candle_" . $interval . "_time",
            'LAB_CANDLE_SYMBOL' => "lab_candle_" . $interval . "_symbol",
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
            'LAB_CANDLE_SIGNAL' => $N == 9 ? "lab_candle_" . $interval . "_signal" : "lab_candle_" . $interval . "_signal" . $N,
            'LAB_CANDLE_HISTOGRAM' => $N == 9 ? "lab_candle_" . $interval . "_histogram" :  "lab_candle_" . $interval . "_histogram" . $N,
            'LAB_CANDLE_SIGNAL7'=>'lab_candle_'.$interval.'_signal7',
            'LAB_CANDLE_HISTOGRAM7'=>'lab_candle_'.$interval.'_histogram7',
            'LAB_CANDLE_SIGNAL4'=>'lab_candle_'.$interval.'_signal4',
            'LAB_CANDLE_HISTOGRAM4'=>'lab_candle_'.$interval.'_histogram4',
            'LAB_CANDLE_SIGNAL2'=>'lab_candle_'.$interval.'_signal2',
            'LAB_CANDLE_HISTOGRAM2'=>'lab_candle_'.$interval.'_histogram2',
            'LAB_CANDLE_SIGNAL3'=>'lab_candle_'.$interval.'_signal3',
            'LAB_CANDLE_HISTOGRAM3'=>'lab_candle_'.$interval.'_histogram3',
            'LAB_CANDLE_SIGNAL5'=>'lab_candle_'.$interval.'_signal5',
            'LAB_CANDLE_HISTOGRAM5'=>'lab_candle_'.$interval.'_histogram5',
            'LAB_CANDLE_SIGNAL6'=>'lab_candle_'.$interval.'_signal6',
            'LAB_CANDLE_HISTOGRAM6'=>'lab_candle_'.$interval.'_histogram6',
            'LAB_CANDLE_STARTPOINT' => "lab_candle_" . $interval . "_startpoint",
        ];

        if($clone){
            $model = Models::clone('Admin/Lab_candle_' . $interval);
        }else{
            $model = Models::get('Admin/Lab_candle_' . $interval);
        }



        if (!isset($startObjectIndex[$index]) || $startObjectIndex[$index] == null) {

            echo "Caculate start object for signal $index\n";

            $firstEmas = $model->read([[[$columnName['LAB_CANDLE_SYMBOL'], '=', $symbol], [$columnName['LAB_CANDLE_STARTPOINT'], '=', 1], [$columnName['LAB_CANDLE_SIGNAL'], '<>', 0]]], function ($db) use ($columnName) {
                $db->orderBy($columnName['LAB_CANDLE_CLOSE_TIME'], 'DESC')->limit(1);
            });

            if (!$firstEmas['result']) return $firstEmas;

            if (isset($firstEmas['data'][0])) {
                $startObjectIndex[$index] = $firstEmas['data'][0];
            }

            if (!isset($startObjectIndex[$index])) {

                $firstEmas = $model->read([[[$columnName['LAB_CANDLE_SYMBOL'], '=', $symbol], [$columnName['LAB_CANDLE_STARTPOINT'], '=', 1], [$columnName['LAB_CANDLE_MACD'], '<>', 0]]], function ($db) use ($columnName, $N) {
                    $db->orderBy($columnName['LAB_CANDLE_CLOSE_TIME'], 'ASC')->limit($N);
                });

                $firstEmas = $firstEmas['data'];

                if (count($firstEmas) == $N) {
                    $avg = 0;
                    foreach ($firstEmas as $item) {
                        $avg += (float)$item->{$columnName['LAB_CANDLE_MACD']} / $N;
                    }
                    $firstEma = $avg;

                    $startObjectIndex[$index] = $firstEmas[$N - 1];

                    $firstGram = doubleval($startObjectIndex[$index]->{$columnName['LAB_CANDLE_MACD']}) - $avg;

                    $model->edit([
                        DATA_KEY => [[[$columnName['LAB_CANDLE_ID'], '=', $startObjectIndex[$index]->{$columnName['LAB_CANDLE_ID']}]]],
                        DATA_EDITOR => [$columnName['LAB_CANDLE_SIGNAL'] => $firstEma, $columnName['LAB_CANDLE_HISTOGRAM'] => $firstGram]
                    ]);

                    $startObjectIndex[$index]->{$columnName['LAB_CANDLE_SIGNAL']} = $firstEma;
                    $startObjectIndex[$index]->{$columnName['LAB_CANDLE_HISTOGRAM']} = $firstGram;
                }
            }
        }

        if(!isset($startObjectIndex[$index])) return Reply::make(false, 'Can not get start object');

        $firstEma = $startObjectIndex[$index]->{$columnName['LAB_CANDLE_SIGNAL']};
        $startPoint = $startObjectIndex[$index]->{$columnName['LAB_CANDLE_CLOSE_TIME']};

        if (!$firstEma > 0) return Reply::make(false, 'Can not caculate Signal');


        $K = 2 / ($N + 1);

        if ($restObjectIndex == null) {

            echo "Caculate rest object for signal $index\n";

            $restObjects = $model->read([[
                [$columnName['LAB_CANDLE_SYMBOL'], '=', $symbol], 
                [$columnName['LAB_CANDLE_CLOSE_TIME'], '>', $startPoint],
                [$columnName['LAB_CANDLE_SIGNAL'], '=', null]

            ]], function ($db) use ($columnName) {
                $db->orderBy($columnName['LAB_CANDLE_CLOSE_TIME'], 'ASC');
            });
            if (!$restObjects['result']) return $restObjects;

            $restObjects = $restObjects['data'];

            $periodEma = $firstEma;
            foreach ($restObjects as $key => $restObject) {
                $ema = $periodEma * (1 - $K) + $restObject->{$columnName['LAB_CANDLE_MACD']} * $K;

                $gram = doubleval($restObject->{$columnName['LAB_CANDLE_MACD']}) - doubleval($ema);

                $result = $model->edit([
                    DATA_KEY => [[[$columnName['LAB_CANDLE_ID'], '=', $restObject->{$columnName['LAB_CANDLE_ID']}]]],
                    DATA_EDITOR => [$columnName['LAB_CANDLE_SIGNAL'] => $ema, $columnName['LAB_CANDLE_HISTOGRAM'] => $gram]
                ]);
                if (!$result['result']) return $result;

                $restObject->{$columnName['LAB_CANDLE_SIGNAL']} = $ema;
                $restObject->{$columnName['LAB_CANDLE_HISTOGRAM']} = $gram;

                $restObjects[$key] = $restObject;

                if (isset($restObject->{$columnName['LAB_CANDLE_STARTPOINT']}) && $restObject->{$columnName['LAB_CANDLE_STARTPOINT']} == 1) {
                    $periodEma = $ema;
                    $startObjectIndex[$index] = $restObject;
                }
            }

        } else {

            $ema = $firstEma * (1 - $K) + $restObjectIndex->{$columnName['LAB_CANDLE_MACD']} * $K;

            $gram = doubleval($restObjectIndex->{$columnName['LAB_CANDLE_MACD']}) - doubleval($ema);
            
            $restObjectIndex->{$columnName['LAB_CANDLE_SIGNAL']} = $ema;
            $restObjectIndex->{$columnName['LAB_CANDLE_HISTOGRAM']} = $gram;

            if (isset($restObjectIndex->{$columnName['LAB_CANDLE_STARTPOINT']}) && $restObjectIndex->{$columnName['LAB_CANDLE_STARTPOINT']} == 1) {
                $startObjectIndex[$index] = $restObjectIndex;
            }
        }

        return Reply::make(true, 'success');
    }
}

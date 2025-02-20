<?php

namespace App\Crawler\Caculator;

use App\Helpers\DB\Models;
use App\Helpers\Request\Query;
use App\Helpers\Request\Reply;

class SignalRealtime
{

    function __construct()
    {
        
    }

    public static function caculate($symbol, $interval, $N = 9, &$startObjectIndex, &$restObjectIndex = null, $setStartPoint = false, $clone=false)
    {

        $index = 'signal_' . $interval . '_' . $N;

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
            'CANDLE_SIGNAL' => $N == 9 ? "candle_" . $interval . "_signal" : "candle_" . $interval . "_signal" . $N,
            'CANDLE_HISTOGRAM' => $N == 9 ? "candle_" . $interval . "_histogram" :  "candle_" . $interval . "_histogram" . $N,
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
        ];

        if($clone){
            $model = Models::clone('Admin/Candle_' . $interval);
        }else{
            $model = Models::get('Admin/Candle_' . $interval);
        }


        if (!isset($startObjectIndex[$index]) || $startObjectIndex[$index] == null) {

            echo "Caculate start object for signal $index\n";

            $firstEmas = $model->read([[[$columnName['CANDLE_SYMBOL'], '=', $symbol], [$columnName['CANDLE_SIGNAL'], '<>', 0]]], function ($db) use ($columnName) {
                $db->orderBy($columnName['CANDLE_CLOSE_TIME'], 'DESC')->limit(1);
            });

            if (!$firstEmas['result']) return $firstEmas;

            if (isset($firstEmas['data'][0])) {
                $startObjectIndex[$index] = $firstEmas['data'][0];
            }

            if (!isset($startObjectIndex[$index])) {

                $firstEmas = $model->read([[[$columnName['CANDLE_SYMBOL'], '=', $symbol], [$columnName['CANDLE_MACD'], '<>', 0]]], function ($db) use ($columnName, $N) {
                    $db->orderBy($columnName['CANDLE_CLOSE_TIME'], 'ASC')->limit($N);
                });

                $firstEmas = $firstEmas['data'];

                if (count($firstEmas) == $N) {
                    $avg = 0;
                    foreach ($firstEmas as $item) {
                        $avg += (float)$item->{$columnName['CANDLE_MACD']} / $N;
                    }
                    $firstEma = $avg;

                    $startObjectIndex[$index] = $firstEmas[$N - 1];

                    $firstGram = doubleval($startObjectIndex[$index]->{$columnName['CANDLE_MACD']}) - $avg;

                    $model->edit([
                        DATA_KEY => [[[$columnName['CANDLE_ID'], '=', $startObjectIndex[$index]->{$columnName['CANDLE_ID']}]]],
                        DATA_EDITOR => [$columnName['CANDLE_SIGNAL'] => $firstEma, $columnName['CANDLE_HISTOGRAM'] => $firstGram]
                    ]);

                    $startObjectIndex[$index]->{$columnName['CANDLE_SIGNAL']} = $firstEma;
                    $startObjectIndex[$index]->{$columnName['CANDLE_HISTOGRAM']} = $firstGram;
                }
            }
        }

        if(!isset($startObjectIndex[$index])) return Reply::make(false, 'Can not get start object');

        $firstEma = $startObjectIndex[$index]->{$columnName['CANDLE_SIGNAL']};
        $startPoint = $startObjectIndex[$index]->{$columnName['CANDLE_CLOSE_TIME']};

        if (!$firstEma > 0) return Reply::make(false, 'Can not caculate Signal');


        $K = 2 / ($N + 1);

        if ($restObjectIndex == null) {

            echo "Caculate rest object for signal $index\n";

            $restObjects = $model->read([[
                [$columnName['CANDLE_SYMBOL'], '=', $symbol], 
                [$columnName['CANDLE_CLOSE_TIME'], '>', $startPoint],
            ]], function ($db) use ($columnName) {
                $db->orderBy($columnName['CANDLE_CLOSE_TIME'], 'ASC');
            });
            if (!$restObjects['result']) return $restObjects;

            $restObjects = $restObjects['data'];

            $periodEma = $firstEma;
            foreach ($restObjects as $key => $restObject) {
                $ema = $periodEma * (1 - $K) + $restObject->{$columnName['CANDLE_MACD']} * $K;

                $gram = doubleval($restObject->{$columnName['CANDLE_MACD']}) - doubleval($ema);

                $result = $model->edit([
                    DATA_KEY => [[[$columnName['CANDLE_ID'], '=', $restObject->{$columnName['CANDLE_ID']}]]],
                    DATA_EDITOR => [$columnName['CANDLE_SIGNAL'] => $ema, $columnName['CANDLE_HISTOGRAM'] => $gram]
                ]);
                if (!$result['result']) return $result;

                $restObject->{$columnName['CANDLE_SIGNAL']} = $ema;
                $restObject->{$columnName['CANDLE_HISTOGRAM']} = $gram;

                $restObjects[$key] = $restObject;

                $periodEma =  $ema;

                
            }

            if (count($restObjects) >= 2) {
                $startObjectIndex[$index] = $restObjects[count($restObjects) - 2];
            }

        } else {

            $ema = $firstEma * (1 - $K) + $restObjectIndex->{$columnName['CANDLE_MACD']} * $K;

            $gram = doubleval($restObjectIndex->{$columnName['CANDLE_MACD']}) - doubleval($ema);
            
            $restObjectIndex->{$columnName['CANDLE_SIGNAL']} = $ema;
            $restObjectIndex->{$columnName['CANDLE_HISTOGRAM']} = $gram;

            if ($setStartPoint) {
                $startObjectIndex[$index] = $restObjectIndex;
            }
        }

        return Reply::make(true, 'success');
    }
}

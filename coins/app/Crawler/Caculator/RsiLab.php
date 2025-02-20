<?php

namespace App\Crawler\Caculator;

use App\Helpers\DB\Models;
use App\Helpers\Request\Query;
use App\Helpers\Request\Reply;

class RsiLab
{

    function __construct()
    {
        
    }

    public static function caculate($symbol, $interval, $N = 14, &$startObjectIndex, &$restObjectIndex = null, $clone=false)
    {

        $index = 'rsi_' . $interval . '_' . $N;

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
            'LAB_CANDLE_SIGNAL' => "lab_candle_" . $interval . "_signal",
            'LAB_CANDLE_HISTOGRAM' => "lab_candle_" . $interval . "_histogram",
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
            'LAB_CANDLE_AVGU' => 'lab_candle_'.$interval.'_avgu'.$N,
            'LAB_CANDLE_AVGD' => 'lab_candle_'.$interval.'_avgd'.$N,
            'LAB_CANDLE_RSI' => 'lab_candle_'.$interval.'_rsi'.$N,
            'LAB_CANDLE_RSI_EMA9' => 'lab_candle_'.$interval.'_rsi_ema9',
            'LAB_CANDLE_RSI_EMA5' => 'lab_candle_'.$interval.'_rsi_ema5',
            'LAB_CANDLE_RSI_EMA4' => 'lab_candle_'.$interval.'_rsi_ema4',
            'LAB_CANDLE_RSI_WMA' => 'lab_candle_'.$interval.'_rsi_wma',

        ];

        if($clone){
            $model = Models::clone('Admin/Lab_candle_' . $interval);
        }else{
            $model = Models::get('Admin/Lab_candle_' . $interval);
        }

        if (!isset($startObjectIndex[$index]) || $startObjectIndex[$index] == null) {

            echo "Caculate start object for signal $index\n";

            $firstData = $model->read([[[$columnName['LAB_CANDLE_SYMBOL'], '=', $symbol], [$columnName['LAB_CANDLE_STARTPOINT'], '=', 1], [$columnName['LAB_CANDLE_AVGU'], '<>', 0]]], function ($db) use ($columnName) {
                $db->orderBy($columnName['LAB_CANDLE_CLOSE_TIME'], 'DESC')->limit(1);
            });

            if (!$firstData['result']) return $firstData;

            if (isset($firstData['data'][0])) {
                $startObjectIndex[$index] = $firstData['data'][0];
            }

            if (!isset($startObjectIndex[$index])) {

                $firstData = $model->read([[[$columnName['LAB_CANDLE_SYMBOL'], '=', $symbol], [$columnName['LAB_CANDLE_STARTPOINT'], '=', 1]]], function ($db) use ($columnName, $N) {
                    $db->orderBy($columnName['LAB_CANDLE_CLOSE_TIME'], 'ASC')->limit($N + 1);
                });

                $firstData = $firstData['data'];

                if (count($firstData) == $N + 1) {
                    $sumU = 0;
                    $sumD = 0;
                    foreach ($firstData as $key => $item) {
                       
                        if(isset($firstData[$key + 1])){
                            // $detal = doubleval($firstData[$key + 1]->{$columnName['LAB_CANDLE_CLOSE']}) - doubleval($firstData[$key + 1]->{$columnName['LAB_CANDLE_OPEN']});
                            $periodDelta = doubleval($firstData[$key + 1]->{$columnName['LAB_CANDLE_CLOSE']}) - doubleval($firstData[$key]->{$columnName['LAB_CANDLE_CLOSE']});
                            if($periodDelta > 0){
                                $sumU += $periodDelta;
                            }else if($periodDelta < 0){
                                $sumD -= $periodDelta;
                            }
                        }
                    }

                    $firstAvgU = $sumU/$N;
                    $firstAvgD = $sumD/$N;
                    $RS = $firstAvgU/$firstAvgD;
                    $firstRSI = 100 - 100/(1+$RS);

                    $startObjectIndex[$index] = $firstData[$N];

                    $model->edit([
                        DATA_KEY => [[[$columnName['LAB_CANDLE_ID'], '=', $startObjectIndex[$index]->{$columnName['LAB_CANDLE_ID']}]]],
                        DATA_EDITOR => [
                            $columnName['LAB_CANDLE_AVGU'] => $firstAvgU, 
                            $columnName['LAB_CANDLE_AVGD'] => $firstAvgD, 
                            $columnName['LAB_CANDLE_RSI'] => $firstRSI
                        ]
                    ]);

                    $startObjectIndex[$index]->{$columnName['LAB_CANDLE_AVGU']} = $firstAvgU;
                    $startObjectIndex[$index]->{$columnName['LAB_CANDLE_AVGD']} = $firstAvgD;
                    $startObjectIndex[$index]->{$columnName['LAB_CANDLE_RSI']} = $firstRSI;
                }
            }
        }

        if(!isset($startObjectIndex[$index])) return Reply::make(false, 'Can not get start object');

        $firstAvgU = $startObjectIndex[$index]->{$columnName['LAB_CANDLE_AVGU']};
        $firstAvgD = $startObjectIndex[$index]->{$columnName['LAB_CANDLE_AVGD']};
       
        $startPoint = $startObjectIndex[$index]->{$columnName['LAB_CANDLE_CLOSE_TIME']};

        if ($firstAvgU === null || $firstAvgD === null) return Reply::make(false, 'Can not caculate Fist AVG');

        if ($restObjectIndex == null) {

            echo "Caculate rest object for RSI $index\n";

            $periodAvgU = $firstAvgU;
            $periodAvgD = $firstAvgD;
            $periodClose = doubleval($startObjectIndex[$index]->{$columnName['LAB_CANDLE_CLOSE']});

            while(true){
                $restObjects = $model->read([[
                    [$columnName['LAB_CANDLE_SYMBOL'], '=', $symbol], 
                    [$columnName['LAB_CANDLE_CLOSE_TIME'], '>', $startPoint],
                    [$columnName['LAB_CANDLE_AVGU'], '=', null],
                    [$columnName['LAB_CANDLE_STARTPOINT'], '=', 1]
    
                ]], function ($db) use ($columnName) {
                    $db->orderBy($columnName['LAB_CANDLE_CLOSE_TIME'], 'ASC');
                    $db->limit(5000);
                });
                if (!$restObjects['result']) return $restObjects;
    
                $restObjects = $restObjects['data'];
                                
                foreach ($restObjects as $key => $restObject) {
                    $close = doubleval($restObject->{$columnName['LAB_CANDLE_CLOSE']});
                    $open = doubleval($restObject->{$columnName['LAB_CANDLE_OPEN']});
                    $Ut = 0;
                    $Dt = 0;
                    if($close > $periodClose){
                        $Ut = $close - $periodClose;
                    }else if($close < $periodClose){
                        $Dt = $periodClose - $close;
                    }
    
                    $avgU = 1/$N * $Ut + (1 - 1/$N) * $periodAvgU;
                    $avgD = 1/$N * $Dt + (1 - 1/$N) * $periodAvgD;
                    $RS = $avgU/$avgD;
                    $RSI = 100 - 100/(1+$RS);
    
                    $result = $model->edit([
                        DATA_KEY => [[[$columnName['LAB_CANDLE_ID'], '=', $restObject->{$columnName['LAB_CANDLE_ID']}]]],
                        DATA_EDITOR => [
                            $columnName['LAB_CANDLE_AVGU'] => $avgU, 
                            $columnName['LAB_CANDLE_AVGD'] => $avgD, 
                            $columnName['LAB_CANDLE_RSI'] => $RSI
                        ]
                    ]);
                    if (!$result['result']) return $result;
    
                    $restObject->{$columnName['LAB_CANDLE_AVGU']} = $avgU;
                    $restObject->{$columnName['LAB_CANDLE_AVGD']} = $avgD;
                    $restObject->{$columnName['LAB_CANDLE_RSI']} = $RSI;
    
                    $restObjects[$key] = $restObject;
    
                    if (isset($restObject->{$columnName['LAB_CANDLE_STARTPOINT']}) && $restObject->{$columnName['LAB_CANDLE_STARTPOINT']} == 1) {
                        $periodAvgU = $avgU;
                        $periodAvgD = $avgD;
                        $periodClose = $close;
                        $startObjectIndex[$index] = $restObject;
                        $startPoint = $startObjectIndex[$index]->{$columnName['LAB_CANDLE_CLOSE_TIME']};
                    }
                }

                if(count($restObjects) <= 5000) break;
            }

        } else {

            $close = doubleval($restObjectIndex->{$columnName['LAB_CANDLE_CLOSE']});
            $open = doubleval($restObjectIndex->{$columnName['LAB_CANDLE_OPEN']});
            $periodClose = doubleval($startObjectIndex[$index]->{$columnName['LAB_CANDLE_CLOSE']});
            $periodAvgU = doubleval($startObjectIndex[$index]->{$columnName['LAB_CANDLE_AVGU']});
            $periodAvgD = doubleval($startObjectIndex[$index]->{$columnName['LAB_CANDLE_AVGD']});

            $Ut = 0;
            $Dt = 0;
            if($close > $periodClose){
                $Ut = $close - $periodClose;
            }else if($close < $periodClose){
                $Dt = $periodClose - $close;
            }

            $avgU = 1/$N * $Ut + (1 - 1/$N) * $periodAvgU;
            $avgD = 1/$N * $Dt + (1 - 1/$N) * $periodAvgD;
            $RS = $avgU/$avgD;
            $RSI = 100 - 100/(1+$RS);
            
            $restObjectIndex->{$columnName['LAB_CANDLE_AVGU']} = $avgU;
            $restObjectIndex->{$columnName['LAB_CANDLE_AVGD']} = $avgD;
            $restObjectIndex->{$columnName['LAB_CANDLE_RSI']} = $RSI;

            if (isset($restObjectIndex->{$columnName['LAB_CANDLE_STARTPOINT']}) && $restObjectIndex->{$columnName['LAB_CANDLE_STARTPOINT']} == 1) {
                $startObjectIndex[$index] = $restObjectIndex;
            }
        }

        return Reply::make(true, 'success');
    }
}

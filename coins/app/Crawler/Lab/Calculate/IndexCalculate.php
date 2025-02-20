<?php

namespace App\Crawler\Lab\Calculate;

class IndexCalculate
{

    function __construct()
    {
    }

    private static $context = [];

    /**
     * Calculate for an array.
     */

    public static function calBlock(&$datas, $interval)
    {

        $historyData = [];
        foreach ($datas as $key => $data) {
            if (isset($datas[$key - 1])) {
                $periodData = $datas[$key - 1];
            } else {
                $periodData = null;
            }

            IndexCalculate::calIndex($periodData, $datas[$key], $interval, $historyData);
            if ($interval == '15m' || $interval == '1h' || $interval == '4h' || $interval == '1d' || $interval == '1w') {
                IndexCalculate::calRsiWma($historyData, $datas[$key], $interval, 45);
            }

            $historyData[] = $datas[$key];
        }
    }

    public static function calIndex(&$periodData, &$data, $interval, $historyData)
    {

        foreach ([5, 9, 12, 13, 26] as $N) {
            IndexCalculate::calEma($periodData, $data, $interval, $N);
        }

        IndexCalculate::calMacd($data, $interval);

        foreach ([9] as $N) {
            IndexCalculate::calHistogram($periodData, $data, $interval, $N);
        }

        if ($interval == '15m' || $interval == '1h' || $interval == '4h' || $interval == '1d' || $interval == '1w') {
            foreach ([14] as $N) {
                IndexCalculate::calRsi($periodData, $data, $interval, $N, $historyData);
            }
            foreach ([9] as $N) {
                IndexCalculate::calRsiEma($periodData, $data, $interval, $N);
            }
        }
    }

    public static function calEma($periodData, &$data, $interval, $N)
    {
        $K = 2 / ($N + 1);
        $closeName = "lab_candle_" . $interval . "_close";
        $columnName = "lab_candle_" . $interval . "_ema" . $N;
        if ($periodData == null) {
            $data[$columnName] = $data[$closeName];
            return;
        };
        if (!isset($periodData[$columnName]) || $periodData[$columnName] == '' || $periodData[$columnName] == 0) {
            $data[$columnName] = $data[$closeName];
            return;
        }

        $periodEma = doubleval($periodData[$columnName]);
        $closePrice = doubleval($data[$closeName]);

        $ema = $periodEma * (1 - $K) + $closePrice * $K;
        $data[$columnName] = $ema;
    }

    public static function calMacd(&$data, $interval)
    {

        $ema5ColName = "lab_candle_" . $interval . "_ema" . 5;
        $ema13ColName = "lab_candle_" . $interval . "_ema" . 13;
        $ema26ColName = "lab_candle_" . $interval . "_ema" . 26;
        $ema12ColName = "lab_candle_" . $interval . "_ema" . 12;
        $macdColName = "lab_candle_" . $interval . "_macd";

        if ($interval == '15m') {
            $macd = doubleval($data[$ema5ColName]) - doubleval($data[$ema13ColName]);
        } else {
            $macd = doubleval($data[$ema12ColName]) - doubleval($data[$ema26ColName]);
        }
        $data[$macdColName] = $macd;
    }

    public static function calHistogram($periodData, &$data, $interval, $N)
    {
        $signalColName = ($N == 9 ? "lab_candle_" . $interval . "_signal" : "lab_candle_" . $interval . "_signal" . $N);
        $histoColName = ($N == 9 ? "lab_candle_" . $interval . "_histogram" :  "lab_candle_" . $interval . "_histogram" . $N);
        $macdColName = "lab_candle_" . $interval . "_macd";
        $K = 2 / ($N + 1);

        if ($periodData == null) {
            $signal = $data[$macdColName];
        } else if (!isset($periodData[$signalColName]) || $periodData[$signalColName] == '' || $periodData[$signalColName] == 0) {
            $signal = $data[$macdColName];
        } else {
            $signal = doubleval($periodData[$signalColName]) * (1 - $K) + doubleval($data[$macdColName]) * $K;
        }

        $gram = doubleval($data[$macdColName]) - $signal;

        $data[$signalColName] = $signal;
        $data[$histoColName] = $gram;
    }

    /**
     * @param Array historyData: data not contain the lastdata
     * @param Array data: data that you have to calculate
     */
    public static function calRsi($periodData, &$data, $interval, $N, $historyData)
    {

        $avguColName = 'lab_candle_' . $interval . '_avgu' . $N;
        $avgdColName = 'lab_candle_' . $interval . '_avgd' . $N;
        $rsiColName = 'lab_candle_' . $interval . '_rsi' . $N;
        $closeName = "lab_candle_" . $interval . "_close";

        if ($periodData == null || $periodData[$rsiColName] == null) {
            $periodClose = 0;
            $periodAvgU = 0;
            $periodAvgD = 0;
            $Ut = 0;
            $Dt = 0;
            $historyData[] = $data;

            $len = count($historyData);
            if ($len <= $N) {
                $data[$avguColName] = null;
                $data[$avgdColName] = null;
                $data[$rsiColName] = null;
                return;
            }
            
            $totalAvgU = 0;
            $totalAvgD = 0;
            $countU = 0;
            $countD = 0;
           
            for ($key = $len-1; $key >= $len-$N; $key--) {
                if ($key == 0) continue;
                $candle = $historyData[$key];
                $tempClosePrice = doubleval($candle[$closeName]);
                $tempPeriodPrice = doubleval($historyData[$key - 1][$closeName]);

                if ($tempClosePrice > $tempPeriodPrice) {
                    $totalAvgU += $tempClosePrice - $tempPeriodPrice;
                    $countU++;
                } else if ($tempClosePrice < $tempPeriodPrice) {
                    $totalAvgD += $tempPeriodPrice - $tempClosePrice;
                    $countD++;
                }
                
            }

            $avgU = $totalAvgU / $N;
            $avgD = $totalAvgD / $N;
            
        } else {
            $periodAvgU = isset($periodData[$avguColName]) ? doubleval($periodData[$avguColName]) : 0;
            $periodAvgD = isset($periodData[$avgdColName]) ? doubleval($periodData[$avgdColName]) : 0;
        
            $close = doubleval($data[$closeName]);
            $periodClose = doubleval($periodData[$closeName]);
            $Ut = 0;
            $Dt = 0;

            if ($close > $periodClose) {
                $Ut = $close - $periodClose;
            } else if ($close < $periodClose) {
                $Dt = $periodClose - $close;
            }

            $avgU = 1 / $N * $Ut + (1 - 1 / $N) * $periodAvgU;
            $avgD = 1 / $N * $Dt + (1 - 1 / $N) * $periodAvgD;
        }

        if ($avgD != 0) {
            $RS = $avgU / $avgD;
            $RSI = 100 - 100 / (1 + $RS);
        } else {
            $RSI = 100;
        }

        $data[$avguColName] = $avgU;
        $data[$avgdColName] = $avgD;
        $data[$rsiColName] = $RSI;
    }


    public static function calRsiEma($periodData, &$data, $interval, $N)
    {
        $K = 2 / ($N + 1);
        $rsiColName = "lab_candle_" . $interval . "_rsi14";
        $rsiEmaColName = "lab_candle_" . $interval . "_rsi_ema" . $N;
        if ($periodData == null) {
            $data[$rsiEmaColName] = $data[$rsiColName];
            return;
        };
        if (!isset($periodData[$rsiEmaColName]) || $periodData[$rsiEmaColName] == '' || $periodData[$rsiEmaColName] == 0) {
            $data[$rsiEmaColName] = $data[$rsiColName];
            return;
        }

        $periodEma = doubleval($periodData[$rsiEmaColName]);
        $rsi = doubleval($data[$rsiColName]);

        $ema = $periodEma * (1 - $K) + $rsi * $K;
        $data[$rsiEmaColName] = $ema;
    }

    /**
     * @param Array historyData: data not contain the lastdata
     * @param Array data: data that you have to calculate
     */
    public static function calRsiWma($historyData, &$data, $interval, $N)
    {

        $rsiColName = "lab_candle_" . $interval . "_rsi14";
        $rsiWmaColName = "lab_candle_" . $interval . "_rsi_wma";
        $symbolColName = "lab_candle_" . $interval . "_symbol";

        // if($data[$symbolColName] != 'BTCUSDT'){
        //     $data[$rsiWmaColName] = null;
        //     return;
        // }

        if (!isset($data[$rsiColName])) {
            $data[$rsiWmaColName] = null;
            return;
        }

        $historyData[] = $data;
        $len = count($historyData);
       
        if ($len < $N || $historyData[$len-$N][$rsiColName] == null) {
            $data[$rsiWmaColName] = null;
            return;
        }

        $wmaUpper = 0;
        $n = $N;
        for ($i = $len - 1; $i >= ($len - $N); $i--) {
            $wmaUpper += doubleval($historyData[$i][$rsiColName]) * $n;
            $n--;
        }
        $wma = $wmaUpper / ($N * ($N + 1) / 2);
        $data[$rsiWmaColName] = $wma;
    }
}

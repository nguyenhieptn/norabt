<?php

namespace App\Crawler\Caculator;

use App\Helpers\DB\Models;
use App\Helpers\Request\Query;
use App\Helpers\Request\Reply;

class RsiEmaRealtime
{

    function __construct()
    {
    }

    public static function caculate($symbol, $interval, $N, &$startObjectIndex, &$restPointIndex = null, $setStartPoint = false, $clone = false)
    {
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
            'CANDLE_STARTPOINT' => "candle_" . $interval . "_startpoint",
            'CANDLE_RSI14' => 'candle_' . $interval . '_rsi14',
            'CANDLE_RSI_EMA' => 'candle_' . $interval . '_rsi_ema' . $N,
            'CANDLE_RSI_EMA9' => 'candle_' . $interval . '_rsi_ema9',
            'CANDLE_RSI_EMA5' => 'candle_' . $interval . '_rsi_ema5',
            'CANDLE_RSI_EMA4' => 'candle_' . $interval . '_rsi_ema4',
        ];

        if ($clone) {
            $model = Models::clone('Admin/Candle_' . $interval);
        } else {
            $model = Models::get('Admin/Candle_' . $interval);
        }

        $index = "rsiema_" . $interval . "_" . $N;

        if (!isset($startObjectIndex[$index]) || $startObjectIndex[$index] == null) {

            echo "Caculate start object for $index\n";

            $firstEmas = $model->read([[[$columnName['CANDLE_SYMBOL'], '=', $symbol], [$columnName['CANDLE_RSI_EMA'], '>', 0]]], function ($db) use ($N, $columnName) {
                $db->orderBy($columnName['CANDLE_CLOSE_TIME'], 'DESC')->limit(1);
            });

            if (!$firstEmas['result']) return $firstEmas;

            if (isset($firstEmas['data'][0])) {
                $startObjectIndex[$index] = $firstEmas['data'][0];
            }

            if (!isset($startObjectIndex[$index])) {

                $firstEmas = $model->read([[[$columnName['CANDLE_SYMBOL'], '=', $symbol], [$columnName['CANDLE_RSI14'], '>', 0]]], function ($db) use ($N, $columnName) {
                    $db->orderBy($columnName['CANDLE_CLOSE_TIME'], 'ASC')->limit($N);
                });

                $firstEmas = $firstEmas['data'];

                if (count($firstEmas) == $N) {
                    $avg = 0;
                    foreach ($firstEmas as $item) {
                        $avg += (float)$item->{$columnName['CANDLE_RSI14']} / $N;
                    }
                    $firstEma = $avg;

                    $startObjectIndex[$index] = $firstEmas[$N - 1];

                    $model->edit([
                        DATA_KEY => [[[$columnName['CANDLE_ID'], '=', $startObjectIndex[$index]->{$columnName['CANDLE_ID']}]]],
                        DATA_EDITOR => [$columnName['CANDLE_RSI_EMA'] => $firstEma]
                    ]);

                    $startObjectIndex[$index]->{$columnName['CANDLE_RSI_EMA']} = $firstEma;
                }
            }
        }

        if (!isset($startObjectIndex[$index])) return Reply::make(false, 'Can not get start object');

        $firstEma = $startObjectIndex[$index]->{$columnName['CANDLE_RSI_EMA']};
        $startPoint = $startObjectIndex[$index]->{$columnName['CANDLE_CLOSE_TIME']};

        if (!$firstEma > 0) return Reply::make(false, 'Can not caculate EMA');

        $K = 2 / ($N + 1);

        if ($restPointIndex == null) {

            $periodEma = $firstEma;

            $condition = [
                [$columnName['CANDLE_SYMBOL'], '=', $symbol],
                [$columnName['CANDLE_CLOSE_TIME'], '>', $startPoint],
                [$columnName['CANDLE_RSI_EMA'], '=', null],
            ];

            $restPoints = $model->read([$condition], function ($db) use ($columnName) {
                $db->orderBy($columnName['CANDLE_CLOSE_TIME'], 'ASC');
            });

            if (!$restPoints['result']) return $restPoints;

            $restPoints = $restPoints['data'];

            $ema = null;

            foreach ($restPoints as $restPoint) {
                $ema = $periodEma * (1 - $K) + $restPoint->{$columnName['CANDLE_RSI14']} * $K;

                $result = $model->edit([
                    DATA_KEY => [[[$columnName['CANDLE_ID'], '=', $restPoint->{$columnName['CANDLE_ID']}]]],
                    DATA_EDITOR => [$columnName['CANDLE_RSI_EMA'] => $ema]
                ]);
                if (!$result['result']) return $result;
                $restPoint->{$columnName['CANDLE_RSI_EMA']} = $ema;
                $periodEma = $ema;
            }

            if (count($restPoints) >= 2) {
                $startObjectIndex[$index] = $restPoints[count($restPoints) - 2];
            }
        } else {

            $periodEma = $firstEma;

            $ema = $periodEma * (1 - $K) + $restPointIndex->{$columnName['CANDLE_RSI14']} * $K;

            $restPointIndex->{$columnName['CANDLE_RSI_EMA']} = $ema;

            if ($setStartPoint) {
                $startObjectIndex[$index] = $restPointIndex;
            }
        }

        return Reply::make(true, 'success');
    }
}

<?php

namespace App\Crawler\History;

use App\Crawler\Caculator\Ema;
use App\Helpers\DB\Models;
use App\Helpers\Request\Query;
use App\Helpers\Request\Reply;

class Candle
{

    function __construct()
    {
    }

    public static function craw($symbol, $interval, $limit=1000, $reset=true)
    {
        $datas = Query::make("https://fapi.binance.com/fapi/v1/klines?symbol=$symbol&interval=$interval&limit=$limit", 'GET', null, ['dataType' => 'json']);


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
            'CANDLE_MACD' => "candle_".$interval."_macd",
            'CANDLE_SIGNAL' => "candle_".$interval."_signal",
            'CANDLE_HISTOGRAM' => "candle_".$interval."_histogram",
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

        ];


        if ($datas) {

            $model = Models::get('Admin/Candle_' . $interval);

            $lastData = $model->read([[[$columnName['CANDLE_SYMBOL'], '=', $symbol]]], function ($db) use ($columnName) {
                $db->orderBy($columnName['CANDLE_CLOSE_TIME'], 'DESC')->limit(1);
            });
            $lastCloseTime = 0;
            if ($lastData['result'] && isset($lastData['data'][0])) {
                $lastCloseTime = $lastData['data'][0]->{$columnName['CANDLE_CLOSE_TIME']};
            }

            $addDatas = [];

            foreach ($datas as $data) {

                $editData = [
                    $columnName['CANDLE_SYMBOL'] => $symbol,
                    $columnName['CANDLE_OPEN_TIME'] => get($data[0], ''),
                    $columnName['CANDLE_OPEN'] => get($data[1], ''),
                    $columnName['CANDLE_HIGH'] => get($data[2], ''),
                    $columnName['CANDLE_LOW'] => get($data[3], ''),
                    $columnName['CANDLE_CLOSE'] => get($data[4], ''),
                    $columnName['CANDLE_VOLUME'] => get($data[5], ''),
                    $columnName['CANDLE_CLOSE_TIME'] => get($data[6], ''),
                    $columnName['CANDLE_TRADES'] => get($data[8], ''),
                ];

                if($reset){
                    $editData = array_merge($editData, [
                        $columnName['CANDLE_EMA5'] => null,
                        $columnName['CANDLE_EMA9'] => null,
                        $columnName['CANDLE_EMA12'] => null,
                        $columnName['CANDLE_EMA13'] => null,
                        $columnName['CANDLE_EMA26'] => null,
                        $columnName['CANDLE_MACD'] => null,
                        $columnName['CANDLE_SIGNAL'] => null,
                        $columnName['CANDLE_HISTOGRAM'] => null,
                        $columnName['CANDLE_SIGNAL7'] => null,
                        $columnName['CANDLE_HISTOGRAM7'] => null,
                        $columnName['CANDLE_SIGNAL4'] => null,
                        $columnName['CANDLE_HISTOGRAM4'] => null,
                        $columnName['CANDLE_SIGNAL2'] => null,
                        $columnName['CANDLE_HISTOGRAM2'] => null,
                        $columnName['CANDLE_SIGNAL3'] => null,
                        $columnName['CANDLE_HISTOGRAM3'] => null,
                        $columnName['CANDLE_SIGNAL5'] => null,
                        $columnName['CANDLE_HISTOGRAM5'] => null,
                        $columnName['CANDLE_SIGNAL6'] => null,
                        $columnName['CANDLE_HISTOGRAM6'] => null,
                    ]);
                }

                if ((int)($editData[$columnName['CANDLE_CLOSE_TIME']]) <= (int)$lastCloseTime) {
                    $result = $model->edit([
                        DATA_KEY => [[[$columnName['CANDLE_CLOSE_TIME'], '=', $editData[$columnName['CANDLE_CLOSE_TIME']]], [$columnName['CANDLE_SYMBOL'], '=', $symbol]]],
                        DATA_EDITOR => $editData
                    ]);
                    if (!$result['result']) return $result;
                } else {
                    $addDatas[] = $editData;
                }
            }

            if (count($addDatas) > 0) {
                $result = $model->add($addDatas);
                if (!$result['result']) return $result;
            }

            return Reply::make(true, 'success');

        }



        return Reply::make(false, $datas);
    }
}

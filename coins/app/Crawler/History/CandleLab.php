<?php

namespace App\Crawler\History;

use App\Crawler\Caculator\Ema;
use App\Helpers\DB\Models;
use App\Helpers\Request\Query;
use App\Helpers\Request\Reply;

class CandleLab
{

    function __construct()
    {
    }

    public static function craw($symbol, $interval, $limit = 500, $reset = true)
    {
        $datas = Query::make("https://fapi.binance.com/fapi/v1/klines?symbol=$symbol&interval=$interval&limit=$limit", 'GET', null, ['dataType' => 'json']);


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
            'LAB_CANDLE_STARTPOINT' => "lab_candle_" . $interval . "_startpoint",
            'LAB_CANDLE_SIGNAL7' => 'lab_candle_' . $interval . '_signal7',
            'LAB_CANDLE_HISTOGRAM7' => 'lab_candle_' . $interval . '_histogram7',
            'LAB_CANDLE_SIGNAL4' => 'lab_candle_' . $interval . '_signal4',
            'LAB_CANDLE_HISTOGRAM4' => 'lab_candle_' . $interval . '_histogram4',
            'LAB_CANDLE_SIGNAL2' => 'lab_candle_' . $interval . '_signal2',
            'LAB_CANDLE_HISTOGRAM2' => 'lab_candle_' . $interval . '_histogram2',
            'LAB_CANDLE_SIGNAL3' => 'lab_candle_' . $interval . '_signal3',
            'LAB_CANDLE_HISTOGRAM3' => 'lab_candle_' . $interval . '_histogram3',
            'LAB_CANDLE_SIGNAL5' => 'lab_candle_' . $interval . '_signal5',
            'LAB_CANDLE_HISTOGRAM5' => 'lab_candle_' . $interval . '_histogram5',
            'LAB_CANDLE_SIGNAL6' => 'lab_candle_' . $interval . '_signal6',
            'LAB_CANDLE_HISTOGRAM6' => 'lab_candle_' . $interval . '_histogram6',

        ];


        if ($datas) {

            $model = Models::get('Admin/Lab_candle_' . $interval);

            $leng = count($datas);


            $addDatas = [];

            foreach ($datas as $key => $data) {

                if ($key == $leng - 1) {
                    $editData = [
                        $columnName['LAB_CANDLE_SYMBOL'] => $symbol,
                        $columnName['LAB_CANDLE_TIME'] => $data[0],
                        $columnName['LAB_CANDLE_OPEN_TIME'] => get($data[0], ''),
                        $columnName['LAB_CANDLE_OPEN'] => get($data[1], ''),
                        $columnName['LAB_CANDLE_HIGH'] => get($data[2], ''),
                        $columnName['LAB_CANDLE_LOW'] => get($data[3], ''),
                        $columnName['LAB_CANDLE_CLOSE'] => get($data[4], ''),
                        $columnName['LAB_CANDLE_VOLUME'] => get($data[5], ''),
                        $columnName['LAB_CANDLE_CLOSE_TIME'] => get($data[6], ''),
                        $columnName['LAB_CANDLE_TRADES'] => get($data[8], ''),
                        $columnName['LAB_CANDLE_STARTPOINT'] => 0,
                    ];
                } else {
                    $editData = [
                        $columnName['LAB_CANDLE_SYMBOL'] => $symbol,
                        $columnName['LAB_CANDLE_TIME'] => $data[0],
                        $columnName['LAB_CANDLE_OPEN_TIME'] => get($data[0], ''),
                        $columnName['LAB_CANDLE_OPEN'] => get($data[1], ''),
                        $columnName['LAB_CANDLE_HIGH'] => get($data[2], ''),
                        $columnName['LAB_CANDLE_LOW'] => get($data[3], ''),
                        $columnName['LAB_CANDLE_CLOSE'] => get($data[4], ''),
                        $columnName['LAB_CANDLE_VOLUME'] => get($data[5], ''),
                        $columnName['LAB_CANDLE_CLOSE_TIME'] => get($data[6], ''),
                        $columnName['LAB_CANDLE_TRADES'] => get($data[8], ''),
                        $columnName['LAB_CANDLE_STARTPOINT'] => 1,
                    ];
                }

                if ($reset) {
                    $editData = array_merge($editData, [
                        $columnName['LAB_CANDLE_EMA5'] => null,
                        $columnName['LAB_CANDLE_EMA9'] => null,
                        $columnName['LAB_CANDLE_EMA12'] => null,
                        $columnName['LAB_CANDLE_EMA13'] => null,
                        $columnName['LAB_CANDLE_EMA26'] => null,
                        $columnName['LAB_CANDLE_MACD'] => null,
                        $columnName['LAB_CANDLE_SIGNAL'] => null,
                        $columnName['LAB_CANDLE_HISTOGRAM'] => null,
                        $columnName['LAB_CANDLE_SIGNAL7'] => null,
                        $columnName['LAB_CANDLE_HISTOGRAM7'] => null,
                        $columnName['LAB_CANDLE_SIGNAL4'] => null,
                        $columnName['LAB_CANDLE_HISTOGRAM4'] => null,
                        $columnName['LAB_CANDLE_SIGNAL2'] => null,
                        $columnName['LAB_CANDLE_HISTOGRAM2'] => null,
                        $columnName['LAB_CANDLE_SIGNAL3'] => null,
                        $columnName['LAB_CANDLE_HISTOGRAM3'] => null,
                        $columnName['LAB_CANDLE_SIGNAL5'] => null,
                        $columnName['LAB_CANDLE_HISTOGRAM5'] => null,
                        $columnName['LAB_CANDLE_SIGNAL6'] => null,
                        $columnName['LAB_CANDLE_HISTOGRAM6'] => null,
                    ]);
                }

                if (!$model->is_exist([[
                    [$columnName['LAB_CANDLE_CLOSE_TIME'], '=', $editData[$columnName['LAB_CANDLE_CLOSE_TIME']]],
                    [$columnName['LAB_CANDLE_SYMBOL'], '=', $symbol],
                    [$columnName['LAB_CANDLE_STARTPOINT'], '=', 1]
                ]])) {
                    $addDatas[] = $editData;
                } else {
                    $result = $model->edit([
                        DATA_KEY => [[
                            [$columnName['LAB_CANDLE_CLOSE_TIME'], '=', $editData[$columnName['LAB_CANDLE_CLOSE_TIME']]],
                            [$columnName['LAB_CANDLE_SYMBOL'], '=', $symbol],
                            [$columnName['LAB_CANDLE_STARTPOINT'], '=', 1]
                        ]],
                        DATA_EDITOR => $editData
                    ]);
                    if (!$result['result']) return $result;
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

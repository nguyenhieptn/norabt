<?php

namespace App\Crawler\Lab\History;

use App\Crawler\Caculator\Ema;
use App\Crawler\Lab\Calculate\IndexCalculate;
use App\Helpers\DB\Models;
use App\Helpers\Request\Query;
use App\Helpers\Request\Reply;

class CandleHistory
{

    function __construct()
    {
    }

    public static function craw($symbol, $interval, $limit=1000, $reset=true)
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
            'LAB_CANDLE_STARTPOINT' => "lab_candle_" . $interval . "_startpoint",
            

        ];


        if ($datas) {


            $addDatas = [];

            foreach ($datas as $data) {

                $editData = [
                    $columnName['LAB_CANDLE_SYMBOL'] => $symbol,
                    $columnName['LAB_CANDLE_TIME'] => get($data[6], ''),
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

                $addDatas[] = $editData;

            }

            $addDatas[count($addDatas)-1][$columnName['LAB_CANDLE_STARTPOINT']] = 0;
            
            IndexCalculate::calBlock($addDatas, $interval);

            return Reply::make(true, 'success', $addDatas);

        }

        return Reply::make(false, $datas);
    }
}

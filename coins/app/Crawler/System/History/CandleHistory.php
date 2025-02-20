<?php

namespace App\Crawler\System\History;

use App\Crawler\Caculator\Ema;
use App\Crawler\System\Calculate\IndexCalculate;
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
            

        ];

        if ($datas) {


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

                $addDatas[] = $editData;

            }
            
            IndexCalculate::calBlock($addDatas, $interval);
            return Reply::make(true, 'success', $addDatas);

        }

        return Reply::make(false, $datas);
    }
}

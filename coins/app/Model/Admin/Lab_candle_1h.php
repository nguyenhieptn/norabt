<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Lab_candle_1h extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            LAB_CANDLE_1H_ID => [
                PROP_NAME => LAB_CANDLE_1H_ID,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_TIME => [
                PROP_NAME => LAB_CANDLE_1H_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_SYMBOL => [
                PROP_NAME => LAB_CANDLE_1H_SYMBOL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_OPEN_TIME => [
                PROP_NAME => LAB_CANDLE_1H_OPEN_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_CLOSE_TIME => [
                PROP_NAME => LAB_CANDLE_1H_CLOSE_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_OPEN => [
                PROP_NAME => LAB_CANDLE_1H_OPEN,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_CLOSE => [
                PROP_NAME => LAB_CANDLE_1H_CLOSE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_HIGH => [
                PROP_NAME => LAB_CANDLE_1H_HIGH,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_LOW => [
                PROP_NAME => LAB_CANDLE_1H_LOW,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_TRADES => [
                PROP_NAME => LAB_CANDLE_1H_TRADES,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_VOLUME => [
                PROP_NAME => LAB_CANDLE_1H_VOLUME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_EMA5 => [
                PROP_NAME => LAB_CANDLE_1H_EMA5,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_EMA9 => [
                PROP_NAME => LAB_CANDLE_1H_EMA9,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_EMA12 => [
                PROP_NAME => LAB_CANDLE_1H_EMA12,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_EMA13 => [
                PROP_NAME => LAB_CANDLE_1H_EMA13,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_EMA26 => [
                PROP_NAME => LAB_CANDLE_1H_EMA26,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_MACD => [
                PROP_NAME => LAB_CANDLE_1H_MACD,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_SIGNAL => [
                PROP_NAME => LAB_CANDLE_1H_SIGNAL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_HISTOGRAM => [
                PROP_NAME => LAB_CANDLE_1H_HISTOGRAM,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_SIGNAL7 => [
                PROP_NAME => LAB_CANDLE_1H_SIGNAL7,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_HISTOGRAM7 => [
                PROP_NAME => LAB_CANDLE_1H_HISTOGRAM7,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_SIGNAL4 => [
                PROP_NAME => LAB_CANDLE_1H_SIGNAL4,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_HISTOGRAM4 => [
                PROP_NAME => LAB_CANDLE_1H_HISTOGRAM4,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_SIGNAL5 => [
                PROP_NAME => LAB_CANDLE_1H_SIGNAL5,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_HISTOGRAM5 => [
                PROP_NAME => LAB_CANDLE_1H_HISTOGRAM5,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_SIGNAL6 => [
                PROP_NAME => LAB_CANDLE_1H_SIGNAL6,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_HISTOGRAM6 => [
                PROP_NAME => LAB_CANDLE_1H_HISTOGRAM6,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_SIGNAL2 => [
                PROP_NAME => LAB_CANDLE_1H_SIGNAL2,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_HISTOGRAM2 => [
                PROP_NAME => LAB_CANDLE_1H_HISTOGRAM2,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_SIGNAL3 => [
                PROP_NAME => LAB_CANDLE_1H_SIGNAL3,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_HISTOGRAM3 => [
                PROP_NAME => LAB_CANDLE_1H_HISTOGRAM3,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_STARTPOINT => [
                PROP_NAME => LAB_CANDLE_1H_STARTPOINT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_AVGU14 => [
                PROP_NAME => LAB_CANDLE_1H_AVGU14,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_AVGD14 => [
                PROP_NAME => LAB_CANDLE_1H_AVGD14,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_RSI14 => [
                PROP_NAME => LAB_CANDLE_1H_RSI14,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_RSI_EMA9 => [
                PROP_NAME => LAB_CANDLE_1H_RSI_EMA9,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_RSI_EMA5 => [
                PROP_NAME => LAB_CANDLE_1H_RSI_EMA5,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_RSI_EMA4 => [
                PROP_NAME => LAB_CANDLE_1H_RSI_EMA4,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1H_RSI_WMA => [
                PROP_NAME => LAB_CANDLE_1H_RSI_WMA,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],

        );

        $this->query_builder = DB::connection('coin_crawler')->table(LAB_CANDLE_1H_TABLE);
        $this->id = LAB_CANDLE_1H_ID;
        $this->name = LAB_CANDLE_1H_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }

    public function resetConnection()
    {
        DB::connection('lab')->reconnect();
    }
}

<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Lab_candle_1w extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            LAB_CANDLE_1W_ID => [
                PROP_NAME => LAB_CANDLE_1W_ID,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_TIME => [
                PROP_NAME => LAB_CANDLE_1W_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_SYMBOL => [
                PROP_NAME => LAB_CANDLE_1W_SYMBOL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_OPEN_TIME => [
                PROP_NAME => LAB_CANDLE_1W_OPEN_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_CLOSE_TIME => [
                PROP_NAME => LAB_CANDLE_1W_CLOSE_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_OPEN => [
                PROP_NAME => LAB_CANDLE_1W_OPEN,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_CLOSE => [
                PROP_NAME => LAB_CANDLE_1W_CLOSE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_HIGH => [
                PROP_NAME => LAB_CANDLE_1W_HIGH,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_LOW => [
                PROP_NAME => LAB_CANDLE_1W_LOW,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_TRADES => [
                PROP_NAME => LAB_CANDLE_1W_TRADES,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_VOLUME => [
                PROP_NAME => LAB_CANDLE_1W_VOLUME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_EMA5 => [
                PROP_NAME => LAB_CANDLE_1W_EMA5,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_EMA9 => [
                PROP_NAME => LAB_CANDLE_1W_EMA9,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_EMA12 => [
                PROP_NAME => LAB_CANDLE_1W_EMA12,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_EMA13 => [
                PROP_NAME => LAB_CANDLE_1W_EMA13,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_EMA26 => [
                PROP_NAME => LAB_CANDLE_1W_EMA26,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_MACD => [
                PROP_NAME => LAB_CANDLE_1W_MACD,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_SIGNAL => [
                PROP_NAME => LAB_CANDLE_1W_SIGNAL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_HISTOGRAM => [
                PROP_NAME => LAB_CANDLE_1W_HISTOGRAM,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_SIGNAL7 => [
                PROP_NAME => LAB_CANDLE_1W_SIGNAL7,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_HISTOGRAM7 => [
                PROP_NAME => LAB_CANDLE_1W_HISTOGRAM7,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_SIGNAL4 => [
                PROP_NAME => LAB_CANDLE_1W_SIGNAL4,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_HISTOGRAM4 => [
                PROP_NAME => LAB_CANDLE_1W_HISTOGRAM4,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_SIGNAL5 => [
                PROP_NAME => LAB_CANDLE_1W_SIGNAL5,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_HISTOGRAM5 => [
                PROP_NAME => LAB_CANDLE_1W_HISTOGRAM5,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_SIGNAL6 => [
                PROP_NAME => LAB_CANDLE_1W_SIGNAL6,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_HISTOGRAM6 => [
                PROP_NAME => LAB_CANDLE_1W_HISTOGRAM6,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_SIGNAL2 => [
                PROP_NAME => LAB_CANDLE_1W_SIGNAL2,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_HISTOGRAM2 => [
                PROP_NAME => LAB_CANDLE_1W_HISTOGRAM2,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_SIGNAL3 => [
                PROP_NAME => LAB_CANDLE_1W_SIGNAL3,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_HISTOGRAM3 => [
                PROP_NAME => LAB_CANDLE_1W_HISTOGRAM3,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_STARTPOINT => [
                PROP_NAME => LAB_CANDLE_1W_STARTPOINT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_AVGU14 => [
                PROP_NAME => LAB_CANDLE_1W_AVGU14,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_AVGD14 => [
                PROP_NAME => LAB_CANDLE_1W_AVGD14,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_RSI14 => [
                PROP_NAME => LAB_CANDLE_1W_RSI14,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_RSI_EMA9 => [
                PROP_NAME => LAB_CANDLE_1W_RSI_EMA9,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_RSI_EMA5 => [
                PROP_NAME => LAB_CANDLE_1W_RSI_EMA5,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_RSI_EMA4 => [
                PROP_NAME => LAB_CANDLE_1W_RSI_EMA4,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CANDLE_1W_RSI_WMA => [
                PROP_NAME => LAB_CANDLE_1W_RSI_WMA,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],

        );

        $this->query_builder = DB::connection('coin_crawler')->table(LAB_CANDLE_1W_TABLE);
        $this->id = LAB_CANDLE_1W_ID;
        $this->name = LAB_CANDLE_1W_TABLE;

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

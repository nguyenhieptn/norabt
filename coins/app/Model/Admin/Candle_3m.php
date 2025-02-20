<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Candle_3m extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            CANDLE_3M_ID => [
                PROP_NAME => CANDLE_3M_ID,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_SYMBOL => [
                PROP_NAME => CANDLE_3M_SYMBOL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_OPEN_TIME => [
                PROP_NAME => CANDLE_3M_OPEN_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_CLOSE_TIME => [
                PROP_NAME => CANDLE_3M_CLOSE_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_OPEN => [
                PROP_NAME => CANDLE_3M_OPEN,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_CLOSE => [
                PROP_NAME => CANDLE_3M_CLOSE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_HIGH => [
                PROP_NAME => CANDLE_3M_HIGH,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_LOW => [
                PROP_NAME => CANDLE_3M_LOW,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_TRADES => [
                PROP_NAME => CANDLE_3M_TRADES,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_VOLUME => [
                PROP_NAME => CANDLE_3M_VOLUME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_EMA5 => [
                PROP_NAME => CANDLE_3M_EMA5,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_EMA9 => [
                PROP_NAME => CANDLE_3M_EMA9,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_EMA12 => [
                PROP_NAME => CANDLE_3M_EMA12,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_EMA13 => [
                PROP_NAME => CANDLE_3M_EMA13,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_EMA26 => [
                PROP_NAME => CANDLE_3M_EMA26,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_MACD => [
                PROP_NAME => CANDLE_3M_MACD,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_SIGNAL => [
                PROP_NAME => CANDLE_3M_SIGNAL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_HISTOGRAM => [
                PROP_NAME => CANDLE_3M_HISTOGRAM,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_SIGNAL7 => [
                PROP_NAME => CANDLE_3M_SIGNAL7,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_HISTOGRAM7 => [
                PROP_NAME => CANDLE_3M_HISTOGRAM7,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_SIGNAL4 => [
                PROP_NAME => CANDLE_3M_SIGNAL4,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_HISTOGRAM4 => [
                PROP_NAME => CANDLE_3M_HISTOGRAM4,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_SIGNAL2 => [
                PROP_NAME => CANDLE_3M_SIGNAL2,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_HISTOGRAM2 => [
                PROP_NAME => CANDLE_3M_HISTOGRAM2,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_SIGNAL3 => [
                PROP_NAME => CANDLE_3M_SIGNAL3,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_HISTOGRAM3 => [
                PROP_NAME => CANDLE_3M_HISTOGRAM3,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_SIGNAL5 => [
                PROP_NAME => CANDLE_3M_SIGNAL5,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_HISTOGRAM5 => [
                PROP_NAME => CANDLE_3M_HISTOGRAM5,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_SIGNAL6 => [
                PROP_NAME => CANDLE_3M_SIGNAL6,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_HISTOGRAM6 => [
                PROP_NAME => CANDLE_3M_HISTOGRAM6,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_AVGU14 => [
                PROP_NAME => CANDLE_3M_AVGU14,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_AVGD14 => [
                PROP_NAME => CANDLE_3M_AVGD14,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_RSI14 => [
                PROP_NAME => CANDLE_3M_RSI14,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_RSI_EMA9 => [
                PROP_NAME => CANDLE_3M_RSI_EMA9,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_RSI_EMA5 => [
                PROP_NAME => CANDLE_3M_RSI_EMA5,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_RSI_EMA4 => [
                PROP_NAME => CANDLE_3M_RSI_EMA4,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_RSI_WMA => [
                PROP_NAME => CANDLE_3M_RSI_WMA,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_3M_PRICE_WMA => [
                PROP_NAME => CANDLE_3M_PRICE_WMA,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],

        );

        $this->query_builder = DB::table(CANDLE_3M_TABLE);
        $this->id = CANDLE_3M_ID;
        $this->name = CANDLE_3M_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }

    public function resetConnection()
    {
        DB::reconnect();
    }
}

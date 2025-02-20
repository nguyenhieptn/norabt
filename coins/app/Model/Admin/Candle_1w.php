<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Candle_1w extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            CANDLE_1W_ID => [
                PROP_NAME => CANDLE_1W_ID,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_SYMBOL => [
                PROP_NAME => CANDLE_1W_SYMBOL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_OPEN_TIME => [
                PROP_NAME => CANDLE_1W_OPEN_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_CLOSE_TIME => [
                PROP_NAME => CANDLE_1W_CLOSE_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_OPEN => [
                PROP_NAME => CANDLE_1W_OPEN,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_CLOSE => [
                PROP_NAME => CANDLE_1W_CLOSE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_HIGH => [
                PROP_NAME => CANDLE_1W_HIGH,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_LOW => [
                PROP_NAME => CANDLE_1W_LOW,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_TRADES => [
                PROP_NAME => CANDLE_1W_TRADES,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_VOLUME => [
                PROP_NAME => CANDLE_1W_VOLUME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_EMA5 => [
                PROP_NAME => CANDLE_1W_EMA5,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_EMA9 => [
                PROP_NAME => CANDLE_1W_EMA9,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_EMA12 => [
                PROP_NAME => CANDLE_1W_EMA12,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_EMA13 => [
                PROP_NAME => CANDLE_1W_EMA13,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_EMA26 => [
                PROP_NAME => CANDLE_1W_EMA26,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_MACD => [
                PROP_NAME => CANDLE_1W_MACD,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_SIGNAL => [
                PROP_NAME => CANDLE_1W_SIGNAL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_HISTOGRAM => [
                PROP_NAME => CANDLE_1W_HISTOGRAM,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_SIGNAL7 => [
                PROP_NAME => CANDLE_1W_SIGNAL7,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_HISTOGRAM7 => [
                PROP_NAME => CANDLE_1W_HISTOGRAM7,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_SIGNAL4 => [
                PROP_NAME => CANDLE_1W_SIGNAL4,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_HISTOGRAM4 => [
                PROP_NAME => CANDLE_1W_HISTOGRAM4,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_SIGNAL2 => [
                PROP_NAME => CANDLE_1W_SIGNAL2,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_HISTOGRAM2 => [
                PROP_NAME => CANDLE_1W_HISTOGRAM2,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_SIGNAL3 => [
                PROP_NAME => CANDLE_1W_SIGNAL3,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_HISTOGRAM3 => [
                PROP_NAME => CANDLE_1W_HISTOGRAM3,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_SIGNAL5 => [
                PROP_NAME => CANDLE_1W_SIGNAL5,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_HISTOGRAM5 => [
                PROP_NAME => CANDLE_1W_HISTOGRAM5,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_SIGNAL6 => [
                PROP_NAME => CANDLE_1W_SIGNAL6,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_HISTOGRAM6 => [
                PROP_NAME => CANDLE_1W_HISTOGRAM6,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_AVGU14 => [
                PROP_NAME => CANDLE_1W_AVGU14,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_AVGD14 => [
                PROP_NAME => CANDLE_1W_AVGD14,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_RSI14 => [
                PROP_NAME => CANDLE_1W_RSI14,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_RSI_EMA9 => [
                PROP_NAME => CANDLE_1W_RSI_EMA9,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_RSI_EMA5 => [
                PROP_NAME => CANDLE_1W_RSI_EMA5,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_RSI_EMA4 => [
                PROP_NAME => CANDLE_1W_RSI_EMA4,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_RSI_WMA => [
                PROP_NAME => CANDLE_1W_RSI_WMA,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_PRICE_WMA => [
                PROP_NAME => CANDLE_1W_PRICE_WMA,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_PRICE_WMA45 => [
                PROP_NAME => CANDLE_1W_PRICE_WMA45,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_RSI_WMA45 => [
                PROP_NAME => CANDLE_1W_RSI_WMA45,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_RSI_EMA9 => [
                PROP_NAME => CANDLE_1W_RSI_EMA9,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_PRICE_EMA9 => [
                PROP_NAME => CANDLE_1W_PRICE_EMA9,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1W_NET_EMA9_WMA45 => [
                PROP_NAME => CANDLE_1W_NET_EMA9_WMA45,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],

        );

        $this->query_builder = DB::table(CANDLE_1W_TABLE);
        $this->id = CANDLE_1W_ID;
        $this->name = CANDLE_1W_TABLE;

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

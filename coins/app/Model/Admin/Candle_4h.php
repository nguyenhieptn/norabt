<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Candle_4h extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            CANDLE_4H_ID => [
                PROP_NAME => CANDLE_4H_ID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            CANDLE_4H_SYMBOL => [
                PROP_NAME => CANDLE_4H_SYMBOL,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLE_4H_OPEN_TIME => [
                PROP_NAME => CANDLE_4H_OPEN_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLE_4H_CLOSE_TIME => [
                PROP_NAME => CANDLE_4H_CLOSE_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLE_4H_OPEN => [
                PROP_NAME => CANDLE_4H_OPEN,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLE_4H_CLOSE => [
                PROP_NAME => CANDLE_4H_CLOSE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLE_4H_HIGH => [
                PROP_NAME => CANDLE_4H_HIGH,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLE_4H_LOW => [
                PROP_NAME => CANDLE_4H_LOW,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLE_4H_TRADES => [
                PROP_NAME => CANDLE_4H_TRADES,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLE_4H_VOLUME => [
                PROP_NAME => CANDLE_4H_VOLUME,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLE_4H_EMA5 => [
                PROP_NAME => CANDLE_4H_EMA5,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLE_4H_EMA9 => [
                PROP_NAME => CANDLE_4H_EMA9,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLE_4H_EMA12 => [
                PROP_NAME => CANDLE_4H_EMA12,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLE_4H_EMA13 => [
                PROP_NAME => CANDLE_4H_EMA13,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLE_4H_EMA26 => [
                PROP_NAME => CANDLE_4H_EMA26,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLE_4H_MACD => [
                PROP_NAME => CANDLE_4H_MACD,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLE_4H_SIGNAL => [
                PROP_NAME => CANDLE_4H_SIGNAL,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLE_4H_HISTOGRAM => [
                PROP_NAME => CANDLE_4H_HISTOGRAM,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLE_4H_SIGNAL7 => [
                PROP_NAME => CANDLE_4H_SIGNAL7,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLE_4H_HISTOGRAM7 => [
                PROP_NAME => CANDLE_4H_HISTOGRAM7,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLE_4H_SIGNAL4 => [
                PROP_NAME => CANDLE_4H_SIGNAL4,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLE_4H_HISTOGRAM4 => [
                PROP_NAME => CANDLE_4H_HISTOGRAM4,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLE_4H_SIGNAL5 => [
                PROP_NAME => CANDLE_4H_SIGNAL5,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLE_4H_HISTOGRAM5 => [
                PROP_NAME => CANDLE_4H_HISTOGRAM5,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLE_4H_SIGNAL6 => [
                PROP_NAME => CANDLE_4H_SIGNAL6,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLE_4H_HISTOGRAM6 => [
                PROP_NAME => CANDLE_4H_HISTOGRAM6,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLE_4H_SIGNAL2 => [
                PROP_NAME => CANDLE_4H_SIGNAL2,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLE_4H_HISTOGRAM2 => [
                PROP_NAME => CANDLE_4H_HISTOGRAM2,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLE_4H_SIGNAL3 => [
                PROP_NAME => CANDLE_4H_SIGNAL3,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLE_4H_HISTOGRAM3 => [
                PROP_NAME => CANDLE_4H_HISTOGRAM3,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],

            CANDLE_4H_AVGU14 => [
                PROP_NAME => CANDLE_4H_AVGU14,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_4H_AVGD14 => [
                PROP_NAME => CANDLE_4H_AVGD14,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_4H_RSI14 => [
                PROP_NAME => CANDLE_4H_RSI14,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_4H_RSI_EMA9 => [
                PROP_NAME => CANDLE_4H_RSI_EMA9,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_4H_RSI_EMA5 => [
                PROP_NAME => CANDLE_4H_RSI_EMA5,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_4H_RSI_EMA4 => [
                PROP_NAME => CANDLE_4H_RSI_EMA4,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_4H_RSI_WMA => [
                PROP_NAME => CANDLE_4H_RSI_WMA,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_4H_PRICE_WMA => [
                PROP_NAME => CANDLE_4H_PRICE_WMA,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_4H_PRICE_WMA45 => [
                PROP_NAME => CANDLE_4H_PRICE_WMA45,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_4H_RSI_WMA45 => [
                PROP_NAME => CANDLE_4H_RSI_WMA45,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_4H_RSI_EMA9 => [
                PROP_NAME => CANDLE_4H_RSI_EMA9,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_4H_PRICE_EMA9 => [
                PROP_NAME => CANDLE_4H_PRICE_EMA9,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_4H_NET_EMA9_WMA45 => [
                PROP_NAME => CANDLE_4H_NET_EMA9_WMA45,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],

        );

        $this->query_builder = DB::table(CANDLE_4H_TABLE);
        $this->id = CANDLE_4H_ID;
        $this->name = CANDLE_4H_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

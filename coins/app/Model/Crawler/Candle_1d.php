<?php

namespace App\Model\Crawler;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Candle_1d extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            CANDLE_1D_ID => [
                PROP_NAME => CANDLE_1D_ID,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_SYMBOL => [
                PROP_NAME => CANDLE_1D_SYMBOL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_OPEN_TIME => [
                PROP_NAME => CANDLE_1D_OPEN_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_CLOSE_TIME => [
                PROP_NAME => CANDLE_1D_CLOSE_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_OPEN => [
                PROP_NAME => CANDLE_1D_OPEN,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_CLOSE => [
                PROP_NAME => CANDLE_1D_CLOSE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_HIGH => [
                PROP_NAME => CANDLE_1D_HIGH,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_LOW => [
                PROP_NAME => CANDLE_1D_LOW,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_TRADES => [
                PROP_NAME => CANDLE_1D_TRADES,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_VOLUME => [
                PROP_NAME => CANDLE_1D_VOLUME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_EMA5 => [
                PROP_NAME => CANDLE_1D_EMA5,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_EMA9 => [
                PROP_NAME => CANDLE_1D_EMA9,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_EMA12 => [
                PROP_NAME => CANDLE_1D_EMA12,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_EMA13 => [
                PROP_NAME => CANDLE_1D_EMA13,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_EMA26 => [
                PROP_NAME => CANDLE_1D_EMA26,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_MACD => [
                PROP_NAME => CANDLE_1D_MACD,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_SIGNAL => [
                PROP_NAME => CANDLE_1D_SIGNAL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_HISTOGRAM => [
                PROP_NAME => CANDLE_1D_HISTOGRAM,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_SIGNAL7 => [
                PROP_NAME => CANDLE_1D_SIGNAL7,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_HISTOGRAM7 => [
                PROP_NAME => CANDLE_1D_HISTOGRAM7,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_SIGNAL4 => [
                PROP_NAME => CANDLE_1D_SIGNAL4,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_HISTOGRAM4 => [
                PROP_NAME => CANDLE_1D_HISTOGRAM4,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_SIGNAL2 => [
                PROP_NAME => CANDLE_1D_SIGNAL2,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_HISTOGRAM2 => [
                PROP_NAME => CANDLE_1D_HISTOGRAM2,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_SIGNAL3 => [
                PROP_NAME => CANDLE_1D_SIGNAL3,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_HISTOGRAM3 => [
                PROP_NAME => CANDLE_1D_HISTOGRAM3,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_SIGNAL5 => [
                PROP_NAME => CANDLE_1D_SIGNAL5,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_HISTOGRAM5 => [
                PROP_NAME => CANDLE_1D_HISTOGRAM5,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_SIGNAL6 => [
                PROP_NAME => CANDLE_1D_SIGNAL6,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_HISTOGRAM6 => [
                PROP_NAME => CANDLE_1D_HISTOGRAM6,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_AVGU14 => [
                PROP_NAME => CANDLE_1D_AVGU14,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_AVGD14 => [
                PROP_NAME => CANDLE_1D_AVGD14,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_RSI14 => [
                PROP_NAME => CANDLE_1D_RSI14,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_RSI_EMA9 => [
                PROP_NAME => CANDLE_1D_RSI_EMA9,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_RSI_EMA5 => [
                PROP_NAME => CANDLE_1D_RSI_EMA5,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_RSI_EMA4 => [
                PROP_NAME => CANDLE_1D_RSI_EMA4,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_1D_RSI_WMA => [
                PROP_NAME => CANDLE_1D_RSI_WMA,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],

        );

        $this->query_builder = DB::table(CANDLE_1D_TABLE);
        // $this->query_builder = DB::connection('coin_crawler')->table(CANDLE_1D_TABLE);
        $this->id = CANDLE_1D_ID;
        $this->name = CANDLE_1D_TABLE;

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

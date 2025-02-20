<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Candle_24h extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            CANDLE_24H_ID => [
                PROP_NAME => CANDLE_24H_ID,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_24H_SYMBOL => [
                PROP_NAME => CANDLE_24H_SYMBOL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_24H_TIME => [
                PROP_NAME => CANDLE_24H_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_24H_DATE => [
                PROP_NAME => CANDLE_24H_DATE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_24H_OPEN_TIME => [
                PROP_NAME => CANDLE_24H_OPEN_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_24H_CLOSE_TIME => [
                PROP_NAME => CANDLE_24H_CLOSE_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_24H_OPEN => [
                PROP_NAME => CANDLE_24H_OPEN,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_24H_CLOSE => [
                PROP_NAME => CANDLE_24H_CLOSE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_24H_LOW => [
                PROP_NAME => CANDLE_24H_LOW,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_24H_HIGH => [
                PROP_NAME => CANDLE_24H_HIGH,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_24H_VOLUME => [
                PROP_NAME => CANDLE_24H_VOLUME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_24H_VOLUME_USDT => [
                PROP_NAME => CANDLE_24H_VOLUME_USDT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CANDLE_24H_TRADE => [
                PROP_NAME => CANDLE_24H_TRADE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],

        );

        $this->query_builder = DB::connection('coin_analytics')->table(CANDLE_24H_TABLE);
        $this->id = CANDLE_24H_ID;
        $this->name = CANDLE_24H_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

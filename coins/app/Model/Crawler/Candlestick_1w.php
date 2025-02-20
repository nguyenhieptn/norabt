<?php

namespace App\Model\Crawler;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Candlestick_1w extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            CANDLESTICK_1W_ID => [
                PROP_NAME => CANDLESTICK_1W_ID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            CANDLESTICK_1W_SYMBOL => [
                PROP_NAME => CANDLESTICK_1W_SYMBOL,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLESTICK_1W_OPEN_TIME => [
                PROP_NAME => CANDLESTICK_1W_OPEN_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            CANDLESTICK_1W_CLOSE_TIME => [
                PROP_NAME => CANDLESTICK_1W_CLOSE_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            CANDLESTICK_1W_OPEN => [
                PROP_NAME => CANDLESTICK_1W_OPEN,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLESTICK_1W_CLOSE => [
                PROP_NAME => CANDLESTICK_1W_CLOSE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLESTICK_1W_HIGH => [
                PROP_NAME => CANDLESTICK_1W_HIGH,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLESTICK_1W_LOW => [
                PROP_NAME => CANDLESTICK_1W_LOW,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLESTICK_1W_VOLUME => [
                PROP_NAME => CANDLESTICK_1W_VOLUME,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLESTICK_1W_ASSET_VOLUME => [
                PROP_NAME => CANDLESTICK_1W_ASSET_VOLUME,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLESTICK_1W_NUMBER_TRADES => [
                PROP_NAME => CANDLESTICK_1W_NUMBER_TRADES,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLESTICK_1W_BASE => [
                PROP_NAME => CANDLESTICK_1W_BASE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLESTICK_1W_QUOTE => [
                PROP_NAME => CANDLESTICK_1W_QUOTE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLESTICK_1W_IGNORE => [
                PROP_NAME => CANDLESTICK_1W_IGNORE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],

        );

        $this->query_builder = DB::connection('coin_crawler')->table(CANDLESTICK_1W_TABLE);
        $this->id = CANDLESTICK_1W_ID;
        $this->name = CANDLESTICK_1W_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

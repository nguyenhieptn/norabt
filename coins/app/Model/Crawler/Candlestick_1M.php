<?php

namespace App\Model\Crawler;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Candlestick_1M extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            CANDLESTICK_1M_ID => [
                PROP_NAME => CANDLESTICK_1M_ID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            CANDLESTICK_1M_SYMBOL => [
                PROP_NAME => CANDLESTICK_1M_SYMBOL,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLESTICK_1M_OPEN_TIME => [
                PROP_NAME => CANDLESTICK_1M_OPEN_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            CANDLESTICK_1M_CLOSE_TIME => [
                PROP_NAME => CANDLESTICK_1M_CLOSE_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            CANDLESTICK_1M_OPEN => [
                PROP_NAME => CANDLESTICK_1M_OPEN,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLESTICK_1M_CLOSE => [
                PROP_NAME => CANDLESTICK_1M_CLOSE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLESTICK_1M_HIGH => [
                PROP_NAME => CANDLESTICK_1M_HIGH,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLESTICK_1M_LOW => [
                PROP_NAME => CANDLESTICK_1M_LOW,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLESTICK_1M_VOLUME => [
                PROP_NAME => CANDLESTICK_1M_VOLUME,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLESTICK_1M_ASSET_VOLUMN => [
                PROP_NAME => CANDLESTICK_1M_ASSET_VOLUMN,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLESTICK_1M_NUMBER_TRADES => [
                PROP_NAME => CANDLESTICK_1M_NUMBER_TRADES,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLESTICK_1M_BASE => [
                PROP_NAME => CANDLESTICK_1M_BASE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLESTICK_1M_QUOTE => [
                PROP_NAME => CANDLESTICK_1M_QUOTE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CANDLESTICK_1M_IGNORE => [
                PROP_NAME => CANDLESTICK_1M_IGNORE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],

        );

        $this->query_builder = DB::connection('coin_crawler')->table(CANDLESTICK_1M_TABLE);
        $this->id = CANDLESTICK_1M_ID;
        $this->name = CANDLESTICK_1M_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

<?php

namespace App\Model\Crawler;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class WMA45 extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            WMA45_TIME => [
                PROP_NAME => WMA45_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            WMA45_SYMBOL => [
                PROP_NAME => WMA45_SYMBOL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            WMA45_OPEN => [
                PROP_NAME => WMA45_OPEN,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            WMA45_HIGH => [
                PROP_NAME => WMA45_HIGH,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            WMA45_LOW => [
                PROP_NAME => WMA45_LOW,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            WMA45_CLOSE => [
                PROP_NAME => WMA45_CLOSE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            WMA45_VOLUME_BTC => [
                PROP_NAME => WMA45_VOLUME_BTC,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            WMA45_VOLUME_USD => [
                PROP_NAME => WMA45_VOLUME_USD,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            WMA45_RSI14_1D => [
                PROP_NAME => WMA45_RSI14_1D,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            WMA45_RSI14_1W => [
                PROP_NAME => WMA45_RSI14_1W,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            WMA45_WMA45_1D => [
                PROP_NAME => WMA45_WMA45_1D,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            WMA45_WMA45_1W => [
                PROP_NAME => WMA45_WMA45_1W,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],

        );

        $this->query_builder = DB::connection('coin_crawler')->table(WMA_45_TABLE);
        $this->id = WMA45_TIME;
        $this->name = WMA_45_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

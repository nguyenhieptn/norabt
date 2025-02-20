<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Watchlist extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            WL_ID => [
                PROP_NAME => WL_ID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            WL_SYMBOL => [
                PROP_NAME => WL_SYMBOL,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            WL_NOTE => [
                PROP_NAME => WL_NOTE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            WL_UID => [
                PROP_NAME => WL_UID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            WL_TIME => [
                PROP_NAME => WL_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            WL_STOPTIME => [
                PROP_NAME => WL_STOPTIME,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            WL_ICON => [
                PROP_NAME => WL_ICON,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            WL_IS_KLINE => [
                PROP_NAME => WL_IS_KLINE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            WL_IS_BUSD => [
                PROP_NAME => WL_IS_BUSD,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],

        );

        $this->query_builder = DB::table(WATCHLIST_TABLE);
        $this->id = WL_ID;
        $this->name = WATCHLIST_TABLE;

        $this->registerSql = [
            ['Admin/Candle_1h', WL_SYMBOL, CANDLE_1H_SYMBOL, null, null, 'cascade', null],
            ['Admin/Candle_3m', WL_SYMBOL, CANDLE_3M_SYMBOL, null, null, 'cascade', null],
            ['Admin/Candle_15m', WL_SYMBOL, CANDLE_15M_SYMBOL, null, null, 'cascade', null],
            ['Admin/Candle_1m', WL_SYMBOL, CANDLE_1M_SYMBOL, null, null, 'cascade', null],
            ['Admin/Trades', WL_SYMBOL, TRADE_SYMBOL, null, null, 'deny', null],
            ['Admin/Testnet_campaign', WL_SYMBOL, TESTNET_SYMBOL, null, null, 'deny', null],
            ['Admin/Price_1s', WL_SYMBOL, PRICE_1S_SYMBOL, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

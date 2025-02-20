<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Trades extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            TRADE_ID => [
                PROP_NAME => TRADE_ID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TRADE_ACCOUNT => [
                PROP_NAME => TRADE_ACCOUNT,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TRADE_SYMBOL => [
                PROP_NAME => TRADE_SYMBOL,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            TRADE_BUDGET => [
                PROP_NAME => TRADE_BUDGET,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            TRADE_ACTION_BUDGET => [
                PROP_NAME => TRADE_ACTION_BUDGET,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            TRADE_MONEY => [
                PROP_NAME => TRADE_MONEY,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            TRADE_PROFIT => [
                PROP_NAME => TRADE_PROFIT,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            TRADE_PARAM => [
                PROP_NAME => TRADE_PARAM,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TRADE_SIDE => [
                PROP_NAME => TRADE_SIDE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TRADE_STRATEGY => [
                PROP_NAME => TRADE_STRATEGY,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TRADE_START_TIME => [
                PROP_NAME => TRADE_START_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TRADE_STOP_TIME => [
                PROP_NAME => TRADE_STOP_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TRADE_PRIORITY => [
                PROP_NAME => TRADE_PRIORITY,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TRADE_COMPOUND => [
                PROP_NAME => TRADE_COMPOUND,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],

        );

        $this->query_builder = DB::connection('binance')->table(TRADES_TABLE);
        $this->id = TRADE_ID;
        $this->name = TRADES_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Strategies extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            STRATEGY_ID => [
                PROP_NAME => STRATEGY_ID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            STRATEGY_NAME => [
                PROP_NAME => STRATEGY_NAME,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            STRATEGY_CONTENT => [
                PROP_NAME => STRATEGY_CONTENT,
                PROP_NULL => true,
                PROP_REGEX => "Json",
            ],
            STRATEGY_NOTE => [
                PROP_NAME => STRATEGY_NOTE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            STRATEGY_TAKEPROFIT => [
                PROP_NAME => STRATEGY_TAKEPROFIT,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            STRATEGY_STOPLOSS => [
                PROP_NAME => STRATEGY_STOPLOSS,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            STRATEGY_BASEPROFIT => [
                PROP_NAME => STRATEGY_BASEPROFIT,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            STRATEGY_STEPPROFIT => [
                PROP_NAME => STRATEGY_STEPPROFIT,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            STRATEGY_BACKPROFIT => [
                PROP_NAME => STRATEGY_BACKPROFIT,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            STRATEGY_TIMELIFE => [
                PROP_NAME => STRATEGY_TIMELIFE,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            STRATEGY_INTERVAL => [
                PROP_NAME => STRATEGY_INTERVAL,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            STRATEGY_MARGIN => [
                PROP_NAME => STRATEGY_MARGIN,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            STRATEGY_BASEPROFIT_BASEON => [
                PROP_NAME => STRATEGY_BASEPROFIT_BASEON,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            STRATEGY_CONTAINER => [
                PROP_NAME => STRATEGY_CONTAINER,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            STRATEGY_USER => [
                PROP_NAME => STRATEGY_USER,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],

        );

        $this->query_builder = DB::table(STRATEGIES_TABLE);
        $this->id = STRATEGY_ID;
        $this->name = STRATEGIES_TABLE;

        $this->registerSql = [
            ['Admin/Testnet_campaign', STRATEGY_ID, TESTNET_STRATEGY, null, null, 'deny', null],
            ['Admin/Trades', STRATEGY_ID, TRADE_STRATEGY, null, null, 'deny', null],
            ['Admin/Strategy_container', STRATEGY_ID, STRA_CON_CONTAINER, null, null, 'cascade', null],
            ['Admin/Strategy_container', STRATEGY_ID, STRA_CON_CHILD, null, null, 'deny', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

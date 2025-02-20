<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Lab_strategies extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            LAB_STRATEGY_ID => [
                PROP_NAME => LAB_STRATEGY_ID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_STRATEGY_NAME => [
                PROP_NAME => LAB_STRATEGY_NAME,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            LAB_STRATEGY_CONTENT => [
                PROP_NAME => LAB_STRATEGY_CONTENT,
                PROP_NULL => true,
                PROP_REGEX => "Json",
            ],
            LAB_STRATEGY_TAKEPROFIT => [
                PROP_NAME => LAB_STRATEGY_TAKEPROFIT,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_STRATEGY_STOPLOSS => [
                PROP_NAME => LAB_STRATEGY_STOPLOSS,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_STRATEGY_BASEPROFIT => [
                PROP_NAME => LAB_STRATEGY_BASEPROFIT,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_STRATEGY_STEPPROFIT => [
                PROP_NAME => LAB_STRATEGY_STEPPROFIT,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_STRATEGY_BACKPROFIT => [
                PROP_NAME => LAB_STRATEGY_BACKPROFIT,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],

            LAB_STRATEGY_BASEPROFIT_BASEON => [
                PROP_NAME => LAB_STRATEGY_BASEPROFIT_BASEON,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            LAB_STRATEGY_TIMELIFE => [
                PROP_NAME => LAB_STRATEGY_TIMELIFE,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_STRATEGY_INTERVAL => [
                PROP_NAME => LAB_STRATEGY_INTERVAL,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_STRATEGY_NOTE => [
                PROP_NAME => LAB_STRATEGY_NOTE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_STRATEGY_CONTAINER => [
                PROP_NAME => LAB_STRATEGY_CONTAINER,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_STRATEGY_MARGIN => [
                PROP_NAME => LAB_STRATEGY_MARGIN,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_STRATEGY_USER => [
                PROP_NAME => LAB_STRATEGY_USER,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_STRATEGY_GROUP => [
                PROP_NAME => LAB_STRATEGY_GROUP,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],

        );

        $this->query_builder = DB::connection('lab')->table(LAB_STRATEGIES_TABLE);
        $this->id = LAB_STRATEGY_ID;
        $this->name = LAB_STRATEGIES_TABLE;

        $this->registerSql = [
            ['Admin/Lab_campaigns', LAB_STRATEGY_ID, LAB_CAMPAIGN_STRATEGY, null, null, 'deny', null],
            ['Admin/Lab_strategy_container', LAB_STRATEGY_ID, LAB_STRA_CON_CONTAINER, null, null, 'cascade', null],
            ['Admin/Lab_strategy_container', LAB_STRATEGY_ID, LAB_STRA_CON_CHILD, null, null, 'deny', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

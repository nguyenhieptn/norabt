<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Testnet_results extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            TESTNET_RESULT_ID => [
                PROP_NAME => TESTNET_RESULT_ID,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_CAMPAIGN => [
                PROP_NAME => TESTNET_RESULT_CAMPAIGN,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_STRATEGY => [
                PROP_NAME => TESTNET_RESULT_STRATEGY,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_SYMBOL => [
                PROP_NAME => TESTNET_RESULT_SYMBOL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_CHART => [
                PROP_NAME => TESTNET_RESULT_CHART,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_ENTER_TIME => [
                PROP_NAME => TESTNET_RESULT_ENTER_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_ENTER_PRICE => [
                PROP_NAME => TESTNET_RESULT_ENTER_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_ORDER_TIME => [
                PROP_NAME => TESTNET_RESULT_ORDER_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_ORDER_PRICE => [
                PROP_NAME => TESTNET_RESULT_ORDER_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_ORDER_PHASE => [
                PROP_NAME => TESTNET_RESULT_ORDER_PHASE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_ORDER_RELEASE => [
                PROP_NAME => TESTNET_RESULT_ORDER_RELEASE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_ORDER_QTY => [
                PROP_NAME => TESTNET_RESULT_ORDER_QTY,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_HIGH => [
                PROP_NAME => TESTNET_RESULT_HIGH,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_LOW => [
                PROP_NAME => TESTNET_RESULT_LOW,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_TYPE => [
                PROP_NAME => TESTNET_RESULT_TYPE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_BASE => [
                PROP_NAME => TESTNET_RESULT_BASE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_PARAMS => [
                PROP_NAME => TESTNET_RESULT_PARAMS,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_START_REASON => [
                PROP_NAME => TESTNET_RESULT_START_REASON,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_STATUS => [
                PROP_NAME => TESTNET_RESULT_STATUS,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_MATCHED_EMA5 => [
                PROP_NAME => TESTNET_RESULT_MATCHED_EMA5,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_MATCHED_PRICE => [
                PROP_NAME => TESTNET_RESULT_MATCHED_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_MATCHED_TIME => [
                PROP_NAME => TESTNET_RESULT_MATCHED_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_MATCHED_QTY => [
                PROP_NAME => TESTNET_RESULT_MATCHED_QTY,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_SELL_PRICE => [
                PROP_NAME => TESTNET_RESULT_SELL_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_SELL_TIME => [
                PROP_NAME => TESTNET_RESULT_SELL_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_PROFIT => [
                PROP_NAME => TESTNET_RESULT_PROFIT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_EVENT_PROFIT => [
                PROP_NAME => TESTNET_RESULT_EVENT_PROFIT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_REAL_PROFIT => [
                PROP_NAME => TESTNET_RESULT_REAL_PROFIT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_REAL_PNL => [
                PROP_NAME => TESTNET_RESULT_REAL_PNL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_BASEPROFIT => [
                PROP_NAME => TESTNET_RESULT_BASEPROFIT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_PENDING => [
                PROP_NAME => TESTNET_RESULT_PENDING,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_PHASE => [
                PROP_NAME => TESTNET_RESULT_PHASE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_BUDGET => [
                PROP_NAME => TESTNET_RESULT_BUDGET,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_COMMIT => [
                PROP_NAME => TESTNET_RESULT_COMMIT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_NEXTPHASE_NOTE => [
                PROP_NAME => TESTNET_RESULT_NEXTPHASE_NOTE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_PHASE_NOTE => [
                PROP_NAME => TESTNET_RESULT_PHASE_NOTE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_LAST_PRICE => [
                PROP_NAME => TESTNET_RESULT_LAST_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_FIRST_PRICE => [
                PROP_NAME => TESTNET_RESULT_FIRST_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_FLOW => [
                PROP_NAME => TESTNET_RESULT_FLOW,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_CONTAINER => [
                PROP_NAME => TESTNET_RESULT_CONTAINER,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_GROUP => [
                PROP_NAME => TESTNET_RESULT_GROUP,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_INTERVAL => [
                PROP_NAME => TESTNET_RESULT_INTERVAL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_MARGIN => [
                PROP_NAME => TESTNET_RESULT_MARGIN,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_ACCOUNT => [
                PROP_NAME => TESTNET_RESULT_ACCOUNT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESULT_CHART_PRICE => [
                PROP_NAME => TESTNET_RESULT_CHART_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],

        );

        $this->query_builder = DB::table(TESTNET_RESULTS_TABLE);
        $this->id = TESTNET_RESULT_ID;
        $this->name = TESTNET_RESULTS_TABLE;

        $this->registerSql = [
            ['Admin/Testnet_order', TESTNET_RESULT_ID, TESTNET_ORDER_ACTION, null, null, 'cascade', null],
            ['Admin/Testnet_enterbase', TESTNET_RESULT_ID, ENTERBASE_ACTION, null, null, 'cascade', null],
            ['Admin/Testnet_profitbase', TESTNET_RESULT_ID, PROFITBASE_ACTION, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

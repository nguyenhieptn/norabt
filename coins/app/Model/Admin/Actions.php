<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Actions extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            ACTION_ID => [
                PROP_NAME => ACTION_ID,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_BINANCE => [
                PROP_NAME => ACTION_BINANCE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_SYMBOL => [
                PROP_NAME => ACTION_SYMBOL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_ACCOUNT => [
                PROP_NAME => ACTION_ACCOUNT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_CHART => [
                PROP_NAME => ACTION_CHART,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_ENTER_TIME => [
                PROP_NAME => ACTION_ENTER_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_ENTER_QTY => [
                PROP_NAME => ACTION_ENTER_QTY,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_ENTER_PRICE => [
                PROP_NAME => ACTION_ENTER_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_ORDER_TIME => [
                PROP_NAME => ACTION_ORDER_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_ORDER_QTY => [
                PROP_NAME => ACTION_ORDER_QTY,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_ORDER_PRICE => [
                PROP_NAME => ACTION_ORDER_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_ORDER_PHASE => [
                PROP_NAME => ACTION_ORDER_PHASE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_ORDER_RELEASE => [
                PROP_NAME => ACTION_ORDER_RELEASE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_LOW => [
                PROP_NAME => ACTION_LOW,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_HIGH => [
                PROP_NAME => ACTION_HIGH,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_TYPE => [
                PROP_NAME => ACTION_TYPE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_STATUS => [
                PROP_NAME => ACTION_STATUS,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_EVENT_DATA => [
                PROP_NAME => ACTION_EVENT_DATA,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_STOP_REASON => [
                PROP_NAME => ACTION_STOP_REASON,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_START_REASON => [
                PROP_NAME => ACTION_START_REASON,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_MATCHED_PRICE => [
                PROP_NAME => ACTION_MATCHED_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_MATCHED_EMA5 => [
                PROP_NAME => ACTION_MATCHED_EMA5,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_MATCHED_QTY => [
                PROP_NAME => ACTION_MATCHED_QTY,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_MATCHED_TIME => [
                PROP_NAME => ACTION_MATCHED_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_MATCHED_EXPECTED_QTY => [
                PROP_NAME => ACTION_MATCHED_EXPECTED_QTY,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_SELL_PRICE => [
                PROP_NAME => ACTION_SELL_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_SELL_TIME => [
                PROP_NAME => ACTION_SELL_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_PROFIT => [
                PROP_NAME => ACTION_PROFIT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_EVENTPROFIT => [
                PROP_NAME => ACTION_EVENTPROFIT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_BASEPROFIT => [
                PROP_NAME => ACTION_BASEPROFIT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_REALPROFIT => [
                PROP_NAME => ACTION_REALPROFIT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_TOTALPROFIT => [
                PROP_NAME => ACTION_TOTALPROFIT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_PNL => [
                PROP_NAME => ACTION_PNL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_COMMIT => [
                PROP_NAME => ACTION_COMMIT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_PENDING => [
                PROP_NAME => ACTION_PENDING,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_LOG => [
                PROP_NAME => ACTION_LOG,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_STRATEGY => [
                PROP_NAME => ACTION_STRATEGY,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_BUDGET => [
                PROP_NAME => ACTION_BUDGET,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_BUDGET_ACTIVE => [
                PROP_NAME => ACTION_BUDGET_ACTIVE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_BUDGET_USED => [
                PROP_NAME => ACTION_BUDGET_USED,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_PHASE => [
                PROP_NAME => ACTION_PHASE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_MARGIN => [
                PROP_NAME => ACTION_MARGIN,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_NEXTPHASE_NOTE => [
                PROP_NAME => ACTION_NEXTPHASE_NOTE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_PHASE_NOTE => [
                PROP_NAME => ACTION_PHASE_NOTE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            
            ACTION_LIQUIDATION => [
                PROP_NAME => ACTION_LIQUIDATION,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_LAST_PRICE => [
                PROP_NAME => ACTION_LAST_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_FIRST_PRICE => [
                PROP_NAME => ACTION_FIRST_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_FLOW => [
                PROP_NAME => ACTION_FLOW,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_CONTAINER => [
                PROP_NAME => ACTION_CONTAINER,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ACTION_INTERVAL => [
                PROP_NAME => ACTION_INTERVAL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],

        );

        $this->query_builder = DB::connection('binance')->table(ACTIONS_TABLE);
        $this->id = ACTION_ID;
        $this->name = ACTIONS_TABLE;

        $this->registerSql = [
            ['Admin/Orders', ACTION_ID, ORDER_ACTION, null, null, 'cascade', null],
            ['Admin/Log_enterbase', ACTION_ID, LOG_ENTERBASE_ACTION, null, null, 'cascade', null],
            ['Admin/Log_profitbase', ACTION_ID, LOG_PROFITBASE_ACTION, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Lab_results extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            LAB_RESULT_ID => [
                PROP_NAME => LAB_RESULT_ID,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_CAMPAIGN => [
                PROP_NAME => LAB_RESULT_CAMPAIGN,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_STRATEGY => [
                PROP_NAME => LAB_RESULT_STRATEGY,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_SYMBOL => [
                PROP_NAME => LAB_RESULT_SYMBOL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_ENTER_TIME => [
                PROP_NAME => LAB_RESULT_ENTER_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_ENTER_PRICE => [
                PROP_NAME => LAB_RESULT_ENTER_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_ORDER_TIME => [
                PROP_NAME => LAB_RESULT_ORDER_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_ORDER_QTY => [
                PROP_NAME => LAB_RESULT_ORDER_QTY,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_ORDER_PHASE => [
                PROP_NAME => LAB_RESULT_ORDER_PHASE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_ORDER_RELEASE => [
                PROP_NAME => LAB_RESULT_ORDER_RELEASE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_CHART => [
                PROP_NAME => LAB_RESULT_CHART,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_CHART_PRICE  => [
                PROP_NAME => LAB_RESULT_CHART_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_ORDER_PRICE => [
                PROP_NAME => LAB_RESULT_ORDER_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_HIGH => [
                PROP_NAME => LAB_RESULT_HIGH,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_LOW => [
                PROP_NAME => LAB_RESULT_LOW,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_MATCHED_EMA5 => [
                PROP_NAME => LAB_RESULT_MATCHED_EMA5,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_TYPE => [
                PROP_NAME => LAB_RESULT_TYPE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_BASE => [
                PROP_NAME => LAB_RESULT_BASE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_PARAMS => [
                PROP_NAME => LAB_RESULT_PARAMS,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_START_REASON => [
                PROP_NAME => LAB_RESULT_START_REASON,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_STATUS => [
                PROP_NAME => LAB_RESULT_STATUS,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_MATCHED_PRICE => [
                PROP_NAME => LAB_RESULT_MATCHED_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_MATCHED_TIME => [
                PROP_NAME => LAB_RESULT_MATCHED_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_MATCHED_QTY => [
                PROP_NAME => LAB_RESULT_MATCHED_QTY,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_SELL_PRICE => [
                PROP_NAME => LAB_RESULT_SELL_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_SELL_TIME => [
                PROP_NAME => LAB_RESULT_SELL_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_PROFIT => [
                PROP_NAME => LAB_RESULT_PROFIT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_REAL_PNL => [
                PROP_NAME => LAB_RESULT_REAL_PNL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_REAL_PROFIT => [
                PROP_NAME => LAB_RESULT_REAL_PROFIT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_EVENT_PROFIT => [
                PROP_NAME => LAB_RESULT_EVENT_PROFIT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_BASEPROFIT => [
                PROP_NAME => LAB_RESULT_BASEPROFIT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_PENDING => [
                PROP_NAME => LAB_RESULT_PENDING,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_BUDGET => [
                PROP_NAME => LAB_RESULT_BUDGET,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_PHASE => [
                PROP_NAME => LAB_RESULT_PHASE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_COMMIT => [
                PROP_NAME => LAB_RESULT_COMMIT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],

            LAB_RESULT_LAST_PRICE => [
                PROP_NAME => LAB_RESULT_LAST_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],

            LAB_RESULT_FIRST_PRICE => [
                PROP_NAME => LAB_RESULT_FIRST_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_FLOW => [
                PROP_NAME => LAB_RESULT_FLOW,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_INTERVAL => [
                PROP_NAME => LAB_RESULT_INTERVAL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_BTC_WMA45_1D => [
                PROP_NAME => LAB_RESULT_BTC_WMA45_1D,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_BTC_WMA45_1W => [
                PROP_NAME => LAB_RESULT_BTC_WMA45_1W,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_ACCOUNT => [
                PROP_NAME => LAB_RESULT_ACCOUNT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_CONTAINER => [
                PROP_NAME => LAB_RESULT_CONTAINER,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_MARGIN => [
                PROP_NAME => LAB_RESULT_MARGIN,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_LOG => [
                PROP_NAME => LAB_RESULT_LOG,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],

            LAB_RESULT_1D_RSI_14 => [
                PROP_NAME => LAB_RESULT_1D_RSI_14,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_1D_RSI_EMA9 => [
                PROP_NAME => LAB_RESULT_1D_RSI_EMA9,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_1D_RSI_WMA => [
                PROP_NAME => LAB_RESULT_1D_RSI_WMA,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],

            LAB_RESULT_WALLET_BALANCE => [
                PROP_NAME => LAB_RESULT_WALLET_BALANCE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_RESULT_PROFIT_INVEST => [
                PROP_NAME => LAB_RESULT_PROFIT_INVEST,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],

        );

        $this->query_builder = DB::connection('lab')->table(LAB_RESULTS_TABLE);
        $this->id = LAB_RESULT_ID;
        $this->name = LAB_RESULTS_TABLE;

        $this->registerSql = [
            ['Admin/Lab_order', LAB_RESULT_ID, LAB_ORDER_ACTION, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Lab_opt_result extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            LAB_OPT_RESULT_ID => [
                PROP_NAME => LAB_OPT_RESULT_ID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_OPT_RESULT_OPTIMIZATION => [
                PROP_NAME => LAB_OPT_RESULT_OPTIMIZATION,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_OPT_RESULT_PARAMS => [
                PROP_NAME => LAB_OPT_RESULT_PARAMS,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_OPT_RESULT_STRATEGY => [
                PROP_NAME => LAB_OPT_RESULT_STRATEGY,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            LAB_OPT_RESULT_BALANCE => [
                PROP_NAME => LAB_OPT_RESULT_BALANCE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            LAB_OPT_RESULT_MARGIN_BALANCE => [
                PROP_NAME => LAB_OPT_RESULT_MARGIN_BALANCE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            LAB_OPT_RESULT_UNRELIZE_MAX => [
                PROP_NAME => LAB_OPT_RESULT_UNRELIZE_MAX,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            LAB_OPT_RESULT_INVEST_MAX => [
                PROP_NAME => LAB_OPT_RESULT_INVEST_MAX,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            LAB_OPT_RESULT_ACCOUNT => [
                PROP_NAME => LAB_OPT_RESULT_ACCOUNT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_OPT_RESULT_CAMPAIGN => [
                PROP_NAME => LAB_OPT_RESULT_CAMPAIGN,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_OPT_RESULT_EVENT => [
                PROP_NAME => LAB_OPT_RESULT_EVENT,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            LAB_OPT_RESULT_INTERVAL_AVG => [
                PROP_NAME => LAB_OPT_RESULT_INTERVAL_AVG,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            LAB_OPT_RESULT_INTERVAL_MAX => [
                PROP_NAME => LAB_OPT_RESULT_INTERVAL_MAX,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            LAB_OPT_RESULT_TOTAL_POSITION => [
                PROP_NAME => LAB_OPT_RESULT_TOTAL_POSITION,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_OPT_RESULT_LOG => [
                PROP_NAME => LAB_OPT_RESULT_LOG,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_OPT_RESULT_DONE => [
                PROP_NAME => LAB_OPT_RESULT_DONE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_OPT_RESULT_TOTAL_LONG => [
                PROP_NAME => LAB_OPT_RESULT_TOTAL_LONG,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_OPT_RESULT_TOTAL_SHORT => [
                PROP_NAME => LAB_OPT_RESULT_TOTAL_SHORT,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_OPT_RESULT_TOTAL_TAKEPROFIT => [
                PROP_NAME => LAB_OPT_RESULT_TOTAL_TAKEPROFIT,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_OPT_RESULT_TOTAL_STOPLOSS => [
                PROP_NAME => LAB_OPT_RESULT_TOTAL_STOPLOSS,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_OPT_RESULT_PENDING_EVENT => [
                PROP_NAME => LAB_OPT_RESULT_PENDING_EVENT,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],

        );

        $this->query_builder = DB::connection('lab')->table(LAB_OPT_RESULT_TABLE);
        $this->id = LAB_OPT_RESULT_ID;
        $this->name = LAB_OPT_RESULT_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

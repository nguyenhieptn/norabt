<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Account_summary extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            AC_SUM_ID => [
                PROP_NAME => AC_SUM_ID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            AC_SUM_ACCOUNT => [
                PROP_NAME => AC_SUM_ACCOUNT,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            AC_SUM_BALLANCE => [
                PROP_NAME => AC_SUM_BALLANCE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            AC_SUM_USED => [
                PROP_NAME => AC_SUM_USED,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            AC_SUM_FREE => [
                PROP_NAME => AC_SUM_FREE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            AC_SUM_INVESTING => [
                PROP_NAME => AC_SUM_INVESTING,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            AC_SUM_TOTALPROFIT => [
                PROP_NAME => AC_SUM_TOTALPROFIT,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            AC_SUM_TODAYPROFIT => [
                PROP_NAME => AC_SUM_TODAYPROFIT,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            AC_SUM_MONTHPROFIT => [
                PROP_NAME => AC_SUM_MONTHPROFIT,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            AC_SUM_TRADING => [
                PROP_NAME => AC_SUM_TRADING,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            AC_SUM_UNREALIZED_PROFIT => [
                PROP_NAME => AC_SUM_UNREALIZED_PROFIT,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],

            AC_SUM_MAINT_MARGIN => [
                PROP_NAME => AC_SUM_MAINT_MARGIN,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            AC_SUM_MARGIN_BALANCE => [
                PROP_NAME => AC_SUM_MARGIN_BALANCE,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            AC_SUM_MARGIN_RATIO => [
                PROP_NAME => AC_SUM_MARGIN_RATIO,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            AC_SUM_AVAILABLE => [
                PROP_NAME => AC_SUM_AVAILABLE,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            AC_SUM_INITIAL_MARGIN => [
                PROP_NAME => AC_SUM_INITIAL_MARGIN,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],

            AC_SUM_FUNDING_FEE => [
                PROP_NAME => AC_SUM_FUNDING_FEE,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            AC_SUM_REFERAL => [
                PROP_NAME => AC_SUM_REFERAL,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            AC_SUM_COMMISSION => [
                PROP_NAME => AC_SUM_COMMISSION,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],



        );

        $this->query_builder = DB::connection('binance')->table(ACCOUNT_SUMMARY_TABLE);
        $this->id = AC_SUM_ID;
        $this->name = ACCOUNT_SUMMARY_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

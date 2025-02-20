<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Testnet_campaign extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            TESTNET_ID => [
                PROP_NAME => TESTNET_ID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TESTNET_NAME => [
                PROP_NAME => TESTNET_NAME,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            TESTNET_SYMBOL => [
                PROP_NAME => TESTNET_SYMBOL,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            TESTNET_PARAM => [
                PROP_NAME => TESTNET_PARAM,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_SIDE => [
                PROP_NAME => TESTNET_SIDE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_STRATEGY => [
                PROP_NAME => TESTNET_STRATEGY,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TESTNET_START_TIME => [
                PROP_NAME => TESTNET_START_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TESTNET_STOP_TIME => [
                PROP_NAME => TESTNET_STOP_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TESTNET_NOTE => [
                PROP_NAME => TESTNET_NOTE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_BUDGET => [
                PROP_NAME => TESTNET_BUDGET,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_RESERVE => [
                PROP_NAME => TESTNET_RESERVE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_COMPOUND => [
                PROP_NAME => TESTNET_COMPOUND,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_PROFIT => [
                PROP_NAME => TESTNET_PROFIT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_TELE_BOT => [
                PROP_NAME => TESTNET_TELE_BOT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_TELE_GR_NOTICE => [
                PROP_NAME => TESTNET_TELE_GR_NOTICE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_TELE_GR_ERROR => [
                PROP_NAME => TESTNET_TELE_GR_ERROR,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_TELE_GR_SUMMARY => [
                PROP_NAME => TESTNET_TELE_GR_SUMMARY,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_GROUP => [
                PROP_NAME => TESTNET_GROUP,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            TESTNET_PRIORITY => [
                PROP_NAME => TESTNET_PRIORITY,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TESTNET_ACCOUNT => [
                PROP_NAME => TESTNET_ACCOUNT,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TESTNET_MONEY => [
                PROP_NAME => TESTNET_MONEY,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TESTNET_ACTIVE_BUDGET => [
                PROP_NAME => TESTNET_ACTIVE_BUDGET,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TESTNET_ACTIVE => [
                PROP_NAME => TESTNET_ACTIVE,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],

        );

        $this->query_builder = DB::table(TESTNET_CAMPAIGN_TABLE);
        $this->id = TESTNET_ID;
        $this->name = TESTNET_CAMPAIGN_TABLE;

        $this->registerSql = [
            ['Admin/Testnet_results', TESTNET_ID, TESTNET_RESULT_CAMPAIGN, null, null, 'cascade', null],
            ['Admin/Testnet_event_logs', TESTNET_ID, TESTNET_ELOG_CAMPAIGN, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

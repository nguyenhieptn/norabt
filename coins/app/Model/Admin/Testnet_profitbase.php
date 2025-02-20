<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Testnet_profitbase extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            PROFITBASE_ID => [
                PROP_NAME => PROFITBASE_ID,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            PROFITBASE_CAMPAIGN => [
                PROP_NAME => PROFITBASE_CAMPAIGN,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            PROFITBASE_SYMBOL => [
                PROP_NAME => PROFITBASE_SYMBOL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            PROFITBASE_ACTION => [
                PROP_NAME => PROFITBASE_ACTION,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            PROFITBASE_TIME => [
                PROP_NAME => PROFITBASE_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            PROFITBASE_PRICE => [
                PROP_NAME => PROFITBASE_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            PROFITBASE_VALUE => [
                PROP_NAME => PROFITBASE_VALUE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            PROFITBASE_EVENT => [
                PROP_NAME => PROFITBASE_EVENT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],

        );

        $this->query_builder = DB::table(TESTNET_PROFITBASE_TABLE);
        $this->id = PROFITBASE_ID;
        $this->name = TESTNET_PROFITBASE_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

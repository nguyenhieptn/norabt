<?php

namespace App\Model\Crawler;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Top_sum extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            TOP_SUM_ID => [
                PROP_NAME => TOP_SUM_ID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TOP_SUM_TIME => [
                PROP_NAME => TOP_SUM_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TOP_SUM_IN => [
                PROP_NAME => TOP_SUM_IN,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            TOP_SUM_OUT => [
                PROP_NAME => TOP_SUM_OUT,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            TOP_SUM_BALANCE => [
                PROP_NAME => TOP_SUM_BALANCE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],

            TOP_SUM_NEW_IN => [
                PROP_NAME => TOP_SUM_NEW_IN,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            TOP_SUM_OUTED => [
                PROP_NAME => TOP_SUM_OUTED,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            TOP_SUM_ADDRESS_IN => [
                PROP_NAME => TOP_SUM_ADDRESS_IN,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TOP_SUM_ADDRESS_OUTED => [
                PROP_NAME => TOP_SUM_ADDRESS_OUTED,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TOP_SUM_CHANGE_COUNT => [
                PROP_NAME => TOP_SUM_CHANGE_COUNT,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],

        );

        $this->query_builder = DB::connection('coin_crawler')->table(TOP_SUMMARY_TABLE);
        $this->id = TOP_SUM_ID;
        $this->name = TOP_SUMMARY_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

<?php

namespace App\Model\Crawler;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Top_btc extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            TOP_BTC_ID => [
                PROP_NAME => TOP_BTC_ID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TOP_BTC_TIME => [
                PROP_NAME => TOP_BTC_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TOP_BTC_ADDRESS => [
                PROP_NAME => TOP_BTC_ADDRESS,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TOP_BTC_BTC => [
                PROP_NAME => TOP_BTC_BTC,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            TOP_BTC_USD => [
                PROP_NAME => TOP_BTC_USD,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            TOP_BTC_DENTAL_1W => [
                PROP_NAME => TOP_BTC_DENTAL_1W,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TOP_BTC_DENTAL_1M => [
                PROP_NAME => TOP_BTC_DENTAL_1M,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TOP_BTC_PERCENT => [
                PROP_NAME => TOP_BTC_PERCENT,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TOP_BTC_FIRST_IN => [
                PROP_NAME => TOP_BTC_FIRST_IN,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TOP_BTC_LAST_IN => [
                PROP_NAME => TOP_BTC_LAST_IN,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TOP_BTC_INS => [
                PROP_NAME => TOP_BTC_INS,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TOP_BTC_FIRST_OUT => [
                PROP_NAME => TOP_BTC_FIRST_OUT,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TOP_BTC_LAST_OUT => [
                PROP_NAME => TOP_BTC_LAST_OUT,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TOP_BTC_OUTS => [
                PROP_NAME => TOP_BTC_OUTS,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],

        );

        $this->query_builder = DB::connection('coin_crawler')->table(TOP_BTC_TABLE);
        $this->id = TOP_BTC_ID;
        $this->name = TOP_BTC_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

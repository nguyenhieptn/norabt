<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Change_24h extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            CHANGE24H_ID => [
                PROP_NAME => CHANGE24H_ID,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_TIME => [
                PROP_NAME => CHANGE24H_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_TOTAL => [
                PROP_NAME => CHANGE24H_TOTAL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_DOWN => [
                PROP_NAME => CHANGE24H_DOWN,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_UP => [
                PROP_NAME => CHANGE24H_UP,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],

            CHANGE24H_UP_EMA5 => [
                PROP_NAME => CHANGE24H_UP_EMA5,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_UP_EMA9 => [
                PROP_NAME => CHANGE24H_UP_EMA9,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_UP_EMA13 => [
                PROP_NAME => CHANGE24H_UP_EMA13,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            
            CHANGE24H_KEEP => [
                PROP_NAME => CHANGE24H_KEEP,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_DOWN50 => [
                PROP_NAME => CHANGE24H_DOWN50,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_UP50 => [
                PROP_NAME => CHANGE24H_UP50,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_UP50_EMA5 => [
                PROP_NAME => CHANGE24H_UP50_EMA5,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_UP50_EMA9 => [
                PROP_NAME => CHANGE24H_UP50_EMA9,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_UP50_EMA13 => [
                PROP_NAME => CHANGE24H_UP50_EMA13,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_KEEP50 => [
                PROP_NAME => CHANGE24H_KEEP50,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_BTC_ASC => [
                PROP_NAME => CHANGE24H_BTC_ASC,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_BTC_DESC => [
                PROP_NAME => CHANGE24H_BTC_DESC,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_BTC_CHANGE => [
                PROP_NAME => CHANGE24H_BTC_CHANGE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_BTC_KEEP => [
                PROP_NAME => CHANGE24H_BTC_KEEP,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_UP_10 => [
                PROP_NAME => CHANGE24H_UP_10,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_UP_7_10 => [
                PROP_NAME => CHANGE24H_UP_7_10,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_UP_5_7 => [
                PROP_NAME => CHANGE24H_UP_5_7,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_UP_3_5 => [
                PROP_NAME => CHANGE24H_UP_3_5,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_UP_0_3 => [
                PROP_NAME => CHANGE24H_UP_0_3,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_DOWN_0_3 => [
                PROP_NAME => CHANGE24H_DOWN_0_3,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_DOWN_3_5 => [
                PROP_NAME => CHANGE24H_DOWN_3_5,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_DOWN_5_7 => [
                PROP_NAME => CHANGE24H_DOWN_5_7,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_DOWN_7_10 => [
                PROP_NAME => CHANGE24H_DOWN_7_10,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_DOWN_10 => [
                PROP_NAME => CHANGE24H_DOWN_10,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_DATA => [
                PROP_NAME => CHANGE24H_DATA,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_5M_UP => [
                PROP_NAME => CHANGE24H_5M_UP,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_5M_DOWN => [
                PROP_NAME => CHANGE24H_5M_DOWN,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_15M_UP => [
                PROP_NAME => CHANGE24H_15M_UP,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_15M_DOWN => [
                PROP_NAME => CHANGE24H_15M_DOWN,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_1H_UP => [
                PROP_NAME => CHANGE24H_1H_UP,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_1H_DOWN => [
                PROP_NAME => CHANGE24H_1H_DOWN,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_4H_UP => [
                PROP_NAME => CHANGE24H_4H_UP,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CHANGE24H_4H_DOWN => [
                PROP_NAME => CHANGE24H_4H_DOWN,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            
            

        );

        $this->query_builder = DB::table(CHANGE_24H_TABLE);
        $this->id = CHANGE24H_ID;
        $this->name = CHANGE_24H_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

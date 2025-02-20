<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Strategy_container extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            STRA_CON_ID => [
                PROP_NAME => STRA_CON_ID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            STRA_CON_CONTAINER => [
                PROP_NAME => STRA_CON_CONTAINER,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            STRA_CON_CHILD => [
                PROP_NAME => STRA_CON_CHILD,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            STRA_CON_WEIGHT => [
                PROP_NAME => STRA_CON_WEIGHT,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            STRA_CON_SLOT => [
                PROP_NAME => STRA_CON_SLOT,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            STRA_CON_BLACKLIST => [
                PROP_NAME => STRA_CON_BLACKLIST,
                PROP_NULL => true,
                PROP_REGEX => "Json",
            ],

        );

        $this->query_builder = DB::table(STRATEGY_CONTAINER_TABLE);
        $this->id = STRA_CON_ID;
        $this->name = STRATEGY_CONTAINER_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

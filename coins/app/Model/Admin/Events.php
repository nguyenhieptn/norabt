<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Events extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            EVENT_ID => [
                PROP_NAME => EVENT_ID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            EVENT_SYMBOL => [
                PROP_NAME => EVENT_SYMBOL,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            EVENT_TIME => [
                PROP_NAME => EVENT_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            EVENT_CHART => [
                PROP_NAME => EVENT_CHART,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            EVENT_PRICE => [
                PROP_NAME => EVENT_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            EVENT_TYPE => [
                PROP_NAME => EVENT_TYPE,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            EVENT_BASE => [
                PROP_NAME => EVENT_BASE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            EVENT_PARAMS => [
                PROP_NAME => EVENT_PARAMS,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],

        );

        $this->query_builder = DB::table(EVENTS_TABLE);
        $this->id = EVENT_ID;
        $this->name = EVENTS_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

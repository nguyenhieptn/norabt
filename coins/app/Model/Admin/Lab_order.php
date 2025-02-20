<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Lab_order extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            LAB_ORDER_ID => [
                PROP_NAME => LAB_ORDER_ID,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_ORDER_TIME => [
                PROP_NAME => LAB_ORDER_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_ORDER_ACTION => [
                PROP_NAME => LAB_ORDER_ACTION,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_ORDER_SYMBOL => [
                PROP_NAME => LAB_ORDER_SYMBOL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_ORDER_QTY => [
                PROP_NAME => LAB_ORDER_QTY,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_ORDER_PRICE => [
                PROP_NAME => LAB_ORDER_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_ORDER_BASEON => [
                PROP_NAME => LAB_ORDER_BASEON,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_ORDER_TYPE => [
                PROP_NAME => LAB_ORDER_TYPE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_ORDER_PHASE => [
                PROP_NAME => LAB_ORDER_PHASE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_ORDER_COMMIT => [
                PROP_NAME => LAB_ORDER_COMMIT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_ORDER_PNL => [
                PROP_NAME => LAB_ORDER_PNL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_ORDER_ACCOUNT => [
                PROP_NAME => LAB_ORDER_ACCOUNT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],

        );

        $this->query_builder = DB::connection('lab')->table(LAB_ORDER_TABLE);
        $this->id = LAB_ORDER_ID;
        $this->name = LAB_ORDER_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

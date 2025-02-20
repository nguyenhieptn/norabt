<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Orders extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            ORDER_ID => [
                PROP_NAME => ORDER_ID,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_BINANCE => [
                PROP_NAME => ORDER_BINANCE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_ACCOUNT => [
                PROP_NAME => ORDER_ACCOUNT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_TIME => [
                PROP_NAME => ORDER_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_SYMBOL => [
                PROP_NAME => ORDER_SYMBOL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_ACTION => [
                PROP_NAME => ORDER_ACTION,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_TYPE => [
                PROP_NAME => ORDER_TYPE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_SIDE => [
                PROP_NAME => ORDER_SIDE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_PRICE => [
                PROP_NAME => ORDER_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_STOP_PRICE => [
                PROP_NAME => ORDER_STOP_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_STATUS => [
                PROP_NAME => ORDER_STATUS,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_QTY => [
                PROP_NAME => ORDER_QTY,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_PNL => [
                PROP_NAME => ORDER_PNL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_COMMIT => [
                PROP_NAME => ORDER_COMMIT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_DATA => [
                PROP_NAME => ORDER_DATA,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],

        );

        $this->query_builder = DB::connection('binance')->table(ORDERS_TABLE);
        $this->id = ORDER_ID;
        $this->name = ORDERS_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

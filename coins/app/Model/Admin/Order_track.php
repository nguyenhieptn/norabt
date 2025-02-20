<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Order_track extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            ORDER_TRACK_ID => [
                PROP_NAME => ORDER_TRACK_ID,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_TRACK_SYMBOL => [
                PROP_NAME => ORDER_TRACK_SYMBOL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_TRACK_PRICE => [
                PROP_NAME => ORDER_TRACK_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_TRACK_LOW => [
                PROP_NAME => ORDER_TRACK_LOW,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_TRACK_HIGH => [
                PROP_NAME => ORDER_TRACK_HIGH,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_TRACK_UP => [
                PROP_NAME => ORDER_TRACK_UP,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_TRACK_DOWN => [
                PROP_NAME => ORDER_TRACK_DOWN,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_TRACK_CLOSE => [
                PROP_NAME => ORDER_TRACK_CLOSE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_TRACK_CHANGE => [
                PROP_NAME => ORDER_TRACK_CHANGE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_TRACK_1H_UP => [
                PROP_NAME => ORDER_TRACK_1H_UP,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_TRACK_1H_DOWN => [
                PROP_NAME => ORDER_TRACK_1H_DOWN,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_TRACK_15M_UP => [
                PROP_NAME => ORDER_TRACK_15M_UP,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_TRACK_15M_DOWN => [
                PROP_NAME => ORDER_TRACK_15M_DOWN,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_TRACK_3M_UP => [
                PROP_NAME => ORDER_TRACK_3M_UP,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_TRACK_3M_DOWN => [
                PROP_NAME => ORDER_TRACK_3M_DOWN,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_TRACK_RSI4H_0 => [
                PROP_NAME => ORDER_TRACK_RSI4H_0,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_TRACK_RSI4H_1 => [
                PROP_NAME => ORDER_TRACK_RSI4H_1,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_TRACK_RSI1H_0 => [
                PROP_NAME => ORDER_TRACK_RSI1H_0,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_TRACK_RSI1H_1 => [
                PROP_NAME => ORDER_TRACK_RSI1H_1,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_TRACK_RSI_EMA9 => [
                PROP_NAME => ORDER_TRACK_RSI_EMA9,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_TRACK_1D_RSI_WMA => [
                PROP_NAME => ORDER_TRACK_1D_RSI_WMA,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_TRACK_1W_RSI_WMA => [
                PROP_NAME => ORDER_TRACK_1W_RSI_WMA,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_TRACK_1D_UP => [
                PROP_NAME => ORDER_TRACK_1D_UP,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            ORDER_TRACK_1D_DOWN => [
                PROP_NAME => ORDER_TRACK_1D_DOWN,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],

        );

        $this->query_builder = DB::table(ORDER_TRACK_TABLE);
        $this->id = ORDER_TRACK_ID;
        $this->name = ORDER_TRACK_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Testnet_order extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            TESTNET_ORDER_ID => [
                PROP_NAME => TESTNET_ORDER_ID,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_ORDER_ACCOUNT => [
                PROP_NAME => TESTNET_ORDER_ACCOUNT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_ORDER_TIME => [
                PROP_NAME => TESTNET_ORDER_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_ORDER_ACTION => [
                PROP_NAME => TESTNET_ORDER_ACTION,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_ORDER_SYMBOL => [
                PROP_NAME => TESTNET_ORDER_SYMBOL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_ORDER_QTY => [
                PROP_NAME => TESTNET_ORDER_QTY,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_ORDER_PRICE => [
                PROP_NAME => TESTNET_ORDER_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_ORDER_BASEON => [
                PROP_NAME => TESTNET_ORDER_BASEON,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_ORDER_TYPE => [
                PROP_NAME => TESTNET_ORDER_TYPE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_ORDER_PHASE => [
                PROP_NAME => TESTNET_ORDER_PHASE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_ORDER_COMMIT => [
                PROP_NAME => TESTNET_ORDER_COMMIT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_ORDER_PNL => [
                PROP_NAME => TESTNET_ORDER_PNL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],

        );

        $this->query_builder = DB::table(TESTNET_ORDER_TABLE);
        $this->id = TESTNET_ORDER_ID;
        $this->name = TESTNET_ORDER_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

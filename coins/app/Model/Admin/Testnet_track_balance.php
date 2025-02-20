<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Testnet_track_balance extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            TESTNET_TRACK_BL_ID => [
                PROP_NAME => TESTNET_TRACK_BL_ID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TESTNET_TRACK_BL_ACCOUNT => [
                PROP_NAME => TESTNET_TRACK_BL_ACCOUNT,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TESTNET_TRACK_BL_TIME => [
                PROP_NAME => TESTNET_TRACK_BL_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TESTNET_TRACK_BL_MARGIN_BL => [
                PROP_NAME => TESTNET_TRACK_BL_MARGIN_BL,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            TESTNET_TRACK_BL_INVEST => [
                PROP_NAME => TESTNET_TRACK_BL_INVEST,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            TESTNET_TRACK_BL_UNREALIZE => [
                PROP_NAME => TESTNET_TRACK_BL_UNREALIZE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            TESTNET_TRACK_BL_BALANCE => [
                PROP_NAME => TESTNET_TRACK_BL_BALANCE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],

        );

        $this->query_builder = DB::table(TESTNET_TRACK_BALANCE_TABLE);
        $this->id = TESTNET_TRACK_BL_ID;
        $this->name = TESTNET_TRACK_BALANCE_TABLE;

        $this->registerSql = [
            // ['Admin/Testnet_campaign', TESTNET_ACCOUNT_ID, TESTNET_ACCOUNT, null, null, 'deny', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

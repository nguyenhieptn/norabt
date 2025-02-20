<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Binance_track_balance extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            BINANCE_TRACK_BL_ID => [
                PROP_NAME => BINANCE_TRACK_BL_ID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            BINANCE_TRACK_BL_ACCOUNT => [
                PROP_NAME => BINANCE_TRACK_BL_ACCOUNT,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            BINANCE_TRACK_BL_TIME => [
                PROP_NAME => BINANCE_TRACK_BL_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            BINANCE_TRACK_BL_MARGIN_BL => [
                PROP_NAME => BINANCE_TRACK_BL_MARGIN_BL,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            BINANCE_TRACK_BL_INVEST => [
                PROP_NAME => BINANCE_TRACK_BL_INVEST,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            BINANCE_TRACK_BL_UNREALIZE => [
                PROP_NAME => BINANCE_TRACK_BL_UNREALIZE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            BINANCE_TRACK_BL_BALANCE => [
                PROP_NAME => BINANCE_TRACK_BL_BALANCE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],



        );

        $this->query_builder = DB::connection('binance')->table(BINANCE_TRACK_BALANCE_TABLE);
        $this->id = BINANCE_TRACK_BL_ID;
        $this->name = BINANCE_TRACK_BALANCE_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

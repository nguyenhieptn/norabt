<?php

namespace App\Model\Crawler;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Liquidation extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            LIQUIDATION_ID => [
                PROP_NAME => LIQUIDATION_ID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LIQUIDATION_TIME => [
                PROP_NAME => LIQUIDATION_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LIQUIDATION_PRICE => [
                PROP_NAME => LIQUIDATION_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            LIQUIDATION_BUYVOLUSD => [
                PROP_NAME => LIQUIDATION_BUYVOLUSD,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            LIQUIDATION_SELLVOLUSD => [
                PROP_NAME => LIQUIDATION_SELLVOLUSD,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],

        );

        $this->query_builder = DB::connection('coin_crawler')->table(LIQUIDATIONS_TABLE);
        $this->id = LIQUIDATION_ID;
        $this->name = LIQUIDATIONS_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

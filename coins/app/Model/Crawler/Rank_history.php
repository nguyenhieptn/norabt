<?php

namespace App\Model\Crawler;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Rank_history extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            RANK_HIS_ID => [
                PROP_NAME => RANK_HIS_ID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            RANK_HIS_YEAR => [
                PROP_NAME => RANK_HIS_YEAR,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            RANK_HIS_TIME => [
                PROP_NAME => RANK_HIS_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            RANK_HIS_SYMBOL => [
                PROP_NAME => RANK_HIS_SYMBOL,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            RANK_HIS_VALUE => [
                PROP_NAME => RANK_HIS_VALUE,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            RANK_HIS_MARKET_CAP => [
                PROP_NAME => RANK_HIS_MARKET_CAP,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            RANK_HIS_PRICE => [
                PROP_NAME => RANK_HIS_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            RANK_HIS_VOLUME_24H => [
                PROP_NAME => RANK_HIS_VOLUME_24H,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],

        );

        $this->query_builder = DB::connection('coin_crawler')->table(RANK_HISTORY_TABLE);
        $this->id = RANK_HIS_ID;
        $this->name = RANK_HISTORY_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

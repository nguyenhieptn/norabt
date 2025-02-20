<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class CoinMarket extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            COINMARKET_ID => [
                PROP_NAME => COINMARKET_ID,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            COINMARKET_SYMBOL => [
                PROP_NAME => COINMARKET_SYMBOL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            COINMARKET_PRICE => [
                PROP_NAME => COINMARKET_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            COINMARKET_PERCENT_CHANGE_1H => [
                PROP_NAME => COINMARKET_PERCENT_CHANGE_1H,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            COINMARKET_PERCENT_CHANGE_24H => [
                PROP_NAME => COINMARKET_PERCENT_CHANGE_24H,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            COINMARKET_PERCENT_CHANGE_7D => [
                PROP_NAME => COINMARKET_PERCENT_CHANGE_7D,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            COINMARKET_PERCENT_CHANGE_30D => [
                PROP_NAME => COINMARKET_PERCENT_CHANGE_30D,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            COINMARKET_MARKET_CAP => [
                PROP_NAME => COINMARKET_MARKET_CAP,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            COINMARKET_VOLUME_24H => [
                PROP_NAME => COINMARKET_VOLUME_24H,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            COINMARKET_RANK => [
                PROP_NAME => COINMARKET_RANK,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            COINMARKET_LAST_UPDATED => [
                PROP_NAME => COINMARKET_LAST_UPDATED,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
          
           
        );
        $this->query_builder = DB::table(COINMARKET_TABLE);
        $this->id = COINMARKET_ID;
        $this->name = COINMARKET_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

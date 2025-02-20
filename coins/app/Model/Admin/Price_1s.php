<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Price_1s extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            PRICE_1S_ID => [
                PROP_NAME => PRICE_1S_ID,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            PRICE_1S_SYMBOL => [
                PROP_NAME => PRICE_1S_SYMBOL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            PRICE_1S_TIME => [
                PROP_NAME => PRICE_1S_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            PRICE_1S_CLOSE => [
                PROP_NAME => PRICE_1S_CLOSE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            PRICE_1S_LOW => [
                PROP_NAME => PRICE_1S_LOW,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            PRICE_1S_HIGH => [
                PROP_NAME => PRICE_1S_HIGH,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            PRICE_1S_OPEN => [
                PROP_NAME => PRICE_1S_OPEN,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            PRICE_1S_OPEN_TIME => [
                PROP_NAME => PRICE_1S_OPEN_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            PRICE_1S_CLOSE_TIME => [
                PROP_NAME => PRICE_1S_CLOSE_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],

        );

        $this->query_builder = DB::connection('coin_chart')->table(PRICE_1S_TABLE);
        $this->id = PRICE_1S_ID;
        $this->name = PRICE_1S_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

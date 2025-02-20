<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Volatility extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            VOLATILITY_ID => [
                PROP_NAME => VOLATILITY_ID,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_SYMBOL => [
                PROP_NAME => VOLATILITY_SYMBOL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_TIME => [
                PROP_NAME => VOLATILITY_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_1D_HIGH_LOW_AVG3D_VALUE => [
                PROP_NAME => VOLATILITY_1D_HIGH_LOW_AVG3D_VALUE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_1D_HIGH_HIGH_AVG3D_VALUE => [
                PROP_NAME => VOLATILITY_1D_HIGH_HIGH_AVG3D_VALUE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_1D_LOW_LOW_AVG3D_VALUE => [
                PROP_NAME => VOLATILITY_1D_LOW_LOW_AVG3D_VALUE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_1D_HIGH_LOW_AVG7D_VALUE => [
                PROP_NAME => VOLATILITY_1D_HIGH_LOW_AVG7D_VALUE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_1D_HIGH_HIGH_AVG7D_VALUE => [
                PROP_NAME => VOLATILITY_1D_HIGH_HIGH_AVG7D_VALUE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_1D_LOW_LOW_AVG7D_VALUE => [
                PROP_NAME => VOLATILITY_1D_LOW_LOW_AVG7D_VALUE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_4H_HIGH_LOW_AVG3D_VALUE => [
                PROP_NAME => VOLATILITY_4H_HIGH_LOW_AVG3D_VALUE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_4H_HIGH_HIGH_AVG3D_VALUE => [
                PROP_NAME => VOLATILITY_4H_HIGH_HIGH_AVG3D_VALUE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_4H_LOW_LOW_AVG3D_VALUE => [
                PROP_NAME => VOLATILITY_4H_LOW_LOW_AVG3D_VALUE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_4H_HIGH_LOW_AVG7D_VALUE => [
                PROP_NAME => VOLATILITY_4H_HIGH_LOW_AVG7D_VALUE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_4H_HIGH_HIGH_AVG7D_VALUE => [
                PROP_NAME => VOLATILITY_4H_HIGH_HIGH_AVG7D_VALUE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_4H_LOW_LOW_AVG7D_VALUE => [
                PROP_NAME => VOLATILITY_4H_LOW_LOW_AVG7D_VALUE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_1D_HIGH_LOW_AVG3D_RANK => [
                PROP_NAME => VOLATILITY_1D_HIGH_LOW_AVG3D_RANK,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_1D_HIGH_HIGH_AVG3D_RANK => [
                PROP_NAME => VOLATILITY_1D_HIGH_HIGH_AVG3D_RANK,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_1D_LOW_LOW_AVG3D_RANK => [
                PROP_NAME => VOLATILITY_1D_LOW_LOW_AVG3D_RANK,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_1D_HIGH_LOW_AVG7D_RANK => [
                PROP_NAME => VOLATILITY_1D_HIGH_LOW_AVG7D_RANK,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_1D_HIGH_HIGH_AVG7D_RANK => [
                PROP_NAME => VOLATILITY_1D_HIGH_HIGH_AVG7D_RANK,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_1D_LOW_LOW_AVG7D_RANK => [
                PROP_NAME => VOLATILITY_1D_LOW_LOW_AVG7D_RANK,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_4H_HIGH_LOW_AVG3D_RANK => [
                PROP_NAME => VOLATILITY_4H_HIGH_LOW_AVG3D_RANK,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_4H_HIGH_HIGH_AVG3D_RANK => [
                PROP_NAME => VOLATILITY_4H_HIGH_HIGH_AVG3D_RANK,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_4H_LOW_LOW_AVG3D_RANK => [
                PROP_NAME => VOLATILITY_4H_LOW_LOW_AVG3D_RANK,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_4H_HIGH_LOW_AVG7D_RANK => [
                PROP_NAME => VOLATILITY_4H_HIGH_LOW_AVG7D_RANK,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_4H_HIGH_HIGH_AVG7D_RANK => [
                PROP_NAME => VOLATILITY_4H_HIGH_HIGH_AVG7D_RANK,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_4H_LOW_LOW_AVG7D_RANK => [
                PROP_NAME => VOLATILITY_4H_LOW_LOW_AVG7D_RANK,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],

            VOLATILITY_4H_CLOSE_LOW_AVG3D_VALUE => [
                PROP_NAME => VOLATILITY_4H_CLOSE_LOW_AVG3D_VALUE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_4H_CLOSE_LOW_AVG7D_VALUE => [
                PROP_NAME => VOLATILITY_4H_CLOSE_LOW_AVG7D_VALUE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_1D_CLOSE_LOW_AVG3D_VALUE => [
                PROP_NAME => VOLATILITY_1D_CLOSE_LOW_AVG3D_VALUE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_1D_CLOSE_LOW_AVG7D_VALUE => [
                PROP_NAME => VOLATILITY_1D_CLOSE_LOW_AVG7D_VALUE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_4H_CLOSE_LOW_AVG3D_RANK => [
                PROP_NAME => VOLATILITY_4H_CLOSE_LOW_AVG3D_RANK,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_4H_CLOSE_LOW_AVG7D_RANK => [
                PROP_NAME => VOLATILITY_4H_CLOSE_LOW_AVG7D_RANK,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_1D_CLOSE_LOW_AVG3D_RANK => [
                PROP_NAME => VOLATILITY_1D_CLOSE_LOW_AVG3D_RANK,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            VOLATILITY_1D_CLOSE_LOW_AVG7D_RANK => [
                PROP_NAME => VOLATILITY_1D_CLOSE_LOW_AVG7D_RANK,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],

        );

        $this->query_builder = DB::table(VOLATILITY_TABLE);
        $this->id = VOLATILITY_ID;
        $this->name = VOLATILITY_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

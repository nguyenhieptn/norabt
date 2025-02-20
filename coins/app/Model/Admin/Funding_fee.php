<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Funding_fee extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            FUNDING_FEE_ID => [
                PROP_NAME => FUNDING_FEE_ID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            FUNDING_FEE_ACCOUNT => [
                PROP_NAME => FUNDING_FEE_ACCOUNT,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            FUNDING_FEE_SYMBOL => [
                PROP_NAME => FUNDING_FEE_SYMBOL,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            FUNDING_FEE_INCOME => [
                PROP_NAME => FUNDING_FEE_INCOME,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            FUNDING_FEE_TIME => [
                PROP_NAME => FUNDING_FEE_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],



        );

        $this->query_builder = DB::connection('binance')->table(FUNDING_FEE_TABLE);
        $this->id = FUNDING_FEE_ID;
        $this->name = FUNDING_FEE_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

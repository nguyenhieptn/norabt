<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Finance extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            FINANCE_ID => [
                PROP_NAME => FINANCE_ID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
        
            FINANCE_NAME => [
                PROP_NAME => FINANCE_NAME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            FINANCE_CLOSE_NOW => [
                PROP_NAME => FINANCE_CLOSE_NOW,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            FINANCE_CLOSE_PREVIOUS => [
                PROP_NAME => FINANCE_CLOSE_PREVIOUS,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            FINANCE_CLOSE_TIME => [
                PROP_NAME => FINANCE_CLOSE_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
         
            FINANCE_PERCENT => [
                PROP_NAME => FINANCE_PERCENT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],

        );

        $this->query_builder =  DB::connection('coin_crawler')->table(FINANCE_TABLE);
        $this->id = FINANCE_ID;
        $this->name = FINANCE_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

<?php

namespace App\Model\Crawler;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Finance_Future extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            FIN_FU_ID => [
                PROP_NAME => FIN_FU_ID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ], 
        FIN_FU_NAME => [
                PROP_NAME => FIN_FU_NAME,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ], 
        FIN_FU_CLOSE_NOW => [
                PROP_NAME => FIN_FU_CLOSE_NOW,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ], 
        FIN_FU_CLOSE_PREVIOUS => [
                PROP_NAME => FIN_FU_CLOSE_PREVIOUS,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ], 
        FIN_FU_TIME => [
                PROP_NAME => FIN_FU_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ], 
        FIN_FU_PERCENT => [
                PROP_NAME => FIN_FU_PERCENT,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ], 
        );

        $this->query_builder = DB::connection('coin_crawler')->table(FINANCE_FUTURE_TABLE);
        $this->id = FIN_FU_ID;
        $this->name = FINANCE_FUTURE_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Lab_watchlist extends Model_basic
{
    function __construct(){
        
        parent::__construct();
        
         $this->struct = array(
                LAB_WL_ID => [
                    PROP_NAME => LAB_WL_ID,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            LAB_WL_SYMBOL => [
                    PROP_NAME => LAB_WL_SYMBOL,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            LAB_WL_TIME => [
                    PROP_NAME => LAB_WL_TIME,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            LAB_WL_STOPTIME => [
                    PROP_NAME => LAB_WL_STOPTIME,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            LAB_WL_SYM_RANK => [
                    PROP_NAME => LAB_WL_SYM_RANK,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            
        );
        
         $this->query_builder = DB::connection('lab')->table(LAB_WATCHLIST_TABLE);
        $this->id = LAB_WL_ID;
        $this->name = LAB_WATCHLIST_TABLE;

        $this->registerSql = [
            ['Admin/Lab_candle_1h', LAB_WL_SYMBOL, LAB_CANDLE_1H_SYMBOL, null, null, 'cascade', null],
            ['Admin/Lab_candle_3m', LAB_WL_SYMBOL, LAB_CANDLE_3M_SYMBOL, null, null, 'cascade', null],
            ['Admin/Lab_candle_15m', LAB_WL_SYMBOL, LAB_CANDLE_15M_SYMBOL, null, null, 'cascade', null],
            ['Admin/Lab_candle_1m', LAB_WL_SYMBOL, LAB_CANDLE_1M_SYMBOL, null, null, 'cascade', null],
            ['Admin/Lab_campaigns', LAB_WL_SYMBOL, LAB_CAMPAIGN_SYMBOL, null, null, 'deny', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}
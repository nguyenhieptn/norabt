<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Log_profitbase extends Model_basic
{
    function __construct(){
        
        parent::__construct();
        
         $this->struct = array(
                LOG_PROFITBASE_ID => [
                    PROP_NAME => LOG_PROFITBASE_ID,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            LOG_PROFITBASE_CAMPAIGN => [
                    PROP_NAME => LOG_PROFITBASE_CAMPAIGN,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            LOG_PROFITBASE_SYMBOL => [
                    PROP_NAME => LOG_PROFITBASE_SYMBOL,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            LOG_PROFITBASE_ACTION => [
                    PROP_NAME => LOG_PROFITBASE_ACTION,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            LOG_PROFITBASE_TIME => [
                    PROP_NAME => LOG_PROFITBASE_TIME,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            LOG_PROFITBASE_PRICE => [
                    PROP_NAME => LOG_PROFITBASE_PRICE,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            LOG_PROFITBASE_VALUE => [
                    PROP_NAME => LOG_PROFITBASE_VALUE,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            LOG_PROFITBASE_EVENT => [
                    PROP_NAME => LOG_PROFITBASE_EVENT,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            
        );
        
        $this->query_builder =  DB::connection('binance')->table(LOG_PROFITBASE_TABLE);
        $this->id = LOG_PROFITBASE_ID;
        $this->name = LOG_PROFITBASE_TABLE;
        
        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];
        
        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
        
       
    }
    
   
    
}
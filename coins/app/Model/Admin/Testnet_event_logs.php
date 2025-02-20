<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Testnet_event_logs extends Model_basic
{
    function __construct(){
        
        parent::__construct();
        
         $this->struct = array(
                TESTNET_ELOG_ID => [
                    PROP_NAME => TESTNET_ELOG_ID,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            TESTNET_ELOG_CAMPAIGN => [
                    PROP_NAME => TESTNET_ELOG_CAMPAIGN,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            TESTNET_ELOG_SYMBOL => [
                    PROP_NAME => TESTNET_ELOG_SYMBOL,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            TESTNET_ELOG_TIME => [
                    PROP_NAME => TESTNET_ELOG_TIME,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            TESTNET_ELOG_CHART => [
                    PROP_NAME => TESTNET_ELOG_CHART,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            TESTNET_ELOG_RESULT => [
                    PROP_NAME => TESTNET_ELOG_RESULT,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            TESTNET_ELOG_MAXPROFIT => [
                    PROP_NAME => TESTNET_ELOG_MAXPROFIT,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            TESTNET_ELOG_MINPROFIT => [
                    PROP_NAME => TESTNET_ELOG_MINPROFIT,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            TESTNET_ELOG_PROFIT => [
                    PROP_NAME => TESTNET_ELOG_PROFIT,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            TESTNET_ELOG_BASEPROFIT => [
                    PROP_NAME => TESTNET_ELOG_BASEPROFIT,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            TESTNET_ELOG_STATUS => [
                    PROP_NAME => TESTNET_ELOG_STATUS,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            TESTNET_ELOG_MATCHED => [
                    PROP_NAME => TESTNET_ELOG_MATCHED,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            TESTNET_ELOG_BASE => [
                    PROP_NAME => TESTNET_ELOG_BASE,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            
        );
        
        $this->query_builder = DB::table(TESTNET_EVENT_LOGS_TABLE);
        $this->id = TESTNET_ELOG_ID;
        $this->name = TESTNET_EVENT_LOGS_TABLE;
        
        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];
        
        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
        
       
    }
    
   
    
}
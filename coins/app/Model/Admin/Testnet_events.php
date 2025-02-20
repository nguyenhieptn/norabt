<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Testnet_events extends Model_basic
{
    function __construct(){
        
        parent::__construct();
        
         $this->struct = array(
                TESTNET_EVENTS_ID => [
                    PROP_NAME => TESTNET_EVENTS_ID,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            TESTNET_EVENTS_SYMBOL => [
                    PROP_NAME => TESTNET_EVENTS_SYMBOL,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            TESTNET_EVENTS_TIME => [
                    PROP_NAME => TESTNET_EVENTS_TIME,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            TESTNET_EVENTS_ICON => [
                    PROP_NAME => TESTNET_EVENTS_ICON,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            TESTNET_EVENTS_PROFIT => [
                    PROP_NAME => TESTNET_EVENTS_PROFIT,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            TESTNET_EVENTS_CONTENT => [
                    PROP_NAME => TESTNET_EVENTS_CONTENT,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            TESTNET_EVENTS_STRATEGY => [
                    PROP_NAME => TESTNET_EVENTS_STRATEGY,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            TESTNET_EVENTS_CAMPAIGN => [
                    PROP_NAME => TESTNET_EVENTS_CAMPAIGN,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            
        );
        
        $this->query_builder = DB::table(TESTNET_EVENTS_TABLE);
        $this->id = TESTNET_EVENTS_ID;
        $this->name = TESTNET_EVENTS_TABLE;
        
        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];
        
        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
        
       
    }
    
   
    
}
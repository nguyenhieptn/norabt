<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Testnet_enterbase extends Model_basic
{
    function __construct(){
        
        parent::__construct();
        
         $this->struct = array(
                ENTERBASE_ID => [
                    PROP_NAME => ENTERBASE_ID,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            ENTERBASE_CAMPAIGN => [
                    PROP_NAME => ENTERBASE_CAMPAIGN,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            ENTERBASE_SYMBOL => [
                    PROP_NAME => ENTERBASE_SYMBOL,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            ENTERBASE_ACTION => [
                    PROP_NAME => ENTERBASE_ACTION,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            ENTERBASE_TIME => [
                    PROP_NAME => ENTERBASE_TIME,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            ENTERBASE_PRICE => [
                    PROP_NAME => ENTERBASE_PRICE,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            ENTERBASE_VALUE => [
                    PROP_NAME => ENTERBASE_VALUE,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            ENTERBASE_EVENT => [
                    PROP_NAME => ENTERBASE_EVENT,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            
        );
        
        $this->query_builder = DB::table(TESTNET_ENTERBASE_TABLE);
        $this->id = ENTERBASE_ID;
        $this->name = TESTNET_ENTERBASE_TABLE;
        
        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];
        
        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
        
       
    }
    
   
    
}
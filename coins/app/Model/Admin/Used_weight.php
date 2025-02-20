<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Used_weight extends Model_basic
{
    function __construct(){
        
        parent::__construct();
        
         $this->struct = array(
                USED_W_ID => [
                    PROP_NAME => USED_W_ID,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            USED_W_DOMAIN => [
                    PROP_NAME => USED_W_DOMAIN,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            USED_W_URL => [
                    PROP_NAME => USED_W_URL,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            USED_W_VALUE => [
                    PROP_NAME => USED_W_VALUE,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            USED_W_TIME => [
                    PROP_NAME => USED_W_TIME,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            
        );
        
        $this->query_builder = DB::connection('binance')->table(USED_WEIGHT_TABLE);
        $this->id = USED_W_ID;
        $this->name = USED_WEIGHT_TABLE;
        
        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];
        
        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
        
       
    }
    
   
    
}
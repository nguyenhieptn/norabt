<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Lab_strategy_container extends Model_basic
{
    function __construct(){
        
        parent::__construct();
        
         $this->struct = array(
                LAB_STRA_CON_ID => [
                    PROP_NAME => LAB_STRA_CON_ID,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            LAB_STRA_CON_CONTAINER => [
                    PROP_NAME => LAB_STRA_CON_CONTAINER,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            LAB_STRA_CON_CHILD => [
                    PROP_NAME => LAB_STRA_CON_CHILD,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            LAB_STRA_CON_WEIGHT => [
                    PROP_NAME => LAB_STRA_CON_WEIGHT,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            LAB_STRA_CON_SLOT => [
                    PROP_NAME => LAB_STRA_CON_SLOT,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            LAB_STRA_CON_BLACKLIST => [
                    PROP_NAME => LAB_STRA_CON_BLACKLIST,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            
        );
        
        $this->query_builder = DB::connection('lab')->table(LAB_STRATEGY_CONTAINER_TABLE);
        $this->id = LAB_STRA_CON_ID;
        $this->name = LAB_STRATEGY_CONTAINER_TABLE;
        
        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];
        
        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
        
       
    }
    
   
    
}
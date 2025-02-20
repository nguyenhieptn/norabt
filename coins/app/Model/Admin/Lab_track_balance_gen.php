<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Lab_track_balance_gen extends Model_basic
{
    function __construct(){
        
        parent::__construct();
        
         $this->struct = array(
            LAB_TRACK_BALANCE_GEN_ID => [
                PROP_NAME => LAB_TRACK_BALANCE_GEN_ID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ], 
        LAB_TRACK_BALANCE_GEN_ACCOUNT => [
                PROP_NAME => LAB_TRACK_BALANCE_GEN_ACCOUNT,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ], 
       
       
        
        LAB_TRACK_BALANCE_GEN_TOP20FL => [
                PROP_NAME => LAB_TRACK_BALANCE_GEN_TOP20FL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ], 
        LAB_TRACK_BALANCE_GEN_FLAGSL => [
                PROP_NAME => LAB_TRACK_BALANCE_GEN_FLAGSL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ], 
        LAB_TRACK_BALANCE_GEN_MAX_INVEST => [
                PROP_NAME => LAB_TRACK_BALANCE_GEN_MAX_INVEST,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ], 
        LAB_TRACK_BALANCE_GEN_MAX_DRAWDOWN => [
                PROP_NAME => LAB_TRACK_BALANCE_GEN_MAX_DRAWDOWN,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ], 
        LAB_TRACK_BALANCE_GEN_DD => [
                PROP_NAME => LAB_TRACK_BALANCE_GEN_DD,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ], 
        LAB_TRACK_BALANCE_GEN_MI => [
                PROP_NAME => LAB_TRACK_BALANCE_GEN_MI,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ], 
        LAB_TRACK_BALANCE_GEN_SL => [
                PROP_NAME => LAB_TRACK_BALANCE_GEN_SL,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ], 
        LAB_TRACK_BALANCE_GEN_MD => [
                PROP_NAME => LAB_TRACK_BALANCE_GEN_MD,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ], 
     
            
        );
        
        $this->query_builder = DB::connection('lab')->table(LAB_TRACK_BALANCE_GEN_TABLE);
        $this->id = LAB_TRACK_BALANCE_GEN_ID;
        $this->name = LAB_TRACK_BALANCE_GEN_TABLE;
        
        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];
        
        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
        
       
    }
    
   
    
}


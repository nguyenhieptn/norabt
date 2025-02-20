<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Volatility_history extends Model_basic
{
    function __construct(){
        
        parent::__construct();
        
         $this->struct = array(
                VOLATILITY_ID => [
                    PROP_NAME => VOLATILITY_ID,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            VOLATILITY_SYMBOL => [
                    PROP_NAME => VOLATILITY_SYMBOL,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            VOLATILITY_TIME => [
                    PROP_NAME => VOLATILITY_TIME,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            VOLATILITY_4H_HIGHLOW_T0_VALUE => [
                    PROP_NAME => VOLATILITY_4H_HIGHLOW_T0_VALUE,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            VOLATILITY_4H_HIGHLOW_T1_VALUE => [
                    PROP_NAME => VOLATILITY_4H_HIGHLOW_T1_VALUE,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            VOLATILITY_4H_HIGHLOW_T2_VALUE => [
                    PROP_NAME => VOLATILITY_4H_HIGHLOW_T2_VALUE,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            VOLATILITY_4H_HIGHHIGH_T0_VALUE => [
                    PROP_NAME => VOLATILITY_4H_HIGHHIGH_T0_VALUE,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            VOLATILITY_4H_HIGHHIGH_T1_VALUE => [
                    PROP_NAME => VOLATILITY_4H_HIGHHIGH_T1_VALUE,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            VOLATILITY_4H_HIGHHIGH_T2_VALUE => [
                    PROP_NAME => VOLATILITY_4H_HIGHHIGH_T2_VALUE,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            VOLATILITY_1D_HIGHLOW_T0_VALUE => [
                    PROP_NAME => VOLATILITY_1D_HIGHLOW_T0_VALUE,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            VOLATILITY_1D_HIGHLOW_T1_VALUE => [
                    PROP_NAME => VOLATILITY_1D_HIGHLOW_T1_VALUE,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            VOLATILITY_1D_HIGHLOW_T2_VALUE => [
                    PROP_NAME => VOLATILITY_1D_HIGHLOW_T2_VALUE,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            VOLATILITY_1D_HIGHHIGH_T0_VALUE => [
                    PROP_NAME => VOLATILITY_1D_HIGHHIGH_T0_VALUE,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            VOLATILITY_1D_HIGHHIGH_T1_VALUE => [
                    PROP_NAME => VOLATILITY_1D_HIGHHIGH_T1_VALUE,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            VOLATILITY_1D_HIGHHIGH_T2_VALUE => [
                    PROP_NAME => VOLATILITY_1D_HIGHHIGH_T2_VALUE,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            VOLATILITY_4H_HIGHLOW_T0_RANK => [
                    PROP_NAME => VOLATILITY_4H_HIGHLOW_T0_RANK,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            VOLATILITY_4H_HIGHLOW_T1_RANK => [
                    PROP_NAME => VOLATILITY_4H_HIGHLOW_T1_RANK,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            VOLATILITY_4H_HIGHLOW_T2_RANK => [
                    PROP_NAME => VOLATILITY_4H_HIGHLOW_T2_RANK,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            VOLATILITY_4H_HIGHHIGH_T0_RANK => [
                    PROP_NAME => VOLATILITY_4H_HIGHHIGH_T0_RANK,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            VOLATILITY_4H_HIGHHIGH_T1_RANK => [
                    PROP_NAME => VOLATILITY_4H_HIGHHIGH_T1_RANK,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            VOLATILITY_4H_HIGHHIGH_T2_RANK => [
                    PROP_NAME => VOLATILITY_4H_HIGHHIGH_T2_RANK,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            VOLATILITY_1D_HIGHLOW_T0_RANK => [
                    PROP_NAME => VOLATILITY_1D_HIGHLOW_T0_RANK,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            VOLATILITY_1D_HIGHLOW_T1_RANK => [
                    PROP_NAME => VOLATILITY_1D_HIGHLOW_T1_RANK,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            VOLATILITY_1D_HIGHLOW_T2_RANK => [
                    PROP_NAME => VOLATILITY_1D_HIGHLOW_T2_RANK,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            VOLATILITY_1D_HIGHHIGH_T0_RANK => [
                    PROP_NAME => VOLATILITY_1D_HIGHHIGH_T0_RANK,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            VOLATILITY_1D_HIGHHIGH_T1_RANK => [
                    PROP_NAME => VOLATILITY_1D_HIGHHIGH_T1_RANK,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            VOLATILITY_1D_HIGHHIGH_T2_RANK => [
                    PROP_NAME => VOLATILITY_1D_HIGHHIGH_T2_RANK,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            
        );
        
        $this->query_builder = DB::table(VOLATILITY_HISTORY_TABLE);
        $this->id = VOLATILITY_ID;
        $this->name = VOLATILITY_HISTORY_TABLE;
        
        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];
        
        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
        
       
    }
    
   
    
}
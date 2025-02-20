<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Params extends Model_basic
{
    function __construct(){
        
        parent::__construct();
        
         $this->struct = array(
                PARAM_ID => [
                    PROP_NAME => PARAM_ID,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            PARAM_NAME => [
                    PROP_NAME => PARAM_NAME,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            PARAM_TIMELIFE => [
                    PROP_NAME => PARAM_TIMELIFE,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            PARAM_TAKEPROFIT => [
                    PROP_NAME => PARAM_TAKEPROFIT,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            PARAM_BASEPROFIT => [
                    PROP_NAME => PARAM_BASEPROFIT,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            PARAM_STEPPROFIT => [
                    PROP_NAME => PARAM_STEPPROFIT,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            PARAM_TOPLOSS => [
                    PROP_NAME => PARAM_TOPLOSS,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            PARAM_MARGIN => [
                    PROP_NAME => PARAM_MARGIN,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            
        );
        
        $this->query_builder = DB::connection('binance')->table(PARAMS_TABLE);
        $this->id = PARAM_ID;
        $this->name = PARAMS_TABLE;
        
        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];
        
        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
        
       
    }
    
   
    
}
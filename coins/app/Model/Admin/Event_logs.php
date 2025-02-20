<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Event_logs extends Model_basic
{
    function __construct(){
        
        parent::__construct();
        
         $this->struct = array(
                ELOG_ID => [
                    PROP_NAME => ELOG_ID,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            ELOG_SYMBOL => [
                    PROP_NAME => ELOG_SYMBOL,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            ELOG_TIME => [
                    PROP_NAME => ELOG_TIME,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            ELOG_CHART => [
                    PROP_NAME => ELOG_CHART,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            ELOG_RESULT => [
                    PROP_NAME => ELOG_RESULT,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            ELOG_MATCHED => [
                    PROP_NAME => ELOG_MATCHED,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            ELOG_BASE => [
                    PROP_NAME => ELOG_BASE,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            
        );
        
        $this->query_builder = DB::table(EVENT_LOGS_TABLE);
        $this->id = ELOG_ID;
        $this->name = EVENT_LOGS_TABLE;
        
        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];
        
        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
        
       
    }
    
   
    
}
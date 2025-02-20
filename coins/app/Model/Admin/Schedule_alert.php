<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Schedule_alert extends Model_basic
{
    function __construct(){
        
        parent::__construct();
        
         $this->struct = array(
                SCHEDULE_AL_ID => [
                    PROP_NAME => SCHEDULE_AL_ID,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            SCHEDULE_AL_NAME => [
                    PROP_NAME => SCHEDULE_AL_NAME,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            SCHEDULE_AL_GROUPID => [
                    PROP_NAME => SCHEDULE_AL_GROUPID,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            SCHEDULE_AL_BOTID => [
                    PROP_NAME => SCHEDULE_AL_BOTID,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            SCHEDULE_AL_ICON => [
                    PROP_NAME => SCHEDULE_AL_ICON,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            SCHEDULE_AL_TIME => [
                    PROP_NAME => SCHEDULE_AL_TIME,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            SCHEDULE_AL_CONTENT => [
                    PROP_NAME => SCHEDULE_AL_CONTENT,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            SCHEDULE_AL_BEFORE => [
                    PROP_NAME => SCHEDULE_AL_BEFORE,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            SCHEDULE_AL_NOTE => [
                    PROP_NAME => SCHEDULE_AL_NOTE,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            SCHEDULE_AL_DONE => [
                    PROP_NAME => SCHEDULE_AL_DONE,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            
        );
        
        $this->query_builder = DB::table(SCHEDULE_ALERT_TABLE);
        $this->id = SCHEDULE_AL_ID;
        $this->name = SCHEDULE_ALERT_TABLE;
        
        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];
        
        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
        
       
    }
    
   
    
}
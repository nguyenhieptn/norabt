<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Lab_opt_schedule extends Model_basic
{
    function __construct(){
        
        parent::__construct();
        
         $this->struct = array(
                LAB_OPT_SCHE_ID => [
                    PROP_NAME => LAB_OPT_SCHE_ID,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            LAB_OPT_SCHE_NAME => [
                    PROP_NAME => LAB_OPT_SCHE_NAME,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            LAB_OPT_SCHE_PARAM => [
                    PROP_NAME => LAB_OPT_SCHE_PARAM,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            LAB_OPT_SCHE_START => [
                    PROP_NAME => LAB_OPT_SCHE_START,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            LAB_OPT_SCHE_STOP => [
                    PROP_NAME => LAB_OPT_SCHE_STOP,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            LAB_OPT_SCHE_STATUS => [
                    PROP_NAME => LAB_OPT_SCHE_STATUS,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            LAB_OPT_SCHE_NOTE => [
                    PROP_NAME => LAB_OPT_SCHE_NOTE,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            LAB_OPT_SCHE_LOG => [
                    PROP_NAME => LAB_OPT_SCHE_LOG,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            LAB_OPT_SCHE_USER => [
                    PROP_NAME => LAB_OPT_SCHE_USER,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            
        );
        
        $this->query_builder = DB::connection('lab')->table(LAB_OPT_SCHEDULE_TABLE); 
        $this->id = LAB_OPT_SCHE_ID;
        $this->name = LAB_OPT_SCHEDULE_TABLE;
        
        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];
        
        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
        
       
    }
    
   
    
}
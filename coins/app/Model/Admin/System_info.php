<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class System_info extends Model_basic
{
    function __construct(){
        
        parent::__construct();
        
         $this->struct = array(
                SYS_ID => [
                    PROP_NAME => SYS_ID,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            SYS_NAME => [
                    PROP_NAME => SYS_NAME,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            SYS_CPU => [
                    PROP_NAME => SYS_CPU,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            SYS_RAM => [
                    PROP_NAME => SYS_RAM,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            SYS_SWAP => [
                    PROP_NAME => SYS_SWAP,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            SYS_DISK => [
                    PROP_NAME => SYS_DISK,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            SYS_TOTAL_RAM => [
                    PROP_NAME => SYS_TOTAL_RAM,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            SYS_TOTAL_SWAP => [
                    PROP_NAME => SYS_TOTAL_SWAP,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            SYS_TOTAL_DISK => [
                    PROP_NAME => SYS_TOTAL_DISK,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            SYS_NOTE => [
                    PROP_NAME => SYS_NOTE,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            
        );
        
        $this->query_builder = DB::table(SYSTEM_INFO_TABLE);
        $this->id = SYS_ID;
        $this->name = SYSTEM_INFO_TABLE;
        
        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];
        
        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
        
       
    }
    
   
    
}
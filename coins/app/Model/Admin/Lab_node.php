<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Lab_node extends Model_basic
{
    function __construct(){
        
        parent::__construct();
        
         $this->struct = array(
                LAB_NODE_ID => [
                    PROP_NAME => LAB_NODE_ID,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            LAB_NODE_NAME => [
                    PROP_NAME => LAB_NODE_NAME,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            LAB_NODE_IP => [
                    PROP_NAME => LAB_NODE_IP,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            LAB_NODE_PORT => [
                    PROP_NAME => LAB_NODE_PORT,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            LAB_NODE_SID => [
                    PROP_NAME => LAB_NODE_SID,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            LAB_NODE_STATUS => [
                    PROP_NAME => LAB_NODE_STATUS,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            LAB_NODE_RAM => [
                    PROP_NAME => LAB_NODE_RAM,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            LAB_NODE_RAM_TOTAL => [
                    PROP_NAME => LAB_NODE_RAM_TOTAL,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            LAB_NODE_CPU => [
                    PROP_NAME => LAB_NODE_CPU,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            LAB_NODE_CPU_CORE => [
                    PROP_NAME => LAB_NODE_CPU_CORE,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            LAB_NODE_DISK => [
                    PROP_NAME => LAB_NODE_DISK,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            LAB_NODE_DISK_TOTAL => [
                    PROP_NAME => LAB_NODE_DISK_TOTAL,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            LAB_NODE_NOTE => [
                    PROP_NAME => LAB_NODE_NOTE,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            LAB_NODE_VERSION => [
                    PROP_NAME => LAB_NODE_VERSION,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            
        );
        
        $this->query_builder = DB::connection('lab')->table(LAB_NODE_TABLE);
        $this->id = LAB_NODE_ID;
        $this->name = LAB_NODE_TABLE;
        
        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];
        
        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
        
       
    }
    
   
    
}
<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Lab_track_balance extends Model_basic
{
    function __construct(){
        
        parent::__construct();
        
         $this->struct = array(
                LAB_TRACK_BL_ID => [
                    PROP_NAME => LAB_TRACK_BL_ID,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            LAB_TRACK_BL_ACCOUNT => [
                    PROP_NAME => LAB_TRACK_BL_ACCOUNT,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            LAB_TRACK_BL_TIME => [
                    PROP_NAME => LAB_TRACK_BL_TIME,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            LAB_TRACK_BL_MARGIN_BL => [
                    PROP_NAME => LAB_TRACK_BL_MARGIN_BL,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            LAB_TRACK_BL_INVEST => [
                    PROP_NAME => LAB_TRACK_BL_INVEST,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            LAB_TRACK_BL_UNREALIZE => [
                    PROP_NAME => LAB_TRACK_BL_UNREALIZE,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            LAB_TRACK_BL_BALANCE => [
                    PROP_NAME => LAB_TRACK_BL_BALANCE,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            
        );
        
        $this->query_builder = DB::connection('lab')->table(LAB_TRACK_BALANCE_TABLE);
        $this->id = LAB_TRACK_BL_ID;
        $this->name = LAB_TRACK_BALANCE_TABLE;
        
        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];
        
        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
        
       
    }
    
   
    
}
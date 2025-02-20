<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Bot_ruin extends Model_basic
{
    function __construct(){
        
        parent::__construct();
        
         $this->struct = array(
                BOT_RUIN_ID => [
                    PROP_NAME => BOT_RUIN_ID,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            BOT_RUIN_NAME => [
                    PROP_NAME => BOT_RUIN_NAME,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            BOT_RUIN_CONFIG => [
                    PROP_NAME => BOT_RUIN_CONFIG,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            BOT_RUIN_USER => [
                    PROP_NAME => BOT_RUIN_USER,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            
        );
        
        $this->query_builder = DB::connection('lab')->table(BOT_RUIN_TABLE);
        $this->id = BOT_RUIN_ID;
        $this->name = BOT_RUIN_TABLE;
        
        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];
        
        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
        
       
    }
    
   
    
}


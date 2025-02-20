<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Tele_bot extends Model_basic
{
    function __construct(){
        
        parent::__construct();
        
         $this->struct = array(
                TELE_BOT_ID => [
                    PROP_NAME => TELE_BOT_ID,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            TELE_BOT_NAME => [
                    PROP_NAME => TELE_BOT_NAME,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            TELE_BOT_CODE => [
                    PROP_NAME => TELE_BOT_CODE,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            TELE_BOT_ROLE => [
                    PROP_NAME => TELE_BOT_ROLE,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            
        );
        
        $this->query_builder = DB::table(TELE_BOT_TABLE);
        $this->id = TELE_BOT_ID;
        $this->name = TELE_BOT_TABLE;
        
        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];
        
        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
        
       
    }
    
   
    
}
<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Fear extends Model_basic
{
    function __construct(){
        
        parent::__construct();
        
         $this->struct = array(
                FEAR_ID => [
                    PROP_NAME => FEAR_ID,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            FEAR_TIME => [
                    PROP_NAME => FEAR_TIME,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            FEAR_VALUE => [
                    PROP_NAME => FEAR_VALUE,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            FEAR_CLASS => [
                    PROP_NAME => FEAR_CLASS,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            
        );
        
        $this->query_builder = DB::table(FEAR_TABLE);
        $this->id = FEAR_ID;
        $this->name = FEAR_TABLE;
        
        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];
        
        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
        
       
    }
    
   
    
}
<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Article_group extends Model_basic
{
    function __construct(){
        
        parent::__construct();
        
         $this->struct = array(
                ART_GROUP_ID => [
                    PROP_NAME => ART_GROUP_ID,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            ART_GROUP_TITLE => [
                    PROP_NAME => ART_GROUP_TITLE,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            ART_GROUP_KEY => [
                    PROP_NAME => ART_GROUP_KEY,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            ART_GROUP_WEIGHT => [
                    PROP_NAME => ART_GROUP_WEIGHT,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            ART_GROUP_LANG => [
                    PROP_NAME => ART_GROUP_LANG,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            ART_GROUP_PUBLIC => [
                    PROP_NAME => ART_GROUP_PUBLIC,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            
        );
        
        $this->query_builder = DB::table(ARTICLE_GROUP_TABLE);
        $this->id = ART_GROUP_ID;
        $this->name = ARTICLE_GROUP_TABLE;
        
        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];
        
        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
        
       
    }
    
   
    
}
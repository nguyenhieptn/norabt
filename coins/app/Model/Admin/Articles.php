<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Articles extends Model_basic
{
    function __construct(){
        
        parent::__construct();
        
         $this->struct = array(
                ART_AID => [
                    PROP_NAME => ART_AID,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            ART_TITLE => [
                    PROP_NAME => ART_TITLE,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            ART_SLUG => [
                    PROP_NAME => ART_SLUG,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            ART_SAPO => [
                    PROP_NAME => ART_SAPO,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            ART_BODY => [
                    PROP_NAME => ART_BODY,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            ART_PUBLISHED => [
                    PROP_NAME => ART_PUBLISHED,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            ART_WEIGHT => [
                    PROP_NAME => ART_WEIGHT,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            ART_LANGUAGE => [
                    PROP_NAME => ART_LANGUAGE,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            ART_FEATURE_IMG => [
                    PROP_NAME => ART_FEATURE_IMG,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            ART_TIME => [
                    PROP_NAME => ART_TIME,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            ART_GID => [
                    PROP_NAME => ART_GID,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            
        );
        
        $this->query_builder = DB::table(ARTICLES_TABLE);
        $this->id = ART_AID;
        $this->name = ARTICLES_TABLE;
        
        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];
        
        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
        
       
    }
    
   
    
}
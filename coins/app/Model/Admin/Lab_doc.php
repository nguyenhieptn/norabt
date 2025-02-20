<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Lab_doc extends Model_basic
{
    function __construct(){
        
        parent::__construct();
        
         $this->struct = array(
                LAB_DOC_ID => [
                    PROP_NAME => LAB_DOC_ID,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            LAB_DOC_NAME => [
                    PROP_NAME => LAB_DOC_NAME,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            LAB_DOC_LINK => [
                    PROP_NAME => LAB_DOC_LINK,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            LAB_DOC_DESC => [
                    PROP_NAME => LAB_DOC_DESC,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            LAB_DOC_USER => [
                    PROP_NAME => LAB_DOC_USER,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            LAB_DOC_GROUP => [
                    PROP_NAME => LAB_DOC_GROUP,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            
        );
        
        $this->query_builder = DB::connection('lab')->table(LAB_DOC_TABLE);
        $this->id = LAB_DOC_ID;
        $this->name = LAB_DOC_TABLE;
        
        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];
        
        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
        
       
    }
    
   
    
}
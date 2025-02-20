<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Referral extends Model_basic
{
    function __construct(){
        
        parent::__construct();
        
         $this->struct = array(
                REFERRAL_ID => [
                    PROP_NAME => REFERRAL_ID,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            REFERRAL_ACCOUNT => [
                    PROP_NAME => REFERRAL_ACCOUNT,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            REFERRAL_SYMBOL => [
                    PROP_NAME => REFERRAL_SYMBOL,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            REFERRAL_INCOME => [
                    PROP_NAME => REFERRAL_INCOME,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            REFERRAL_TIME => [
                    PROP_NAME => REFERRAL_TIME,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            
        );
        
        $this->query_builder =  DB::connection('binance')->table(REFERRAL_TABLE); 
        $this->id = REFERRAL_ID;
        $this->name = REFERRAL_TABLE;
        
        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];
        
        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
        
       
    }
    
   
    
}
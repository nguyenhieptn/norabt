<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Accounts extends Model_basic
{
    function __construct(){
        
        parent::__construct();
        
         $this->struct = array(
                ACCOUNT_ID => [
                    PROP_NAME => ACCOUNT_ID,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            ACCOUNT_API_KEY => [
                    PROP_NAME => ACCOUNT_API_KEY,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            ACCOUNT_SECRET_KEY => [
                    PROP_NAME => ACCOUNT_SECRET_KEY,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            ACCOUNT_SIGNATURE => [
                    PROP_NAME => ACCOUNT_SIGNATURE,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            ACCOUNT_TOTAL_INVEST => [
                    PROP_NAME => ACCOUNT_TOTAL_INVEST,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            ACCOUNT_NAME => [
                    PROP_NAME => ACCOUNT_NAME,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            ACCOUNT_NOTE => [
                    PROP_NAME => ACCOUNT_NOTE,
                    PROP_NULL => true,
                    PROP_REGEX => "Pass",
                ], 
            ACCOUNT_TYPE => [
                    PROP_NAME => ACCOUNT_TYPE,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            ACCOUNT_START_TIME => [
                    PROP_NAME => ACCOUNT_START_TIME,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            ACCOUNT_STOP_TIME => [
                    PROP_NAME => ACCOUNT_STOP_TIME,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            ACCOUNT_USER => [
                    PROP_NAME => ACCOUNT_USER,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            ACCOUNT_TELE_BOT => [
                    PROP_NAME => ACCOUNT_TELE_BOT,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            ACCOUNT_TELE_GR_NOTICE => [
                    PROP_NAME => ACCOUNT_TELE_GR_NOTICE,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            ACCOUNT_TELE_GR_ERROR => [
                    PROP_NAME => ACCOUNT_TELE_GR_ERROR,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            ACCOUNT_TELE_GR_SUMMARY => [
                    PROP_NAME => ACCOUNT_TELE_GR_SUMMARY,
                    PROP_NULL => true,
                    PROP_REGEX => "Varchar",
                ], 
            ACCOUNT_RESERVE => [
                    PROP_NAME => ACCOUNT_RESERVE,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            ACCOUNT_COMPOUND => [
                    PROP_NAME => ACCOUNT_COMPOUND,
                    PROP_NULL => true,
                    PROP_REGEX => "Number",
                ], 
            
        );
        
         $this->query_builder = DB::connection('binance')->table(ACCOUNTS_TABLE);
        $this->id = ACCOUNT_ID;
        $this->name = ACCOUNTS_TABLE;
        
        $this->registerSql = [
            ['Admin/Trades', ACCOUNT_ID, TRADE_ACCOUNT, null, null, 'deny', null],
        ];
        
        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
        
       
    }
    
   
    
}
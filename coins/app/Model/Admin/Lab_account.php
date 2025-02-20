<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Lab_account extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            LAB_ACCOUNT_ID => [
                PROP_NAME => LAB_ACCOUNT_ID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_ACCOUNT_NAME => [
                PROP_NAME => LAB_ACCOUNT_NAME,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            LAB_ACCOUNT_BALANCE => [
                PROP_NAME => LAB_ACCOUNT_BALANCE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            LAB_ACCOUNT_RESERVE => [
                PROP_NAME => LAB_ACCOUNT_RESERVE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            LAB_ACCOUNT_COMPOUND => [
                PROP_NAME => LAB_ACCOUNT_COMPOUND,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_ACCOUNT_NOTE => [
                PROP_NAME => LAB_ACCOUNT_NOTE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_ACCOUNT_MARGIN_TYPE => [
                PROP_NAME => LAB_ACCOUNT_MARGIN_TYPE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            LAB_ACCOUNT_TRACK_BALANCE => [
                PROP_NAME => LAB_ACCOUNT_TRACK_BALANCE,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_ACCOUNT_RUNNING => [
                PROP_NAME => LAB_ACCOUNT_RUNNING,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_ACCOUNT_SYNC => [
                PROP_NAME => LAB_ACCOUNT_SYNC,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_ACCOUNT_LEAP => [
                PROP_NAME => LAB_ACCOUNT_LEAP,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_ACCOUNT_DB => [
                PROP_NAME => LAB_ACCOUNT_DB,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_ACCOUNT_DATA_TYPE => [
                PROP_NAME => LAB_ACCOUNT_DATA_TYPE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_ACCOUNT_DATA_LENGTH => [
                PROP_NAME => LAB_ACCOUNT_DATA_LENGTH,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_ACCOUNT_PARAMS => [
                PROP_NAME => LAB_ACCOUNT_PARAMS,
                PROP_NULL => true,
                PROP_REGEX => "Json",
            ],
            LAB_ACCOUNT_SERVER => [
                PROP_NAME => LAB_ACCOUNT_SERVER,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            LAB_ACCOUNT_CHOICE_STRATEGY => [
                PROP_NAME => LAB_ACCOUNT_CHOICE_STRATEGY,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            LAB_ACCOUNT_CHOICE_PERIOD => [
                PROP_NAME => LAB_ACCOUNT_CHOICE_PERIOD,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_ACCOUNT_CHOICE_RESULT => [
                PROP_NAME => LAB_ACCOUNT_CHOICE_RESULT,
                PROP_NULL => true,
                PROP_REGEX => "Json",
            ],
            LAB_ACCOUNT_CHOICE_CONDITION => [
                PROP_NAME => LAB_ACCOUNT_CHOICE_CONDITION,
                PROP_NULL => true,
                PROP_REGEX => "Json",
            ],
            LAB_ACCOUNT_TELE_BOT => [
                PROP_NAME => LAB_ACCOUNT_TELE_BOT,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            LAB_ACCOUNT_TELE_GROUP_NOTICE => [
                PROP_NAME => LAB_ACCOUNT_TELE_GROUP_NOTICE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            LAB_ACCOUNT_TELE_GROUP_SUMMARY => [
                PROP_NAME => LAB_ACCOUNT_TELE_GROUP_SUMMARY,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            LAB_ACCOUNT_TELE_GROUP_ERROR => [
                PROP_NAME => LAB_ACCOUNT_TELE_GROUP_ERROR,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            LAB_ACCOUNT_USER => [
                PROP_NAME => LAB_ACCOUNT_USER,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_ACCOUNT_GROUP => [
                PROP_NAME => LAB_ACCOUNT_GROUP,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],


        );

        $this->query_builder = DB::connection('lab')->table(LAB_ACCOUNT_TABLE);
        $this->id = LAB_ACCOUNT_ID;
        $this->name = LAB_ACCOUNT_TABLE;

        $this->registerSql = [
            ['Admin/Lab_campaigns', LAB_ACCOUNT_ID, LAB_CAMPAIGN_ACCOUNT, null, null, 'cascade', null],
            ['Admin/Lab_optimization', LAB_ACCOUNT_ID, LAB_OPT_ACCOUNT, null, null, 'deny', null],
            ['Admin/Lab_track_balance', LAB_ACCOUNT_ID, LAB_TRACK_BL_ACCOUNT, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

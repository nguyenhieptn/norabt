<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Testnet_account extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            TESTNET_ACCOUNT_ID => [
                PROP_NAME => TESTNET_ACCOUNT_ID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TESTNET_ACCOUNT_NAME => [
                PROP_NAME => TESTNET_ACCOUNT_NAME,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            TESTNET_ACCOUNT_BALANCE => [
                PROP_NAME => TESTNET_ACCOUNT_BALANCE,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TESTNET_ACCOUNT_RESERVE => [
                PROP_NAME => TESTNET_ACCOUNT_RESERVE,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TESTNET_ACCOUNT_COMPOUND => [
                PROP_NAME => TESTNET_ACCOUNT_COMPOUND,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TESTNET_ACCOUNT_NOTE => [
                PROP_NAME => TESTNET_ACCOUNT_NOTE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            TESTNET_ACCOUNT_MARGIN_TYPE => [
                PROP_NAME => TESTNET_ACCOUNT_MARGIN_TYPE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            TESTNET_ACCOUNT_RUNTIME => [
                PROP_NAME => TESTNET_ACCOUNT_RUNTIME,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            TESTNET_ACCOUNT_TELE_BOT => [
                PROP_NAME => TESTNET_ACCOUNT_TELE_BOT,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            TESTNET_ACCOUNT_TELE_GROUP_NOTICE => [
                PROP_NAME => TESTNET_ACCOUNT_TELE_GROUP_NOTICE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            TESTNET_ACCOUNT_TELE_GROUP_SUMMARY => [
                PROP_NAME => TESTNET_ACCOUNT_TELE_GROUP_SUMMARY,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            TESTNET_ACCOUNT_TELE_GROUP_ERROR => [
                PROP_NAME => TESTNET_ACCOUNT_TELE_GROUP_ERROR,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            TESTNET_ACCOUNT_USER => [
                PROP_NAME => TESTNET_ACCOUNT_USER,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],

        );

        $this->query_builder = DB::table(TESTNET_ACCOUNT_TABLE);
        $this->id = TESTNET_ACCOUNT_ID;
        $this->name = TESTNET_ACCOUNT_TABLE;

        $this->registerSql = [
            ['Admin/Testnet_campaign', TESTNET_ACCOUNT_ID, TESTNET_ACCOUNT, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

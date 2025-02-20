<?php

namespace App\Model\Notice;

use Illuminate\Support\Facades\DB;

use App\Model\Model_basic;
use App\Helpers\Request\Reply;


class Notice extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(

            NOTICE_ID => [
                PROP_NAME => NOTICE_ID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            NOTICE_TIME => [
                PROP_NAME => NOTICE_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            NOTICE_UID => [
                PROP_NAME => NOTICE_UID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            NOTICE_UNAME => [
                PROP_NAME => NOTICE_UNAME,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            NOTICE_FIRE_UID => [
                PROP_NAME => NOTICE_FIRE_UID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            NOTICE_FIRE_UNAME => [
                PROP_NAME => NOTICE_FIRE_UNAME,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            NOTICE_CONTENT => [
                PROP_NAME => NOTICE_CONTENT,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            NOTICE_VARIABLE => [
                PROP_NAME => NOTICE_VARIABLE,
                PROP_NULL => true,
                PROP_REGEX => "Json",
            ],
            NOTICE_SEEN => [
                PROP_NAME => NOTICE_SEEN,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            NOTICE_LEVEL => [
                PROP_NAME => NOTICE_LEVEL,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            NOTICE_ACTION => [
                PROP_NAME => NOTICE_ACTION,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            NOTICE_TYPE => [
                PROP_NAME => NOTICE_TYPE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],

        );

        $this->query_builder = DB::table(NOTICE_TABLE);
        $this->id = NOTICE_ID;
        $this->name = NOTICE_TABLE;


        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            ['Auth/Authentication', NOTICE_UNAME, AUTHEN_USERNAME, NOTICE_UID, AUTHEN_ID],
            ['Auth/Authentication', NOTICE_FIRE_UNAME, AUTHEN_USERNAME, NOTICE_FIRE_UID, AUTHEN_ID],

        ];
    }
}

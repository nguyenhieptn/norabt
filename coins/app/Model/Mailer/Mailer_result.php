<?php

namespace App\Model\Mailer;

use Illuminate\Support\Facades\DB;

use App\Model\Model_basic;
use App\Helpers\Request\Reply;


class Mailer_result extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            MRESULT_ID => [
                PROP_NAME => MRESULT_ID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            MRESULT_MAILER => [
                PROP_NAME => MRESULT_MAILER,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            MRESULT_CONTENT => [
                PROP_NAME => MRESULT_CONTENT,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            MRESULT_TO => [
                PROP_NAME => MRESULT_TO,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            MRESULT_FROM => [
                PROP_NAME => MRESULT_FROM,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            MRESULT_TIME => [
                PROP_NAME => MRESULT_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            MRESULT_RESULT => [
                PROP_NAME => MRESULT_RESULT,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            MRESULT_LOG => [
                PROP_NAME => MRESULT_LOG,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],

        );

        $this->query_builder = DB::table(MAILER_RESULT_TABLE);
        $this->id = MRESULT_ID;
        $this->name = MAILER_RESULT_TABLE;
        $this->uploader = APP_UPLOAD;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],

        ];
    }
}

<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Lab_optimization extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            LAB_OPT_ID => [
                PROP_NAME => LAB_OPT_ID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_OPT_NAME => [
                PROP_NAME => LAB_OPT_NAME,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            LAB_OPT_ACCOUNT => [
                PROP_NAME => LAB_OPT_ACCOUNT,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_OPT_PARAMS => [
                PROP_NAME => LAB_OPT_PARAMS,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_OPT_THREAD => [
                PROP_NAME => LAB_OPT_THREAD,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_OPT_NOTE => [
                PROP_NAME => LAB_OPT_NOTE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_OPT_LOG => [
                PROP_NAME => LAB_OPT_LOG,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_OPT_START_TIME => [
                PROP_NAME => LAB_OPT_START_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_OPT_STOP_TIME => [
                PROP_NAME => LAB_OPT_STOP_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_OPT_PROCESSED => [
                PROP_NAME => LAB_OPT_PROCESSED,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_OPT_SERVER => [
                PROP_NAME => LAB_OPT_SERVER,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_OPT_DATA_LENG => [
                PROP_NAME => LAB_OPT_DATA_LENG,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_OPT_USER => [
                PROP_NAME => LAB_OPT_USER,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],

        );

        $this->query_builder = DB::connection('lab')->table(LAB_OPTIMIZATION_TABLE);
        $this->id = LAB_OPT_ID;
        $this->name = LAB_OPTIMIZATION_TABLE;

        $this->registerSql = [
            ['Admin/Lab_opt_result', LAB_OPT_ID, LAB_OPT_RESULT_OPTIMIZATION, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

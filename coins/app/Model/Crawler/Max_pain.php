<?php

namespace App\Model\Crawler;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Max_pain extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            MAX_PAIN_ID => [
                PROP_NAME => MAX_PAIN_ID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            MAX_PAIN_TIME => [
                PROP_NAME => MAX_PAIN_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            MAX_PAIN_PRICE => [
                PROP_NAME => MAX_PAIN_PRICE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
        );

        $this->query_builder = DB::connection('coin_crawler')->table(MAX_PAIN_TABLE);
        $this->id = MAX_PAIN_ID;
        $this->name = MAX_PAIN_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

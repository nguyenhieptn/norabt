<?php

namespace App\Model\Crawler;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Crawler_year_tracking extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            CRAWLER_YEAR_TRACKING_ID => [
                PROP_NAME => CRAWLER_YEAR_TRACKING_ID,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CRAWLER_YEAR_TRACKING_SYMBOL => [
                PROP_NAME => CRAWLER_YEAR_TRACKING_SYMBOL,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CRAWLER_YEAR_TRACKING_DB => [
                PROP_NAME => CRAWLER_YEAR_TRACKING_DB,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CRAWLER_YEAR_TRACKING_EXCHANGE => [
                PROP_NAME => CRAWLER_YEAR_TRACKING_EXCHANGE,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CRAWLER_YEAR_TRACKING_FRAME => [
                PROP_NAME => CRAWLER_YEAR_TRACKING_FRAME,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CRAWLER_YEAR_TRACKING_START_TIME => [
                PROP_NAME => CRAWLER_YEAR_TRACKING_START_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CRAWLER_YEAR_TRACKING_END_TIME => [
                PROP_NAME => CRAWLER_YEAR_TRACKING_END_TIME,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CRAWLER_YEAR_TRACKING_RUNNING => [
                PROP_NAME => CRAWLER_YEAR_TRACKING_RUNNING,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            CRAWLER_YEAR_TRACKING_RESULT => [
                PROP_NAME => CRAWLER_YEAR_TRACKING_RESULT,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            CRAWLER_YEAR_TRACKING_STATUS => [
                PROP_NAME => CRAWLER_YEAR_TRACKING_STATUS,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
        );

        $this->query_builder = DB::connection('coin_crawler')->table(CRAWLER_YEAR_TRACKING_TABLE);
        $this->id = CRAWLER_YEAR_TRACKING_ID;
        $this->name = CRAWLER_YEAR_TRACKING_TABLE;

        $this->registerSql = [
            //['Auth/MapUG', AUTHEN_ID, MAP_UG_PEOPLEID, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

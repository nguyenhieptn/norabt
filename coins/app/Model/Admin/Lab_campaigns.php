<?php

namespace App\Model\Admin;

use Illuminate\Support\Facades\DB;
use App\Model\Model_basic;

class Lab_campaigns extends Model_basic
{
    function __construct()
    {

        parent::__construct();

        $this->struct = array(
            LAB_CAMPAIGN_ID => [
                PROP_NAME => LAB_CAMPAIGN_ID,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_CAMPAIGN_NAME => [
                PROP_NAME => LAB_CAMPAIGN_NAME,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            LAB_CAMPAIGN_SYMBOL => [
                PROP_NAME => LAB_CAMPAIGN_SYMBOL,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            LAB_CAMPAIGN_START => [
                PROP_NAME => LAB_CAMPAIGN_START,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_CAMPAIGN_STOP => [
                PROP_NAME => LAB_CAMPAIGN_STOP,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_CAMPAIGN_PARAMS => [
                PROP_NAME => LAB_CAMPAIGN_PARAMS,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CAMPAIGN_SIDE => [
                PROP_NAME => LAB_CAMPAIGN_SIDE,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CAMPAIGN_STATUS => [
                PROP_NAME => LAB_CAMPAIGN_STATUS,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CAMPAIGN_RUNNING => [
                PROP_NAME => LAB_CAMPAIGN_RUNNING,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CAMPAIGN_STRATEGY => [
                PROP_NAME => LAB_CAMPAIGN_STRATEGY,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_CAMPAIGN_LAST => [
                PROP_NAME => LAB_CAMPAIGN_LAST,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_CAMPAIGN_BUDGET => [
                PROP_NAME => LAB_CAMPAIGN_BUDGET,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_CAMPAIGN_RESERVE => [
                PROP_NAME => LAB_CAMPAIGN_RESERVE,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_CAMPAIGN_COMPOUND => [
                PROP_NAME => LAB_CAMPAIGN_COMPOUND,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_CAMPAIGN_PROFIT => [
                PROP_NAME => LAB_CAMPAIGN_PROFIT,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_CAMPAIGN_ACCOUNT => [
                PROP_NAME => LAB_CAMPAIGN_ACCOUNT,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_CAMPAIGN_MONEY => [
                PROP_NAME => LAB_CAMPAIGN_MONEY,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            LAB_CAMPAIGN_ACTIVE_BUDGET => [
                PROP_NAME => LAB_CAMPAIGN_ACTIVE_BUDGET,
                PROP_NULL => true,
                PROP_REGEX => "Varchar",
            ],
            LAB_CAMPAIGN_PRIORITY => [
                PROP_NAME => LAB_CAMPAIGN_PRIORITY,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_CAMPAIGN_RUNTIME => [
                PROP_NAME => LAB_CAMPAIGN_RUNTIME,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ],
            LAB_CAMPAIGN_LOG => [
                PROP_NAME => LAB_CAMPAIGN_LOG,
                PROP_NULL => true,
                PROP_REGEX => "Pass",
            ],
            LAB_CAMPAIGN_SYM_RANK => [
                PROP_NAME => LAB_CAMPAIGN_SYM_RANK,
                PROP_NULL => true,
                PROP_REGEX => "Number",
            ], 

        );

        $this->query_builder =  DB::connection('lab')->table(LAB_CAMPAIGNS_TABLE);
        $this->id = LAB_CAMPAIGN_ID;
        $this->name = LAB_CAMPAIGNS_TABLE;

        $this->registerSql = [
            ['Admin/Lab_results', LAB_CAMPAIGN_ID, LAB_RESULT_CAMPAIGN, null, null, 'cascade', null],
            ['Admin/Lab_event_logs', LAB_CAMPAIGN_ID, LAB_ELOG_CAMPAIGN, null, null, 'cascade', null],
        ];

        $this->registerDepend = [
            //['Auth/MapUG', AUTHEN_NAME, MAP_UG_PEOPLENAME, AUTHEN_ID, MAP_UG_PEOPLEID],
        ];
    }
}

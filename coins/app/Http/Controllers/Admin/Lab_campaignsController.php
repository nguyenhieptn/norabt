<?php

namespace App\Http\Controllers\Admin;

use App\Crawler\Caculator\EmaLab;
use App\Crawler\Caculator\SignalLab;
use App\Event\Lab\EventCheck15m;
use App\Event\Lab\EventCheck15MH3;
use App\Event\Lab\EventCheck15MH4;
use App\Event\Lab\EventCheck15MH5;
use App\Event\Lab\EventCheck15MH6;
use App\Event\Lab\EventCheck15MH93MH51MH5;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

use App\Helpers\Auth\Role;
use App\Helpers\DB\Edge;
use App\Helpers\DB\Models;
use App\Helpers\Request\Checker;
use App\Helpers\Request\Reply;
use App\Helpers\Uploader\FileFunc;
use App\Helpers\Token\JWToken;
use App\Http\Controllers\Controller;

use Illuminate\Support\Facades\DB;
use App\Helpers\Control\Ctrl;

class Lab_campaignsController extends Controller
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

        $this->mainModel = Models::get('Admin/Lab_campaigns');
        $this->tableName = LAB_CAMPAIGNS_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[LAB_CAMPAIGN_ID] = true;

        if (!Role::checkAdmin()) Reply::finish(false, ERROR_PERMISSION, ['data' => 'Please login by other account']);
    }

    public function add(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas = array_diff_key($datas, $this->dependCols);
        $result = $this->mainModel->add([$datas]);
        if (!$result['result']) Reply::finish($result);
        Reply::finish(true, 'success', $datas);
    }

    public function addGetId(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas = array_diff_key($datas, $this->dependCols);
        $datas[LAB_CAMPAIGN_ID] = uniqid();
        $result = $this->mainModel->add([$datas]);
        if (!$result['result']) Reply::finish($result);
        Reply::finish(true, 'success', $datas);
    }

    public function adds(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        foreach ($datas as $key => $val) {
            $datas[$key] = array_diff_key($datas[$key], $this->dependCols);
        }
        Reply::finish($this->mainModel->add($datas));
    }

    public function addGetIds(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        foreach ($datas as $key => $val) {
            $datas[$key] = array_diff_key($datas[$key], $this->dependCols);
            $datas[$key][LAB_CAMPAIGN_ID] = uniqid();
        }
        $result = $this->mainModel->add($datas);
        if (!$result['result']) Reply::finish($result);
        Reply::finish(true, 'success', $datas);
    }

    public function drop(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas =  $this->mainModel->keyToCondition($datas);
        $dropResult = $this->mainModel->drop([$datas]);
        Reply::finish($dropResult);
    }

    public function drops(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        foreach ($datas as $key => $data) {
            $datas[$key] =  $this->mainModel->keyToCondition($data);
        }
        $result = $this->mainModel->drop($datas);
        Reply::finish($result);
    }

    public function edit(Request $request)
    {
        $datas = $request->all();
        if (count($datas[DATA_KEY]) == 0) Reply::finish(false, "Can not edit all");
        $datas[DATA_KEY] =  array($this->mainModel->keyToCondition($datas[DATA_KEY]));
        $datas[DATA_EDITOR] = array_diff_key($datas[DATA_EDITOR], $this->dependCols);
        $editResult = $this->mainModel->edit($datas);
        Reply::finish($editResult);
    }

    public function edits(Request $request)
    {
        $datas = $request->all();
        foreach ($datas[DATA_KEY] as $key => $data) {
            $datas[DATA_KEY][$key] =  $this->mainModel->keyToCondition($data);
        }
        $datas[DATA_EDITOR] = array_diff_key($datas[DATA_EDITOR], $this->dependCols);
        $editResult = $this->mainModel->edit($datas);
        Reply::finish($editResult);
    }

    public function read(Request $request)
    {
        $datas = $request->all();
        $datas = $this->mainModel->keyToCondition($datas);
        $readResult = $this->mainModel->read([$datas]);
        Reply::finish($readResult);
    }

    public function mapping()
    {
        $mapData = [];
        $mapData[LAB_CAMPAIGN_SYMBOL] = Edge::mapping(Models::get('Admin/Lab_watchlist'), null, LAB_WL_SYMBOL, LAB_WL_SYMBOL);
        $mapData[LAB_CAMPAIGN_SYMBOL]['all'] = 'All';
        $mapData[LAB_CAMPAIGN_STRATEGY] = Edge::mapping(Models::get('Admin/Lab_strategies'), null, LAB_STRATEGY_ID, LAB_STRATEGY_NAME)->toArray();
        $mapData[LAB_CAMPAIGN_SIDE] = ['BOTH' => 'BOTH', 'LONG' => 'LONG', 'SHORT' => 'SHORT'];
        $mapData[LAB_CAMPAIGN_COMPOUND] = ['0' => 'Disable', '1' => 'Enable'];
        $mapData[LAB_CAMPAIGN_ACCOUNT] = Edge::mapping(Models::get('Admin/Lab_account'), null, LAB_ACCOUNT_ID, LAB_ACCOUNT_NAME, null, function ($db) {
            $db->orderBy(LAB_ACCOUNT_ID, 'desc');
            if (!Role::checkRoot()) {
                $db->where(LAB_ACCOUNT_USER, '=', Auth::user()->{AUTHEN_ID});
            }
        })->toArray();


        Reply::finish(true, 'Success', $mapData);
    }

    public function suggest(Request $request)
    {
        $datas = $request->input('search', '');
        $suggestData = $this->mainModel->read([[[LAB_CAMPAIGN_NAME, 'contain', $datas]]], function ($builder) {
            $builder->limit(20);
        });
        $suggest = [];
        if ($suggestData['result']) {

            $suggest = $suggestData['data']->mapWithKeys(function ($item) {
                return [$item->{LAB_CAMPAIGN_ID} => $item->{LAB_CAMPAIGN_NAME}];
            });
        }
        Reply::finish(true, '', $suggest);
    }

    public function filter(Request $request)
    {
        $datas = $request->all();
        $datas[FLAG_FILTER_LOGIC] = 'and';
        $responseData = $this->mainModel->filter($datas);
        if (!$responseData['result']) Reply::finish($responseData);
        $responseData['data']['running'] = $this->mainModel->is_exist([[[LAB_CAMPAIGN_RUNNING, '=', 1]]]);



       

     


      


        // $Candle15mModel = Models::get('Admin/Lab_candle_15m');
        // $Candle15mModel->query_builder = DB::connection(Ctrl::get('control_lab_db', 'coin_crawler'))->table('lab_candle_15m');

        $data = $responseData['data']['data_table'];
        foreach ($data as $row) {

            $sym = $row->{LAB_CAMPAIGN_SYMBOL};
 

            $mongoDb = DB::connection('backtest_data_1m_full');
            $Candle15mModelMongo = $mongoDb->collection('candle_15m');
            $min = $Candle15mModelMongo->where('symbol' , '=' , $sym)->where('is_close' , '=' , 1)->orderBy('close_time', 'ASC')->limit(1)->get();
           
            if (isset($min[0])) {

     

                $staTime = $min[0]['close_time'];
                $row->{'lab_sym_start_time'} = $staTime;
            }
        }
        Reply::finish($responseData);
    }


    public function simulate(Request $request)
    {
        set_time_limit(0);

        $id = $request->input('id', null);

        if (!Checker::validate($id, 'Number')) return Reply::make(false, 'Wrong format');

        $command = 'sudo pkill -f "lab_run ' . $id . '"';
        $result = exec($command);

        $campain = $this->mainModel->read([[[LAB_CAMPAIGN_ID, '=', $id]]]);
        if (!$campain['result'] || !isset($campain['data'][0])) return Reply::make(false, 'Campaign not found');
        $campain = $campain['data'][0];

        $strategyId = $campain->{LAB_CAMPAIGN_STRATEGY};
        if ($strategyId === null) return Reply::make(false, "Please select a Strategy");

        $strategy = Models::get('Admin/Lab_strategies')->read([[[LAB_STRATEGY_ID, '=', $strategyId]]]);
        if (!$strategy['result']) return $strategy;
        if (!isset($strategy['data'][0])) return Reply::make(false, 'Can not find any Strategy');
        $strategy = $strategy['data'][0];

        $strategy = json_decode($strategy->{LAB_STRATEGY_CONTENT});
        if (!$strategy) return Reply::make(false, 'Strategy is wrong format');

        $command = 'sudo php ' . base_path() . '/artisan lab_run ' . $id . ' > /tmp/lab_run_log_' . $id . ' &';
        $result = exec($command);

        $result = $this->mainModel->edit([
            DATA_KEY => [[[LAB_CAMPAIGN_ID, '=', $id]]],
            DATA_EDITOR => [LAB_CAMPAIGN_RUNNING => 1],
        ]);

        return $result;
    }

    public function kill(Request $request)
    {
        set_time_limit(0);

        $id = $request->input('id', null);

        if (!Checker::validate($id, 'Number')) return Reply::make(false, 'Wrong format');

        $command = 'sudo pkill -f "lab_run ' . $id . '"';
        $result = exec($command);

        $result = $this->mainModel->edit([
            DATA_KEY => [[[LAB_CAMPAIGN_ID, '=', $id]]],
            DATA_EDITOR => [LAB_CAMPAIGN_RUNNING => 0],
        ]);

        return $result;
    }


    //

    //

    public function updateRank(Request $request)
    {
        set_time_limit(0);
        $account_id = $request->input('account_id', '');

        $account_id = intval($account_id);

        if ($account_id == '')  Reply::finish(false, 'no account id', '');


        $responseData = $this->mainModel->read([[[LAB_CAMPAIGN_ACCOUNT, '=', $account_id]]]);

        if (!$responseData['result']) Reply::finish($responseData);

        $model_coin_market = Models::get('Admin/CoinMarket');

        $ranks = $model_coin_market->read();

        if (!$ranks['result']) Reply::finish($ranks);
        $ranks = $ranks['data'];


        $rankData = [];
        foreach ($ranks as $row) {
            $rankData[$row->{COINMARKET_SYMBOL}] = $row->{COINMARKET_RANK};
        }




        $data = $responseData['data'];

        foreach ($data as $row) {

 
            $id = $row->{LAB_CAMPAIGN_ID};
            $sym = $row->{LAB_CAMPAIGN_SYMBOL};

            $row->{LAB_CAMPAIGN_SYM_RANK} = isset($rankData[$sym]) ? $rankData[$sym] : '';

            $this->mainModel->edit([
                DATA_KEY => [[[LAB_CAMPAIGN_ID, '=', $id]]],
                DATA_EDITOR => (array)$row
            ]);
        }


        Reply::finish(true, 'success', $account_id);
    }
}

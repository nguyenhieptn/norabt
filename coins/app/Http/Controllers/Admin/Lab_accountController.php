<?php

namespace App\Http\Controllers\Admin;

use App\Helpers\Admin\DataHelper;
use App\Helpers\Admin\LabQuery;
use App\Helpers\Admin\LabSocket;
use App\Helpers\Admin\Services;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

use App\Helpers\Auth\Role;
use App\Helpers\DB\Edge;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use App\Helpers\Uploader\FileFunc;
use App\Helpers\Token\JWToken;
use App\Http\Controllers\Controller;


class Lab_accountController extends Controller
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

        $this->mainModel = Models::get('Admin/Lab_account');
        $this->tableName = LAB_ACCOUNT_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[LAB_ACCOUNT_ID] = true;

        // if(!Role::checkRoot()) Reply::finish(false, ERROR_PERMISSION, ''); 

    }

    public function add(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas = array_diff_key($datas, $this->dependCols);
        $datas[LAB_ACCOUNT_USER] = Auth::user()->{AUTHEN_ID};
        $result = $this->mainModel->add([$datas]);
        if (!$result['result']) Reply::finish($result);
        $datas[LAB_ACCOUNT_ID] = $this->mainModel->getLastId();
        Reply::finish(true, 'success', $datas);
    }

    public function addGetId(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas = array_diff_key($datas, $this->dependCols);
        $result = $this->mainModel->add([$datas]);
        $datas[LAB_ACCOUNT_ID] = $this->mainModel->getLastId();
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
            $datas[$key][LAB_ACCOUNT_ID] = uniqid();
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


    public function editGroup(Request $request){
        $newGroup = $request->input('new_group', '');
        $oldGroup = $request->input('old_group', '');
        $changeStrategyGroup = Models::get('Admin/Lab_strategies')->edit([
            DATA_KEY => [[[LAB_STRATEGY_GROUP, '=', $oldGroup]]],
            DATA_EDITOR => [LAB_STRATEGY_GROUP => $newGroup]
        ]);
        if(!$changeStrategyGroup['result']) return $changeStrategyGroup;
        return $this->mainModel->edit([
            DATA_KEY => [[[LAB_ACCOUNT_GROUP, '=', $oldGroup]]],
            DATA_EDITOR => [LAB_ACCOUNT_GROUP => $newGroup]
        ]);
    }


    public function getGroup(){
        return Reply::make(true, 'success', DataHelper::getLabGroup());
    }

    

    public function mapping()
    {
        $mapData = [];
       
        $mapData[LAB_ACCOUNT_GROUP] = DataHelper::getLabGroup(); 
        $mapData[LAB_ACCOUNT_COMPOUND] = [1 => 'Enable', 0 => 'Disable'];
        $mapData[LAB_ACCOUNT_TRACK_BALANCE] = [1 => 'Enable', 0 => 'Disable'];
        $mapData[LAB_ACCOUNT_MARGIN_TYPE] = ['CROSS' => 'CROSS', 'ISOLATE' => 'ISOLATE'];
        $mapData[LAB_ACCOUNT_RUNNING] = ['1' => 'Running', '0' => 'Stopped'];
        $mapData[LAB_ACCOUNT_SYNC] = ['1' => 'Synchronize', '0' => 'Asynchronize'];
        $mapData[LAB_ACCOUNT_LEAP] = [1 => 'Enable', 0 => 'Disable'];
        $mapData[LAB_ACCOUNT_DB] = [
            'coin_lab_1_year' => 'Database 365 days',
            'coin_crawler' => 'Database 250ms',
            'coin_lab_2021' => 'Database 1m 2021',
            'coin_lab_2020' => 'Database 1m 2020',
            'coin_lab_2019' => 'Database 1m 2019',
            'coin_lab_2018' => 'Database 1m 2018',
            'coin_lab_2017' => 'Database 1m 2017',

            'coin_lab_future_2021' => 'Database 1m future 2021',
            'coin_lab_future_2020' => 'Database 1m future 2020',
            'coin_lab_future_2019' => 'Database 1m future 2019',
            'coin_lab_future_2018' => 'Database 1m future 2018',
            'coin_lab_future_2017' => 'Database 1m future 2017',
            'coin_future' => 'Database 1m Future',
            'coin_spot' => 'Database 1m Spot',

            'backtest_data' => 'LongVan3 1s',
            'backtest_data_1m' => 'LongVan3 1m',
            'backtest_data_1m_full' => 'LongVan3 1m Full Future',
            'backtest_data_1m_spot' => 'LongVan3 1m Full Spot',
            'backtest_data_1m_custom' => 'LongVan3 1m Full Custom',
            'ftx_backtest_data' => 'LongVan3 FTX',

        ];
        $mapData[LAB_ACCOUNT_SERVER] = Edge::mapping(Models::get('Admin/Lab_node'), null, LAB_NODE_NAME, LAB_NODE_NAME);
        $mapData[LAB_ACCOUNT_DATA_TYPE] = ['1m' => '1 minute', '250ms' => '250ms/1s'];

        $mapData[LAB_ACCOUNT_CHOICE_STRATEGY] = Edge::mapping(Models::get('Admin/Lab_strategies'), null, LAB_STRATEGY_ID, LAB_STRATEGY_NAME)->toArray();

        $mapData[LAB_ACCOUNT_TELE_BOT] = Edge::mapping(Models::get('Admin/Tele_bot'), null, TELE_BOT_ID, TELE_BOT_NAME);
        $mapData[LAB_ACCOUNT_TELE_GROUP_NOTICE] = Edge::mapping(Models::get('Admin/Tele_group'), null, TELE_GROUP_ID, TELE_GROUP_NAME, null, function ($db) {
            $db->where(TELE_GROUP_ROLE, '=', 0);
        });
        $mapData[LAB_ACCOUNT_TELE_GROUP_SUMMARY] = Edge::mapping(Models::get('Admin/Tele_group'), null, TELE_GROUP_ID, TELE_GROUP_NAME, null, function ($db) {
            $db->where(TELE_GROUP_ROLE, '=', 1);
        });
        $mapData[LAB_ACCOUNT_TELE_GROUP_ERROR] = Edge::mapping(Models::get('Admin/Tele_group'), null, TELE_GROUP_ID, TELE_GROUP_NAME, null, function ($db) {
            $db->where(TELE_GROUP_ROLE, '=', 2);
        });
        $mapData[LAB_ACCOUNT_USER] = Edge::mapping(Models::get('Auth/Authentication'), null, AUTHEN_ID, AUTHEN_USERNAME, null, function ($db) {

            if (!Role::checkRoot()) {
                $db->where(AUTHEN_ID, '=', Auth::user()->{AUTHEN_ID});
            }
        });
        Reply::finish(true, 'Success', $mapData);
    }

    public function suggest(Request $request)
    {
        $datas = $request->input('search', '');
        $suggestData = $this->mainModel->read([[[LAB_ACCOUNT_NAME, 'contain', $datas]]], function ($builder) {
            $builder->limit(20);
        });
        $suggest = [];
        if ($suggestData['result']) {

            $suggest = $suggestData['data']->mapWithKeys(function ($item) {
                return [$item->{LAB_ACCOUNT_ID} => $item->{LAB_ACCOUNT_NAME}];
            });
        }
        Reply::finish(true, '', $suggest);
    }

    public function filter(Request $request)
    {
        $datas = $request->all();
        $datas[FLAG_FILTER_LOGIC] = 'and';
        $group = get($datas['group'], '');
        
        $responseData = $this->mainModel->filter($datas, function ($db) use($group) {
            $db->where(LAB_ACCOUNT_GROUP, '=', $group);
            if (!Role::checkRoot()) {
                $db->where(LAB_ACCOUNT_USER, '=', Auth::user()->{AUTHEN_ID});
            }
        });
        if (!$responseData['result']) Reply::finish($responseData);
        Reply::finish($responseData);
    }


    public function pysimulate1m(Request $request)
    {
        set_time_limit(0);

        $id = $request->input('id', null);

        $account = Models::get('Admin/Lab_account')->read([[[LAB_ACCOUNT_ID, '=', $id]]]);
        if (!$account['result'] || !isset($account['data'][0])) return Reply::make(false, 'Can not find any account');
        $account = $account['data'][0];

        $server = get($account->{LAB_ACCOUNT_SERVER}, 'Localhost');
        $result = LabSocket::makeRemoteQuery($server, 'account', 'start', ['id' => $id]);
        if (!$result['result']) return $result;

        $result = $this->mainModel->edit([
            DATA_KEY => [[[LAB_ACCOUNT_ID, '=', $id]]],
            DATA_EDITOR => [LAB_ACCOUNT_RUNNING => 1],
        ]);

        return $result;
    }

    public function kill(Request $request)
    {
        set_time_limit(0);

        $id = $request->input('id', null);

        $account = Models::get('Admin/Lab_account')->read([[[LAB_ACCOUNT_ID, '=', $id]]]);
        if (!$account['result'] || !isset($account['data'][0])) return Reply::make(false, 'Can not find any account');
        $account = $account['data'][0];

        $server = get($account->{LAB_ACCOUNT_SERVER}, 'Localhost');
        $result = LabSocket::makeRemoteQuery($server, 'account', 'stop', ['id' => $id]);
        if (!$result['result']) return $result;

        $result = $this->mainModel->edit([
            DATA_KEY => [[[LAB_ACCOUNT_ID, '=', $id]]],
            DATA_EDITOR => [LAB_ACCOUNT_RUNNING => 0],
        ]);

        Models::get('Admin/Lab_campaigns')->edit([
            DATA_KEY => [[[LAB_CAMPAIGN_ACCOUNT, '=', $id]]],
            DATA_EDITOR => [LAB_CAMPAIGN_RUNNING => 0],
        ]);

        return $result;
    }

    
    public function checkRuntime(Request $request)
    {
        $database = $request->input('database', null);
        // if (!is_int($id)) Reply::finish(false, "ID must be an integer");

        // $account = Models::get('Admin/Lab_account')->read([[[LAB_ACCOUNT_ID, '=', $id]]]);
        // if (!$account['result'] || !isset($account['data'][0])) return Reply::make(false, 'Can not find any account');
        // $account = $account['data'][0];
        // $server = get($account->{LAB_ACCOUNT_SERVER}, 'Localhost');
        // return LabSocket::makeRemoteQuery($server, 'account', 'getLog', ['id' => $id]);

    }

    public function getLog(Request $request)
    {
        $id = $request->input('id', null);
        if (!is_int($id)) Reply::finish(false, "ID must be an integer");

        $account = Models::get('Admin/Lab_account')->read([[[LAB_ACCOUNT_ID, '=', $id]]]);
        if (!$account['result'] || !isset($account['data'][0])) return Reply::make(false, 'Can not find any account');
        $account = $account['data'][0];
        $server = get($account->{LAB_ACCOUNT_SERVER}, 'Localhost');
        return LabSocket::makeRemoteQuery($server, 'account', 'getLog', ['id' => $id]);

        // if ($optimize->{LAB_OPT_SERVER} == 'localhost') {
        //     $logFile = base_path() . "/storage/logs/py_lab_optimization_" . $id . ".log";
        //     if (is_file($logFile)) {
        //         $log = file_get_contents($logFile);
        //         return Reply::make(true, 'success', $log);
        //     } else {
        //         return Reply::make(true, 'success', "Log file does not exist");
        //     }
        // } else {
        //     return LabQuery::makeRemoteQuery($optimize->{LAB_OPT_SERVER}, 'api/optimization/getLog', ['id' => $id]);
        // }
    }


    //

    //




}

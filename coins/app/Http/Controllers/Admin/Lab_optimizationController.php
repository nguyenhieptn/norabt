<?php

namespace App\Http\Controllers\Admin;

use App\Helpers\Admin\LabQuery;
use App\Helpers\Admin\LabSocket;
use App\Helpers\Admin\Services;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

use App\Helpers\Auth\Role;
use App\Helpers\DB\Edge;
use App\Helpers\DB\Models;
use App\Helpers\Request\Query;
use App\Helpers\Request\Reply;
use App\Helpers\Uploader\FileFunc;
use App\Helpers\Token\JWToken;
use App\Http\Controllers\Controller;


class Lab_optimizationController extends Controller
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

        $this->mainModel = Models::get('Admin/Lab_optimization');
        $this->tableName = LAB_OPTIMIZATION_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[LAB_OPT_ID] = true;

        if (!Role::checkAdmin()) Reply::finish(false, ERROR_PERMISSION, ['data' => 'Please login by other account']);
    }

    public function add(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas = array_diff_key($datas, $this->dependCols);
        $datas[LAB_OPT_USER] = Auth::user()->{AUTHEN_ID} ;
        $result = $this->mainModel->add([$datas]);
        if (!$result['result']) Reply::finish($result);
        Reply::finish(true, 'success', $datas);
    }

    public function addGetId(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas = array_diff_key($datas, $this->dependCols);
        $datas[LAB_ORDER_ID] = uniqid();
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
            $datas[$key][LAB_ORDER_ID] = uniqid();
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

    public function mapping()
    {
        $mapData = [];
        $mapData[LAB_OPT_ACCOUNT] = Edge::mapping(Models::get('Admin/Lab_account'), null, LAB_ACCOUNT_ID, LAB_ACCOUNT_NAME);
        $mapData[LAB_OPT_SERVER] = Edge::mapping(Models::get('Admin/Lab_node'), null, LAB_NODE_NAME, LAB_NODE_NAME);
        $mapData[LAB_OPT_USER] = Edge::mapping(Models::get('Auth/Authentication'), null, AUTHEN_ID, AUTHEN_USERNAME , null , function($db){

            if(!Role::checkRoot()){
                $db->where(AUTHEN_ID, '=', Auth::user()->{AUTHEN_ID});
            } 
           
        });
        Reply::finish(true, 'Success', $mapData);
    }

    public function suggest(Request $request)
    {
        $datas = $request->input('search', '');
        $suggestData = $this->mainModel->read([[[LAB_ORDER_TIME, 'contain', $datas]]], function ($builder) {
            $builder->limit(20);
        });
        $suggest = [];
        if ($suggestData['result']) {

            $suggest = $suggestData['data']->mapWithKeys(function ($item) {
                return [$item->{LAB_ORDER_ID} => $item->{LAB_ORDER_TIME}];
            });
        }
        Reply::finish(true, '', $suggest);
    }

    public function filter(Request $request)
    {
        $datas = $request->all();
        $datas[FLAG_FILTER_LOGIC] = 'and';
        $responseData = $this->mainModel->filter($datas, function($db){

            if(!Role::checkRoot()){
                $db->where(LAB_OPT_USER, '=', Auth::user()->{AUTHEN_ID});
            } 
           
        });
        if (!$responseData['result']) Reply::finish($responseData);
        
        foreach ($responseData['data'][DATA_TABLE] as $key => $val) {
            $processed = $val->{LAB_OPT_PROCESSED};
            $processed = explode(',', $processed);
            if (count($processed) < 2 || $processed[0] == $processed[1]) {
                $responseData['data'][DATA_TABLE][$key]->{'isRunning'} = false;
                continue;
            }
            $server = get($val->{LAB_OPT_SERVER}, 'Localhost');
            $isRunning = LabSocket::makeRemoteQuery(
                $server,
                'optimization',
                'getStatus',
                ['ids' => [$val->{LAB_OPT_ID}]]
            );

            if ($isRunning['result'] && $isRunning['data'][$val->{LAB_OPT_ID}]) {
                $responseData['data'][DATA_TABLE][$key]->{'isRunning'} = 1;
            }

            // if ($val->{LAB_OPT_SERVER} == 'localhost') {
            //     $isRunning = Services::isRunning("lab_optimization " . $val->{LAB_OPT_ID} . " ");
            //     if (!$isRunning) {
            //         $tempFolder = base_path() . "/python/crypto_services/tmp/phoenix_opti_cache/tempFolder_" . $val->{LAB_OPT_ID};
            //         if (Services::isDir($tempFolder)) {
            //             $isRunning = 2;
            //         } else {
            //             $isRunning = 0;
            //         }
            //     } else {
            //         $isRunning = 1;
            //     }
            //     $responseData['data'][DATA_TABLE][$key]->{'isRunning'} = $isRunning;
            // } else {
            //     $isRunning = LabQuery::makeRemoteQuery(
            //         $val->{LAB_OPT_SERVER},
            //         'api/optimization/getStatus',
            //         ['ids' => [$val->{LAB_OPT_ID}]],
            //         [
            //             CURLOPT_CONNECTTIMEOUT => 5,
            //             CURLOPT_TIMEOUT => 5
            //         ]
            //     );
            //     if ($isRunning['result'] && $isRunning['data'][$val->{LAB_OPT_ID}]) {
            //         $responseData['data'][DATA_TABLE][$key]->{'isRunning'} = 1;
            //     }
            // }
        }
        Reply::finish($responseData);
    }


    // public function optimize(Request $request){
    //     set_time_limit(0);

    //     $id = $request->input('id', null);
    //     $continue = $request->input('continue', false);

    //     $command = 'sudo pkill -f "lab_optimization '.$id.' "';
    //     $result = exec($command);

    //     $optimize = $this->mainModel->read([[[LAB_OPT_ID, '=', $id]]]);
    //     if(!$optimize['result'] || !isset($optimize['data'][0])) Reply::finish(false, "No Optimization $id");
    //     $optimize = $optimize['data'][0];

    //     if($optimize->{LAB_OPT_SERVER} == 'localhost'){
    //         $command = "cd " . base_path() . "/python/crypto_services && sudo python manage.py lab_optimization ".$id;
    //         if($continue) $command .= " --continue";
    //         $command .= " > ".base_path()."/storage/logs/py_lab_optimization_".$id.".log 2>&1 &";
    //         $result = exec($command);
    //         return Reply::make(true, 'success', $result);
    //     }else{
    //         return LabQuery::makeRemoteQuery($optimize->{LAB_OPT_SERVER}, 'api/optimization/start', ['id'=>$id, 'minute' => false, 'continue' => $continue]);
    //     }
    // }

    public function optimize1m(Request $request)
    {

        set_time_limit(0);

        $id = $request->input('id', null);
        $continue = $request->input('continue', false);
        if (!is_int($id)) Reply::finish(false, "ID must be an integer");

        $optimize = $this->mainModel->read([[[LAB_OPT_ID, '=', $id]]]);
        if (!$optimize['result'] || !isset($optimize['data'][0])) Reply::finish(false, "No Optimization $id");
        $optimize = $optimize['data'][0];
        $server = get($optimize->{LAB_OPT_SERVER}, 'Localhost');
        return LabSocket::makeRemoteQuery($server, 'optimization', 'start', ['id' => $id, 'continue' => $continue]);

        // $command = 'sudo pkill -f "lab_optimization ' . $id . ' "';
        // $result = exec($command);

        // if ($optimize->{LAB_OPT_SERVER} == 'localhost') {

        //     $command = "cd " . base_path() . "/python/crypto_services && sudo python manage.py lab_optimization " . $id . " --tail";
        //     if ($continue) $command .= " --continue";
        //     $command .= " > " . base_path() . "/storage/logs/py_lab_optimization_" . $id . ".log 2>&1 &";
        //     $result = exec($command);
        //     return Reply::make(true, 'success', $result);
        // } else {
        //     return LabQuery::makeRemoteQuery($optimize->{LAB_OPT_SERVER}, 'api/optimization/start', ['id' => $id, 'continue' => $continue]);
        // }
    }

    public function kill(Request $request)
    {
        set_time_limit(0);

        $id = $request->input('id', null);
        if (!is_int($id)) Reply::finish(false, "ID must be an integer");


        $optimize = $this->mainModel->read([[[LAB_OPT_ID, '=', $id]]]);
        if (!$optimize['result'] || !isset($optimize['data'][0])) Reply::finish(false, "No Optimization $id");
        $optimize = $optimize['data'][0];
        $server = get($optimize->{LAB_OPT_SERVER}, 'Localhost');
        return LabSocket::makeRemoteQuery($server, 'optimization', 'stop', ['id' => $id]);

        // $command = 'sudo pkill -f "lab_optimization ' . $id . ' "';
        // $result = exec($command);

        // if ($optimize->{LAB_OPT_SERVER} == 'localhost') {
        //     $tempFolder = base_path() . "/python/crypto_services/tmp/phoenix_opti_cache/tempFolder_" . $id;
        //     exec("sudo rm -rf " . $tempFolder);
        //     return Reply::make(true, 'success', $result);
        // } else {
        //     return LabQuery::makeRemoteQuery($optimize->{LAB_OPT_SERVER}, 'api/optimization/stop', ['id' => $id]);
        // }
    }

    public function getLog(Request $request)
    {
        $id = $request->input('id', null);
        if (!is_int($id)) Reply::finish(false, "ID must be an integer");

        $optimize = $this->mainModel->read([[[LAB_OPT_ID, '=', $id]]]);
        if (!$optimize['result'] || !isset($optimize['data'][0])) Reply::finish(false, "No Optimization $id");
        $optimize = $optimize['data'][0];
        $server = get($optimize->{LAB_OPT_SERVER}, 'Localhost');
        return LabSocket::makeRemoteQuery($server, 'optimization', 'getLog', ['id' => $id]);

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

}

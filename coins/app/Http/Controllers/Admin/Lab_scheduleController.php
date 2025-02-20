<?php
namespace App\Http\Controllers\Admin;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

use App\Helpers\Auth\Role;
use App\Helpers\DB\Edge;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use App\Helpers\Uploader\FileFunc;
use App\Helpers\Token\JWToken;
use App\Http\Controllers\Controller;


class Lab_scheduleController extends Controller  
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

        $this->mainModel = Models::get('Admin/Lab_schedule');
        $this->tableName = LAB_SCHEDULE_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[LAB_SCHE_ID] = true;

        if(!Role::checkRoot()) Reply::finish(false, ERROR_PERMISSION, ''); 
        
    }

    public function add(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas = array_diff_key($datas, $this->dependCols);
        $datas[LAB_SCHE_USER] = Auth::user()->{AUTHEN_ID} ;
        $result = $this->mainModel->add([$datas]);
        if(!$result['result']) Reply::finish($result);
        Reply::finish(true, 'success', $datas);
    }

    public function addGetId(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas = array_diff_key($datas, $this->dependCols);
        $datas[LAB_SCHE_ID] = uniqid();
        $result = $this->mainModel->add([$datas]);
        if(!$result['result']) Reply::finish($result);
        Reply::finish(true, 'success', $datas); 
    }

    public function adds(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        foreach ($datas as $key=>$val){
            $datas[$key] = array_diff_key($datas[$key], $this->dependCols);
        }
        Reply::finish($this->mainModel->add($datas)); 
    }

    public function addGetIds(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        foreach ($datas as $key=>$val){
            $datas[$key] = array_diff_key($datas[$key], $this->dependCols);
            $datas[$key][LAB_SCHE_ID] = uniqid();
        }
        $result = $this->mainModel->add($datas);
        if(!$result['result']) Reply::finish($result);
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
        foreach ($datas as $key=>$data){
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
        foreach ($datas[DATA_KEY] as $key=>$data){
            $datas[DATA_KEY][$key] =  $this->mainModel->keyToCondition($data);
        }
        $datas[DATA_EDITOR] = array_diff_key($datas[DATA_EDITOR], $this->dependCols);
        $editResult = $this->mainModel->edit($datas);
        Reply::finish($editResult);
    }

    public function read(Request $request)
    {
        $datas = $request->all();
        $orderBy = get($datas['orderBy'], null);
        $sort = get($datas['sort'], 'asc');
        $limit = get($datas['limit'], null);
        $skip = get($datas['skip'], null);
        $select = get($datas['select'], null);
        $datas = array_diff_key($datas, array_flip(['orderBy', 'sort', 'limit', 'skip', 'select']));
        
        $datas = $this->mainModel->keyToCondition($datas);
        $readResult = $this->mainModel->read([$datas], function($db) use($orderBy, $sort, $limit, $skip){
            if(!is_null($orderBy)) $db->orderBy($orderBy, $sort);
            if(!is_null($limit)) $db->limit($limit);
            if(!is_null($skip)) $db->skip($skip);
        }, false, $select);
        Reply::finish($readResult);
    }

    public function mapping(){
        $mapData = [];
        $mapData['lab_account'] = Edge::mapping(Models::get('Admin/Lab_account'), null, LAB_ACCOUNT_ID, LAB_ACCOUNT_NAME);
        $mapData[LAB_SCHE_STATUS] = [
            "0" => "Stopped", 
            '1' => 'Running',
        ];
        $mapData[LAB_SCHE_PARAM] = [
            LAB_OPT_SCHE_PARAM_STATUS_PENDING => 'PENDING',
            LAB_OPT_SCHE_PARAM_STATUS_SENT => 'SENT',
            LAB_OPT_SCHE_PARAM_STATUS_RUNNING => 'RUNNING',
            LAB_OPT_SCHE_PARAM_STATUS_PAUSE => 'PAUSE',
            LAB_OPT_SCHE_PARAM_STATUS_DONE => 'DONE',
        ];
        $mapData['Lab_sche_server'] = Edge::mapping(Models::get('Admin/Lab_node'), null, LAB_NODE_NAME, LAB_NODE_NAME);
        $mapData[LAB_SCHE_USER] = Edge::mapping(Models::get('Auth/Authentication'), null, AUTHEN_ID, AUTHEN_USERNAME , null , function($db){

            if(!Role::checkRoot()){
                $db->where(AUTHEN_ID, '=', Auth::user()->{AUTHEN_ID});
            } 
           
        });
        Reply::finish(true, 'Success', $mapData);
    }

    public function suggest(Request $request)
    {
        $datas = $request->input('search', '');
        $suggestData = $this->mainModel->read([[[LAB_SCHE_NAME, 'contain', $datas]]], function($builder){$builder->limit(20);});
        $suggest = [];
        if($suggestData['result']){
             
            $suggest = $suggestData['data']->mapWithKeys(function ($item){
                return [$item->{LAB_SCHE_ID} => $item->{LAB_SCHE_NAME}];
            });
        }
        Reply::finish(true, '', $suggest);
    }

    public function filter(Request $request)
    {
        $datas = $request->all();
        $datas[FLAG_FILTER_LOGIC] = 'and';
        $responseData = $this->mainModel->filter($datas);
        if(!$responseData['result']) Reply::finish($responseData);
        Reply::finish($responseData);
    }


    //
    
    //
    
   
   
    
}
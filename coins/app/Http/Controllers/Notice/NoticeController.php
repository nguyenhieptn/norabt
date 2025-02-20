<?php
namespace App\Http\Controllers\Notice;

use App\Helpers\Auth\Role;
use App\Helpers\DB\Models;
use App\Helpers\Notice\Notice_helper;
use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use App\Helpers\Request\Checker;
use App\Helpers\Request\Reply;
use Illuminate\Support\Facades\Auth;


class NoticeController extends Controller  
{

    function __construct()
    {
        parent::__construct();
        $this->mainModel = $this->models->getModel('Notice/Notice');
        $this->tableName = NOTICE_TABLE;
        $this->viewblade = 'reactjs.reactjs';
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[NOTICE_ID] = true;
        if(!Role::checkRoot()) Reply::finish(false, ERROR_PERMISSION, ['data'=>'Please login by other account']); 
    }

    private function checkRoot(){
        
        if(!Role::checkRoot()){
            Reply::finish(false, ERROR_PERMISSION);
        }
    }

    public function add(Request $request)
    {
        $this->checkRoot();
        $datas = $request->input('data', array());
        if(!isset($datas['rowData'])) Reply::finish(false, ERROR_UNDEFINE, ['data'=>'Data']);
        $data = $datas['rowData'];

        if(!isset($data[NOTICE_CONTENT]) || $data[NOTICE_CONTENT] == '') Reply::finish(false, ERROR_UNDEFINE, ['data'=>'Content']);
       
        
        if($data[NOTICE_UID] == 0){
            Notice_helper::all($data[NOTICE_CONTENT], [], get($data[NOTICE_LEVEL], 3), get($data[NOTICE_ACTION], null));
        }else{
            Notice_helper::add([$data[NOTICE_UID]], $data[NOTICE_CONTENT], [], get($data[NOTICE_LEVEL], 3), get($data[NOTICE_ACTION], null));
        }
        Reply::finish(true, 'success'); 
    }

    public function drop(Request $request)
    {
        $this->checkRoot();
        $datas = $request->input('data', array()); 
        foreach ($datas as $key=>$data){
            $datas[$key] =  $this->mainModel->keyToCondition($data);
        }
        
        $dropResult = $this->mainModel->drop($datas);
        return $dropResult;
    }

    public function edit(Request $request)
    {
        $datas = $request->input('data', array());
        foreach ($datas[DATA_KEY] as $key=>$data){
            $data[NOTICE_UID] = Auth::user()->{AUTHEN_ID};
            $datas[DATA_KEY][$key] =  $this->mainModel->keyToCondition($data);
        }
        $datas[DATA_EDITOR] = array_diff_key($datas[DATA_EDITOR], $this->dependCols);
        $editResult = $this->mainModel->edit($datas);
        return $editResult;
    }

    public function read(Request $request)
    {
        
        $datas = $request->input('data', array());
        foreach ($datas as $key=>$data){
            $data[NOTICE_UID] = Auth::user()->{AUTHEN_ID};
            $datas[$key] =  $this->mainModel->keyToCondition($data);
        }
        $readResult = $this->mainModel->read($datas);
        return $readResult;
    }

    public function read_more(Request $request){
        $inteval = $request->input('inteval', 0);
        if(!Checker::validate($inteval, 'Number')) Reply::finish(false, 'Wrong format');
        $readResult = $this->mainModel->read(null, function($builder)use($inteval){
            $builder->where(NOTICE_UID, '=', Auth::user()->{AUTHEN_ID})->orderBy(NOTICE_TIME, 'DESC')->limit($inteval);
        });
        $logs=[];
        if($readResult['result']) $logs = $readResult['data'];
        
        $newLogs = $this->mainModel->count([[[NOTICE_SEEN, '=', 0], [NOTICE_UID, '=', Auth::user()->{AUTHEN_ID}]]]);
        
        Reply::finish(true, 'Success', ['logs' => $logs, 'new_logs' => $newLogs['data']]);
    }

    public function suggest(Request $request)
    {
        $this->checkRoot();
        $datas = $request->input('search', '');
        $suggestData = $this->mainModel->read([[[NOTICE_CONTENT, 'contain', $datas]]], function($builder){$builder->limit(20);});
        $suggest = [];
        if($suggestData['result']){
             
            $suggest = $suggestData['data']->mapWithKeys(function ($item){
                return [$item->{NOTICE_ID} => $item->{NOTICE_CONTENT}];
            });
        }
        Reply::finish(true, '', $suggest);
    }

    public function userSuggest(Request $request){
        $this->checkRoot();
        $datas = $request->input('search', '');
        $suggestData = Models::get('Auth/Authentication')->read([[[AUTHEN_USERNAME, 'contain', $datas]]], function($builder){$builder->limit(20);});
        
        if($suggestData['result']){
             
            $suggest = $suggestData['data']->mapWithKeys(function ($item){
                return [$item->{AUTHEN_ID} => $item->{AUTHEN_USERNAME}];
            });
        }
        $suggest[0] = 'All';
        Reply::finish(true, '', $suggest);
    }
    
    public function mapping(){
        $this->checkRoot();
        $mapData = [];
        $mapData[NOTICE_SEEN] = (object)[0 => 'Chưa xem', 1=> 'Đã xem'];
        Reply::finish(true, 'Success', $mapData);
    }

    public function filter(Request $request)
    {
        $this->checkRoot();
        $datas = $request->input('data', array());
        
        $datas[FLAG_FILTER_LOGIC] = 'and';
        
        $responseData = $this->mainModel->filter($datas);
        
        if(!$responseData['result']) Reply::finish($responseData);
        
        return $responseData;
    }

    public function view() 
    {
        return view($this->viewblade);
    }
    
}
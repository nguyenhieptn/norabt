<?php
namespace App\Http\Controllers\Auth;

use App\Helpers\Auth\Role;
use App\Helpers\DB\Models;
use App\Http\Controllers\Controller;
use Illuminate\Support\Facades\Auth;
use Illuminate\Http\Request;
use App\Helpers\Request\Reply;
use Illuminate\Support\Facades\Hash;
use App\Helpers\Uploader\FileFunc;

class AuthenticationController extends Controller  
{

    function __construct()
    {
        parent::__construct();
        $this->mainModel = Models::get('Auth/Authentication');
        $this->tableName = AUTHENTICATION_TABLE;
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[AUTHEN_ID] = true;
        if(!Role::checkRoot()) Reply::finish(false, ERROR_PERMISSION);

    }


    public function add(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        if(isset($datas[AUTHEN_PASS]) && $datas[AUTHEN_PASS] != ''){
            $datas[AUTHEN_PASS] = Hash::make($datas[AUTHEN_PASS]);
        }
        $datas[AUTHEN_TIME] = time();
        $datas = array_diff_key($datas, $this->dependCols);
        $result = $this->mainModel->add([$datas]);
        if(!$result['result']) Reply::finish($result);
        Reply::finish(true, 'success', $datas);
    }

    public function addGetId(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        if(isset($datas[AUTHEN_PASS]) && $datas[AUTHEN_PASS] != ''){
            $datas[AUTHEN_PASS] = Hash::make($datas[AUTHEN_PASS]);
        }
        $datas[AUTHEN_TIME] = time();
        $datas = array_diff_key($datas, $this->dependCols);
        $datas[AUTHEN_ID] = uniqid();
        $result = $this->mainModel->add([$datas]);
        if(!$result['result']) Reply::finish($result);
        Reply::finish(true, 'success', $datas); 
    }

    public function adds(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        foreach ($datas as $key=>$val){
            if(isset($val[AUTHEN_PASS]) && $val[AUTHEN_PASS] != ''){
                $datas[$key][AUTHEN_PASS] = Hash::make($val[AUTHEN_PASS]);
            }
            $datas[$key][AUTHEN_TIME] = time();
            $datas[$key] = array_diff_key($datas[$key], $this->dependCols);
        }
        Reply::finish($this->mainModel->add($datas)); 
    }

    public function addGetIds(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        foreach ($datas as $key=>$val){
            if(isset($val[AUTHEN_PASS]) && $val[AUTHEN_PASS] != ''){
                $datas[$key][AUTHEN_PASS] = Hash::make($val[AUTHEN_PASS]);
            }
            $datas[$key][AUTHEN_TIME] = time();
            $datas[$key] = array_diff_key($datas[$key], $this->dependCols);
            $datas[$key][AUTHEN_ID] = uniqid();
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
        if(isset($datas[DATA_EDITOR][AUTHEN_PASS]) && $datas[DATA_EDITOR][AUTHEN_PASS] != ''){
            $datas[DATA_EDITOR][AUTHEN_PASS] = Hash::make($datas[DATA_EDITOR][AUTHEN_PASS]);
        }else{
            unset($datas[DATA_EDITOR][AUTHEN_PASS]);
        }
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
        if(isset($datas[DATA_EDITOR][AUTHEN_PASS]) && $datas[DATA_EDITOR][AUTHEN_PASS] != ''){
            $datas[DATA_EDITOR][AUTHEN_PASS] = Hash::make($datas[DATA_EDITOR][AUTHEN_PASS]);
        }else{
            unset($datas[DATA_EDITOR][AUTHEN_PASS]);
        }
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

    public function mapping(){
        $mapData = [];
        //$mapData[CUS_PRO] = $this->getMapData(null, $this->models->getModel('Admin/Projects'), null, PRO_NAME, PRO_NAME);
        $mapData[AUTHEN_GROUP]=[AUTHEN_GROUP_ROOT => 'Root', AUTHEN_GROUP_ADMIN => 'Admin', AUTHEN_GROUP_PROVIDER => 'Provider', AUTHEN_GROUP_USER => 'User' , AUTHEN_GROUP_MONITOR => 'Monitor'];
        $mapData[AUTHEN_ACTIVE]=[AUTHEN_ACTIVE_VERIFIED => 'Verified', AUTHEN_ACTIVE_WAITTING => 'Waiting verify Email'];
        $mapData[AUTHEN_STATUS]=[AUTHEN_STATUS_DENY => 'Blocked', AUTHEN_STATUS_APPROVE => 'Approve'];
        Reply::finish(true, 'Success', $mapData);
    }

    public function filter(Request $request)
    {
        $datas = $request->all();
        $datas[FLAG_FILTER_LOGIC] = 'and';
        $responseData = $this->mainModel->filter($datas);
        if(!$responseData['result']) Reply::finish($responseData);
        Reply::finish($responseData);
    }

    public function uploader_upload(Request $request)
    {
        $column = $request->input('column', '');
        if ($column == '') Reply::finish(false, ERROR_UNDEFINE, ['data' => 'Column']);
        $file = $request->input('file', '');
        if ($file == '') Reply::finish(false, ERROR_UNDEFINE, ['data' => 'Metadata']);
        $size = $file['size'] + 1024;
        $disk = resolve('Models')->getModel('Uploader/Uploader_disks')->read(
            [[[DISK_TYPE, '=', 'local'], [DISK_FREE, '>', $size], [DISK_ACTIVE, '=', 1]]],
            function ($db) {
                $db->orderBy(DISK_WEIGHT, 'DESC');
            }
        );
        $option = ['condition' => ['validation' => 'required|image']];

        if (!$disk['result']) Reply::finish($disk);
        if (!isset($disk['data'][0])) Reply::finish(false, 'All disk is fulled');

        $diskName = $disk['data'][0]->{DISK_NAME};
        $uploader = $disk['data'][0]->{DISK_UPLOADER};

        return FileFunc::upload($uploader, $diskName, $this->tableName, $column, Auth::user()->{AUTHEN_ID}, $option);
    }


    public function uploader_read(Request $request)
    {
        $file = $request->input('file', '');
        if ($file == '') Reply::finish(false, ERROR_UNDEFINE, ['data' => 'File']);
        $fileInfo = FileFunc::parse($file);
        if (!$fileInfo) Reply::finish(false, 'File Not Found');
        $fileInfo[FILE_TABLE] = $this->tableName;
        $fileInfo[FILE_UID] = Auth::user()->{AUTHEN_ID};
        $result = FileFunc::read(...array_values($fileInfo));
        if (!$result['result']) Reply::finish($result);
        return redirect($result['data']['ulink'] . '?utoken=' . $result['data']['utoken']);
    }

    public function uploader_delete(Request $request)
    {
        $file = $request->input('file', '');
        if ($file == '') Reply::finish(false, 'No File Metadata');
        $fileInfo = FileFunc::parse($file);
        if (!$fileInfo) Reply::finish(false, 'File Not Found');
        $fileInfo[FILE_TABLE] = $this->tableName;
        $fileInfo[FILE_UID] = Auth::user()->{AUTHEN_ID};

        $result = FileFunc::delete(...array_values($fileInfo));
        if (!$result['result']) Reply::finish($result);
        return redirect($result['data']['ulink'] . '?utoken=' . $result['data']['utoken']);
    }

    public function uploader_get(Request $request)
    {
        $column = $request->input('column', '');
        if ($column == '') Reply::finish(false, ERROR_UNDEFINE, ['data' => 'Column']);
        return FileFunc::get($this->tableName, $column, Auth::user()->{AUTHEN_ID});
    }

    public function uploader_publish(Request $request)
    {
        $file = $request->input('file', '');
        if ($file == '') Reply::finish(false, ERROR_UNDEFINE, ['data' => 'File']);
        $fileInfo = FileFunc::parse($file);
        if (!$fileInfo) Reply::finish(false, 'File Not Found');
        $fileInfo[FILE_TABLE] = $this->tableName;
        $fileInfo[FILE_UID] = Auth::user()->{AUTHEN_ID};
        $ulink = $fileInfo[FILE_UPLOADER] . '/api/uploader/public/read?file=' . $file;
        return redirect($ulink);
    }
    
}
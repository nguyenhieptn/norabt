<?php
namespace App\Http\Controllers\Admin;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

use App\Helpers\Auth\Role;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use App\Helpers\Uploader\FileFunc;
use App\Helpers\Token\JWToken;
use App\Http\Controllers\Controller;


class RequestsController extends Controller  
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

        $this->mainModel = Models::get('Admin/Requests');
        $this->tableName = REQUESTS_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[REQUEST_ID] = true;

        if(!Role::checkAdmin()) Reply::finish(false, ERROR_PERMISSION, ['data'=>'Please login by other account']);  
        
    }

    public function add(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas = array_diff_key($datas, $this->dependCols);
        $result = $this->mainModel->add([$datas]);
        if(!$result['result']) Reply::finish($result);
        Reply::finish(true, 'success', $datas);
    }

    public function addGetId(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas = array_diff_key($datas, $this->dependCols);
        $datas[REQUEST_ID] = uniqid();
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
            $datas[$key][REQUEST_ID] = uniqid();
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
        $datas = $this->mainModel->keyToCondition($datas);
        $readResult = $this->mainModel->read([$datas]);
        Reply::finish($readResult);
    }

    public function mapping(){
        $mapData = [];
        Reply::finish(true, 'Success', $mapData);
    }

    public function suggest(Request $request)
    {
        $datas = $request->input('search', '');
        $suggestData = $this->mainModel->read([[[REQUEST_TIME, 'contain', $datas]]], function($builder){$builder->limit(20);});
        $suggest = [];
        if($suggestData['result']){
             
            $suggest = $suggestData['data']->mapWithKeys(function ($item){
                return [$item->{REQUEST_ID} => $item->{REQUEST_TIME}];
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


    //$$uploading$$
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
    
    //$$/uploading$$
    
    //
    
   
   
    
}
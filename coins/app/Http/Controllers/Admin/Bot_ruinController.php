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
use App\Helpers\DB\Edge;
use Illuminate\Support\Facades\File;

class Bot_ruinController extends Controller  
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

        $this->mainModel = Models::get('Admin/Bot_ruin');
        $this->tableName = BOT_RUIN_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[BOT_RUIN_ID] = true;

        if(!Role::checkRoot()) Reply::finish(false, ERROR_PERMISSION, ''); 
        
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
        $datas[BOT_RUIN_ID] = uniqid();
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
            $datas[$key][BOT_RUIN_ID] = uniqid();
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
        $mapData[BOT_RUIN_USER] = Edge::mapping(Models::get('Auth/Authentication'), null, AUTHEN_ID, AUTHEN_USERNAME , null , function($db){

            if(!Role::checkRoot()){
                $db->where(AUTHEN_ID, '=', Auth::user()->{AUTHEN_ID});
            } 
           
        });
        Reply::finish(true, 'Success', $mapData);
    }

    public function suggest(Request $request)
    {
        $datas = $request->input('search', '');
        $suggestData = $this->mainModel->read([[[BOT_RUIN_NAME, 'contain', $datas]]], function($builder){$builder->limit(20);});
        $suggest = [];
        if($suggestData['result']){
             
            $suggest = $suggestData['data']->mapWithKeys(function ($item){
                return [$item->{BOT_RUIN_ID} => $item->{BOT_RUIN_NAME}];
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
        $directory = '/var/www/html/coins/python/duy/Coins/results';
        $files = File::files($directory);
        $numbers = [];
        foreach ($files as $file) {
            $filename = $file->getFilename();
            if (preg_match('/(\d+)/', $filename, $matches)) {
                $number = $matches[1];
                $numbers[$number] = true ;
            }
        }
        foreach($responseData['data'][DATA_TABLE] as $key => $val){
            $responseData['data'][DATA_TABLE][$key]->{'file_excel'} = get($numbers[$val->{BOT_RUIN_ID}], false);
        }
        Reply::finish($responseData);
    }


    //
    
    //
    public function run_ruin(Request $request)
    {
        $id = $request->input('id', '');

        $cmd = '/usr/bin/python /var/www/html/coins/python/duy/Coins/run_ruin.py  ' . ' --id ' . $id . ' > /dev/null &'  ;
        $output = exec($cmd);
        Reply::finish(true,'sucess' , $output);
    }

    public function stop_ruin(Request $request)
    {

        $id = $request->input('id', '');

        $cmd = 'pkill -f "/usr/bin/python /var/www/html/coins/python/duy/Coins/run_ruin.py --id ' . $id   ;
        $output = exec($cmd);
        Reply::finish(true,'sucess' , $output);
    }

    public function get_excel(Request $request)
    {
        $id = $request->input('id', '');

        $filePath = '/var/www/html/coins/python/duy/Coins/results/' . $id . '.xlsx';
        $content = file_get_contents($filePath);
        $base64EncodedContent = base64_encode($content);
        return response()->json([
            'result' => TRUE,
            'data' => $base64EncodedContent,
            'message' => 'excel'
        ]);
    }
    
   
   
    
}
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


class Log_profitbaseController extends Controller  
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

        $this->mainModel = Models::get('Admin/Log_profitbase');
        $this->tableName = LOG_PROFITBASE_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[LOG_PROFITBASE_ID] = true;

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
        $datas[LOG_PROFITBASE_ID] = uniqid();
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
            $datas[$key][LOG_PROFITBASE_ID] = uniqid();
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
        $suggestData = $this->mainModel->read([[[LOG_PROFITBASE_CAMPAIGN, 'contain', $datas]]], function($builder){$builder->limit(20);});
        $suggest = [];
        if($suggestData['result']){
             
            $suggest = $suggestData['data']->mapWithKeys(function ($item){
                return [$item->{LOG_PROFITBASE_ID} => $item->{LOG_PROFITBASE_CAMPAIGN}];
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
    
    //$$sorting$$
    public function sort(Request $request){
        $datas = $request->input('data', array());
    
        $sourceID = $datas['src_id'];
        $destID = $datas['dest_id'];
    
        $srcData = $this->mainModel->read([[[LOG_PROFITBASE_ID, '=', $sourceID]]]);
        if(isset($srcData['data'][0])) $srcData = $srcData['data'][0];
        $destData = $this->mainModel->read([[[LOG_PROFITBASE_ID, '=', $destID]]]);
        if(isset($destData['data'][0])) $destData = $destData['data'][0];
    
        if($srcData->{LOG_PROFITBASE_SYMBOL} > $destData->{LOG_PROFITBASE_SYMBOL}){
            $maxW = $srcData->{LOG_PROFITBASE_SYMBOL};
            $minW = $destData->{LOG_PROFITBASE_SYMBOL};
            $vector = 1;
        }else{
            $minW = $srcData->{LOG_PROFITBASE_SYMBOL};
            $maxW = $destData->{LOG_PROFITBASE_SYMBOL};
            $vector = 0;
        }
    
        $sortProjects = $this->mainModel->read( [[[LOG_PROFITBASE_SYMBOL, '>=', $minW], [LOG_PROFITBASE_SYMBOL, '<=', $maxW]]], function($db){$db->orderBy(LOG_PROFITBASE_SYMBOL, 'desc');});
        if(!$sortProjects['result']) return Reply::finish($sortProjects);
        $sortProjects = $sortProjects['data'];
    
        if($vector==1){
    
            $this->mainModel->edit( [
                DATA_KEY => [[[LOG_PROFITBASE_ID, '=', $sourceID]]],
                DATA_EDITOR => [LOG_PROFITBASE_SYMBOL=>0]
            ]);
    
            foreach ($sortProjects as $key=>$sortProject){
                if(isset($sortProjects[$key-1])){
                    $this->mainModel->edit( [
                        DATA_KEY => [[[LOG_PROFITBASE_ID, '=', $sortProject->{LOG_PROFITBASE_ID}]]],
                        DATA_EDITOR => [LOG_PROFITBASE_SYMBOL=>$sortProjects[$key-1]->{LOG_PROFITBASE_SYMBOL}]
                        ]);
                }
    
            }
    
            $this->mainModel->edit( [
                DATA_KEY => [[[LOG_PROFITBASE_ID, '=', $sourceID]]],
                DATA_EDITOR => [
                    LOG_PROFITBASE_SYMBOL=>$destData->{LOG_PROFITBASE_SYMBOL},
                    //SOLUTION_PARENT => $destData->{SOLUTION_PARENT},
                ]
                ]);
    
        }else{
    
            $this->mainModel->edit( [
                DATA_KEY => [[[LOG_PROFITBASE_ID, '=', $sourceID]]],
                DATA_EDITOR => [LOG_PROFITBASE_SYMBOL=>0]
            ]);
    
            for ($key = count($sortProjects)-1; $key >= 0; $key--){
    
                if(isset($sortProjects[$key+1])){
                    $this->mainModel->edit( [
                        DATA_KEY => [[[LOG_PROFITBASE_ID, '=', $sortProjects[$key]->{LOG_PROFITBASE_ID}]]],
                        DATA_EDITOR => [LOG_PROFITBASE_SYMBOL=>$sortProjects[$key+1]->{LOG_PROFITBASE_SYMBOL}]
                        ]);
                }
    
            }
    
            $this->mainModel->edit( [
                DATA_KEY => [[[LOG_PROFITBASE_ID, '=', $sourceID]]],
                DATA_EDITOR => [
                    LOG_PROFITBASE_SYMBOL => $destData->{LOG_PROFITBASE_SYMBOL},
                    //SOLUTION_PARENT => $destData->{SOLUTION_PARENT},
                ]
                ]);
    
        }
    
        Reply::finish(true, 'Success', '');
    
    }
    
    //$$/sorting$$
    
   
   
    
}
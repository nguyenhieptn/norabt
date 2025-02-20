<?php
namespace App\Http\Controllers\Mailer;

use App\Helpers\Auth\Role;
use App\Helpers\DB\Models;
use App\Helpers\Mailer\MailFunction;
use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use App\Helpers\Request\Reply;


class Mailer_configController extends Controller  
{

    function __construct()
    {
        parent::__construct();
        $this->mainModel = Models::get('Mailer/Mailer_config');
        $this->viewblade = 'reactjs.reactjs';
        
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[MAIL_ID] = true;
        if(!Role::checkRoot()) Reply::finish(false, ERROR_PERMISSION, ['data'=>'Please login by other account']); 
        
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
        $datas[MAIL_ID] = uniqid();
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
            $datas[$key][MAIL_ID] = uniqid();
        }
        Reply::finish($this->mainModel->add($datas)); 
    }

    public function addGetIds(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        foreach ($datas as $key=>$val){
            $datas[$key] = array_diff_key($datas[$key], $this->dependCols);
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
        $mapData[MAIL_ACTIVE] = [0=>'Unactive', 1=>'Active'];
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

    public function test(){
        return MailFunction::send([
            'to' => ['vietlinhvu007@gmail.com'],
            'html' => '<p>test</p>',
        ]);
    }
    
}
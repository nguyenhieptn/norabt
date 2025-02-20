<?php
namespace App\Http\Controllers\Admin;

use App\Helpers\Admin\Services;
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


class Testnet_campaignController extends Controller  
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

        $this->mainModel = Models::get('Admin/Testnet_campaign');
        $this->tableName = TESTNET_CAMPAIGN_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[TESTNET_ID] = true;

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
        $datas[TESTNET_ID] = uniqid();
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
            $datas[$key][TESTNET_ID] = uniqid();
        }
        $result = $this->mainModel->add($datas);
        if(!$result['result']) Reply::finish($result);
        Reply::finish(true, 'success', $datas);
    }

    public function drop(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        if(!Checker::validate($datas[TESTNET_ID], 'Number')) return Reply::make(false, 'Wrong format');
        $datas =  $this->mainModel->keyToCondition($datas);
        $dropResult = $this->mainModel->drop([$datas]);
        Reply::finish($dropResult);
    }

    public function drops(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        foreach ($datas as $key=>$data){
            if(!Checker::validate($data[TESTNET_ID], 'Number')) return Reply::make(false, 'Wrong format');
            $datas[$key] =  $this->mainModel->keyToCondition($data);
        }
        $result = $this->mainModel->drop($datas);
        Reply::finish($result);
    }

    public function edit(Request $request)
    {
        $datas = $request->all();
        if(count($datas[DATA_KEY]) == 0) Reply::finish(false, "Can not edit all");
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
        $mapData[TESTNET_SYMBOL] = Edge::mapping(Models::get('Admin/Watchlist'), null, WL_SYMBOL, WL_SYMBOL, null, function($db){
            $db->orderBy(WL_SYMBOL, 'DESC');
        });
        $mapData[TESTNET_SYMBOL]['all'] = 'All';
        $mapData[TESTNET_STRATEGY] = Edge::mapping(Models::get('Admin/Strategies'), null, STRATEGY_ID, STRATEGY_NAME, null, function($db){
            $db->orderBy(STRATEGY_NAME, 'DESC');
        });
        $mapData[TESTNET_ACCOUNT] = Edge::mapping(Models::get('Admin/Testnet_account'), null, TESTNET_ACCOUNT_ID, TESTNET_ACCOUNT_NAME,null, function($db){

            if(!Role::checkRoot()){
                $db->where(TESTNET_ACCOUNT_USER, '=', Auth::user()->{AUTHEN_ID});
            } 
           
        });
        $mapData[TESTNET_SIDE] = ['BOTH' => 'BOTH', 'LONG' => 'LONG', 'SHORT' => 'SHORT', 'NONE' => 'NONE'];
        $mapData[TESTNET_COMPOUND] = ['0' => 'Disable', '1' => 'Enable'];
        $mapData[TESTNET_ACTIVE] = ['0' => 'Disable', '1' => 'Active'];
        Reply::finish(true, 'Success', $mapData);
    }

    public function suggest(Request $request)
    {
        $datas = $request->input('search', '');
        $suggestData = $this->mainModel->read([[[TESTNET_NAME, 'contain', $datas]]], function($builder){$builder->limit(20);});
        $suggest = [];
        if($suggestData['result']){
             
            $suggest = $suggestData['data']->mapWithKeys(function ($item){
                return [$item->{TESTNET_ID} => $item->{TESTNET_NAME}];
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
        foreach($responseData['data'][DATA_TABLE] as $key => $val){
            $responseData['data'][DATA_TABLE][$key]->{'testnet_start'} = Services::isActive('testnet_account@'. $val->{TESTNET_ACCOUNT});
        }
        Reply::finish($responseData);
    }

    // public function stopEventService(Request $request){
    //     $campaign = $request->input('campaign');
    //     if(!Checker::validate($campaign, 'Number')) return Reply::make(false, 'Wrong format');
    //     $result = exec('sudo systemctl stop testnet_start@'.$campaign);
    //     $this->mainModel->edit([
    //         DATA_KEY => [[[TESTNET_ID, '=', $campaign]]],
    //         DATA_EDITOR => [TESTNET_STOP_TIME => time()],
    //     ]);
    //     return Reply::make(true, 'success', $result);

    // }

    // public function startEventService(Request $request){
    //     $campaign = $request->input('campaign');
    //     if(!Checker::validate($campaign, 'Number')) return Reply::make(false, 'Wrong format');
    //     $result = exec('sudo systemctl restart testnet_start@'.$campaign);
    //     $this->mainModel->edit([
    //         DATA_KEY => [[[TESTNET_ID, '=', $campaign]]],
    //         DATA_EDITOR => [TESTNET_START_TIME => time(), TESTNET_STOP_TIME => null],
    //     ]);
    //     return Reply::make(true, 'success', $result);

    // }


    //
    
    //
    
   
   
    
}
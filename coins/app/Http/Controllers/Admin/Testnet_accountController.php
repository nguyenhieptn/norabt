<?php
namespace App\Http\Controllers\Admin;

use App\Helpers\Admin\Services;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

use App\Helpers\Auth\Role;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use App\Helpers\Uploader\FileFunc;
use App\Helpers\Token\JWToken;
use App\Http\Controllers\Controller;
use App\Helpers\DB\Edge;


class Testnet_accountController extends Controller  
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

        $this->mainModel = Models::get('Admin/Testnet_account');
        $this->tableName = TESTNET_ACCOUNT_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[TESTNET_ACCOUNT_ID] = true;

        if(!Role::checkMonitor()) Reply::finish(false, ERROR_PERMISSION, ''); 
        
    }

    public function add(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas = array_diff_key($datas, $this->dependCols);
        $datas[TESTNET_ACCOUNT_USER] = Auth::user()->{AUTHEN_ID} ;
        $result = $this->mainModel->add([$datas]);
        if(!$result['result']) Reply::finish($result);
        Reply::finish(true, 'success', $datas);
    }

    public function addGetId(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas = array_diff_key($datas, $this->dependCols);
        $datas[TESTNET_ACCOUNT_ID] = uniqid();
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
            $datas[$key][TESTNET_ACCOUNT_ID] = uniqid();
        }
        $result = $this->mainModel->add($datas);
        if(!$result['result']) Reply::finish($result);
        Reply::finish(true, 'success', $datas);
    }

    public function drop(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        exec('sudo systemctl stop testnet_account@'.$datas[TESTNET_ACCOUNT_ID]);
        $datas =  $this->mainModel->keyToCondition($datas);
        $dropResult = $this->mainModel->drop([$datas]);
        Reply::finish($dropResult);
    }

    public function drops(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        foreach ($datas as $key=>$data){
            exec('sudo systemctl stop testnet_account@'.$data[TESTNET_ACCOUNT_ID]);
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
        $mapData[TESTNET_ACCOUNT_COMPOUND] = [1 => 'Enable', 0 => 'Disable'];
        $mapData[TESTNET_ACCOUNT_MARGIN_TYPE] = ['ISOLATE' => 'ISOLATE', 'CROSS' => 'CROSS'];
        $mapData[TESTNET_ACCOUNT_TELE_BOT] = Edge::mapping(Models::get('Admin/Tele_bot'), null, TELE_BOT_ID, TELE_BOT_NAME);
        $mapData[TESTNET_ACCOUNT_TELE_GROUP_NOTICE] = Edge::mapping(Models::get('Admin/Tele_group'), null, TELE_GROUP_ID, TELE_GROUP_NAME, null);
        $mapData[TESTNET_ACCOUNT_TELE_GROUP_SUMMARY] = Edge::mapping(Models::get('Admin/Tele_group'), null, TELE_GROUP_ID, TELE_GROUP_NAME, null);
        $mapData[TESTNET_ACCOUNT_TELE_GROUP_ERROR] = Edge::mapping(Models::get('Admin/Tele_group'), null, TELE_GROUP_ID, TELE_GROUP_NAME, null);
        $mapData[TESTNET_ACCOUNT_USER] = Edge::mapping(Models::get('Auth/Authentication'), null, AUTHEN_ID, AUTHEN_USERNAME , null , function($db){

            if(!Role::checkRoot()){
                $db->where(AUTHEN_ID, '=', Auth::user()->{AUTHEN_ID});
            } 
           
        });

       
        Reply::finish(true, 'Success', $mapData);
    }

    public function suggest(Request $request)
    {
        $datas = $request->input('search', '');
        $suggestData = $this->mainModel->read([[[TESTNET_ACCOUNT_NAME, 'contain', $datas]]], function($builder){$builder->limit(20);});
        $suggest = [];
        if($suggestData['result']){
             
            $suggest = $suggestData['data']->mapWithKeys(function ($item){
                return [$item->{TESTNET_ACCOUNT_ID} => $item->{TESTNET_ACCOUNT_NAME}];
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
                $db->where(TESTNET_ACCOUNT_USER, '=', Auth::user()->{AUTHEN_ID});
            } 
           
        });
        if(!$responseData['result']) Reply::finish($responseData);
        foreach($responseData['data'][DATA_TABLE] as $key => $val){
            $responseData['data'][DATA_TABLE][$key]->{'testnet_start'} = Services::isActive('testnet_account@'. $val->{TESTNET_ACCOUNT_ID});
        }
        Reply::finish($responseData);
    }


    public function restartTrading(Request $request)
    {
        $id = $request->input('account');
        $result = exec('sudo systemctl restart testnet_account@' . $id);
        // $tradesModel = Models::get('Admin/Testnet_campaign');

        // $trades = $tradesModel->read([], function ($db) use ($id) {
        //     $db->whereIn(TESTNET_ID, $id);
        // });
        // if (!$trades['result']) return $trades;
        // $trades = $trades['data'];

        // foreach ($trades as $trade) {

        //     $result = exec('sudo systemctl restart testnet_start@' . $trade->{TESTNET_ID});
        //     $tradesModel->edit([
        //         DATA_KEY => [[[TESTNET_ID, '=', $trade->{TESTNET_ID}]]],
        //         DATA_EDITOR => [TESTNET_STOP_TIME => null, TESTNET_START_TIME => time()]
        //     ]);
        // }
        Reply::finish(true, 'Success');
    }

    public function stopTrading(Request $request)
    {

        $id = $request->input('account');
        $result = exec('sudo systemctl stop testnet_account@' . $id);

        // $tradesModel = Models::get('Admin/Testnet_campaign');
        // $trades = $tradesModel->read([[[TESTNET_ACCOUNT, '=', $id]]]);
        // if (!$trades['result']) return $trades;
        // $trades = $trades['data'];
        // $tradeIds = [];
        // foreach ($trades as $trade) {
        //     if (Services::isActive('testnet_start@' . $trade->{TESTNET_ID})) {
        //         $result = exec('sudo systemctl stop testnet_start@' . $trade->{TESTNET_ID});
        //         $tradesModel->edit([
        //             DATA_KEY => [[[TESTNET_ID, '=', $trade->{TESTNET_ID}]]],
        //             DATA_EDITOR => [TESTNET_STOP_TIME => time()]
        //         ]);
        //         $tradeIds[] = $trade->{TESTNET_ID};
        //     }
        // }
        Reply::finish(true, 'Success');
    }

    public function cleanData(Request $request){
        $id = $request->input('id');
        $delResult = Models::get('Admin/Testnet_results')->drop([[[TESTNET_RESULT_ACCOUNT, '=', $id]]]);
        if(!$delResult['result']) return $delResult;
        return $delResult = Models::get('Admin/Testnet_track_balance')->drop([[[TESTNET_TRACK_BL_ACCOUNT, '=', $id]]]);
    }


    public function clone(Request $request){
        $id = $request->input('id');
        $data = $this->mainModel->read([[[TESTNET_ACCOUNT_ID, '=', $id]]]);
        if(!$data['result'] || !isset($data['data'][0])) return Reply::finish(false, "No account");
        $account = (array)$data['data'][0];
       
        unset($account[TESTNET_ACCOUNT_ID]);
        $account[TESTNET_ACCOUNT_NAME] .= '_clone_' . makeId();
        
        $result = $this->mainModel->add([$account]);
        if(!$result['result']) return $result;

        $newid = $this->mainModel->getLastId();

        $campaignModel = Models::get('Admin/Testnet_campaign');
        $oldCampaign = $campaignModel->read([[[TESTNET_ACCOUNT, '=', $id]]]);
        if(!$oldCampaign['result']) return $oldCampaign;

        $oldCampaign = $oldCampaign['data']->toArray();

        $newCampaign = [];

        foreach($oldCampaign as $camp){
            $camp = (array)$camp;
            unset($camp[TESTNET_ID]);
            $camp[TESTNET_ACCOUNT] = $newid;
            $newCampaign[] = $camp;
        }

        return $campaignModel->add($newCampaign);



    }



    //
    
    //
    
   
   
    
}
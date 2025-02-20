<?php
namespace App\Http\Controllers\Admin;

use App\Helpers\Admin\DataHelper;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

use App\Helpers\Auth\Role;
use App\Helpers\DB\Models;
use App\Helpers\Request\Reply;
use App\Helpers\Uploader\FileFunc;
use App\Helpers\Token\JWToken;
use App\Http\Controllers\Controller;
use App\Helpers\DB\Edge;
use Illuminate\Support\Facades\DB;

class Lab_strategiesController extends Controller  
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

        $this->mainModel = Models::get('Admin/Lab_strategies');
        $this->tableName = LAB_STRATEGIES_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[LAB_STRATEGY_ID] = true;

        // if(!Role::checkAdmin()) Reply::finish(false, ERROR_PERMISSION, ['data'=>'Please login by other account']);  
        
    }

    public function add(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas = array_diff_key($datas, $this->dependCols);
        $id = intval($this->mainModel->db()->max(LAB_STRATEGY_ID)) + 1;
        $datas[LAB_STRATEGY_ID] = $id;
        $datas[LAB_STRATEGY_USER] = Auth::user()->{AUTHEN_ID} ;
        $result = $this->mainModel->add([$datas]);
        if(!$result['result']) Reply::finish($result);

        $children = get($datas['children'], null);
        if($children){
           
            $straConModel = Models::get('Admin/Lab_strategy_container');
            $addData = [];
            foreach($children as $child){
                unset($child[LAB_STRA_CON_ID]);
                if($child[LAB_STRA_CON_CHILD] == '') continue;
                $child[LAB_STRA_CON_CONTAINER] = $id;
                $addData[] = $child;
            }
            $straConModel->drop([[[LAB_STRA_CON_CONTAINER, '=', $id]]]);
            $straConModel->add($addData);
        }

        Reply::finish(true, 'success', $datas);
    }

    public function addGetId(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas = array_diff_key($datas, $this->dependCols);
        $datas[LAB_STRATEGY_ID] = uniqid();
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
            $datas[$key][LAB_STRATEGY_ID] = uniqid();
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
        $id = $datas[DATA_KEY][LAB_STRATEGY_ID];
        $datas[DATA_KEY] =  array($this->mainModel->keyToCondition($datas[DATA_KEY]));
        $datas[DATA_EDITOR] = array_diff_key($datas[DATA_EDITOR], $this->dependCols);
        $editResult = $this->mainModel->edit($datas);
        if(!$editResult['result']) return $editResult;

        $children = get($datas['children'], null);
        if($children){
           
            $straConModel = Models::get('Admin/Lab_strategy_container');
            $addData = [];
            foreach($children as $child){
                unset($child[LAB_STRA_CON_ID]);
                if($child[LAB_STRA_CON_CHILD] == '') continue;
                $child[LAB_STRA_CON_CONTAINER] = $id;
                $addData[] = $child;
            }
            $straConModel->drop([[[LAB_STRA_CON_CONTAINER, '=', $id]]]);
            $straConModel->add($addData);
        }

        Reply::finish($editResult);
    }

    public function edits(Request $request)
    {
        $datas = $request->all();
        foreach ($datas[DATA_KEY] as $key=>$data){
            $datas[DATA_KEY][$key] =  $this->mainModel->keyToCondition($data);
        }
        $editData = [];
        if(isset($datas[DATA_EDITOR][LAB_STRATEGY_GROUP])) $editData[LAB_STRATEGY_GROUP] = $datas[DATA_EDITOR][LAB_STRATEGY_GROUP];
        if(isset($datas[DATA_EDITOR][LAB_STRATEGY_USER])) $editData[LAB_STRATEGY_USER] = $datas[DATA_EDITOR][LAB_STRATEGY_USER];
        $datas[DATA_EDITOR] = $editData;
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

    public function getGroup(){
        return Reply::make(true, 'success', DataHelper::getLabGroup());
    }


    // public function editGroup(Request $request){
    //     $newGroup = $request->input('new_group', '');
    //     $oldGroup = $request->input('old_group', '');
    //     $model = $this->mainModel->db();
    //     return $this->mainModel->edit([
    //         DATA_KEY => [[[LAB_STRATEGY_GROUP, '=', $oldGroup]]],
    //         DATA_EDITOR => [LAB_STRATEGY_GROUP => $newGroup]
    //     ]);
    // }

    public function mapping(){
        $mapData = [];
        $mapData[LAB_STRATEGY_GROUP] =  DataHelper::getLabGroup();
        $mapData[LAB_STRATEGY_BASEPROFIT_BASEON] = ['close' => 'Close Price', 'ema5_1m' => 'EMA5 1M', 'ema5_3m' => 'EMA5 3M', 'ema5_15m' => 'EMA5 15M'];
        $mapData[LAB_STRATEGY_USER] = Edge::mapping(Models::get('Auth/Authentication'), null, AUTHEN_ID, AUTHEN_USERNAME , null , function($db){

            if(!Role::checkRoot()){
                $db->where(AUTHEN_ID, '=', Auth::user()->{AUTHEN_ID});
            } 
           
        });
        $mapData[LAB_STRATEGY_CONTENT] = $this->getStrategyOptions();
        Reply::finish(true, 'Success', $mapData);
    }

    public function suggest(Request $request)
    {
        $datas = $request->input('search', '');
        $suggestData = $this->mainModel->read([[[LAB_STRATEGY_NAME, 'contain', $datas]]], function($builder){$builder->limit(20);});
        $suggest = [];
        if($suggestData['result']){
             
            $suggest = $suggestData['data']->mapWithKeys(function ($item){
                return [$item->{LAB_STRATEGY_ID} => $item->{LAB_STRATEGY_NAME}];
            });
        }
        Reply::finish(true, '', $suggest);
    }

    public function filter(Request $request)
    {
        $datas = $request->all();
        $datas[FLAG_FILTER_LOGIC] = 'and';
        $group = get($datas['group'], '');
        $responseData = $this->mainModel->filter($datas, function($db)  use($group){
            $db->where(LAB_STRATEGY_GROUP, '=', $group);
            if(!Role::checkRoot()){
                $db->where(LAB_STRATEGY_USER, '=', Auth::user()->{AUTHEN_ID});
            } 
           
        });
        if(!$responseData['result']) Reply::finish($responseData);
        Reply::finish($responseData);
    }

    private function getStrategyOptions(){
        try {
            $database = 'backtest_data';
            $this->btModel = DB::connection($database);
            $returnData = [];
            foreach ($this->btModel->getMongoDB()->listCollections() as $coll){
                $source = $coll->getName();
                $lastRows = $this->btModel->collection($source)->orderBy('_id', 'DESC')->limit(1)->get();
                $fields = [];
                if($lastRows->count() > 0){
                    $lastRows = $lastRows[0];
                    unset($lastRows['_id']);
                    unset($lastRows['symbol']);
                    // $returnData += array_keys($lastRows);
                    foreach($lastRows as $key => $val){
                        $returnData[] = ['value' => $key, 'meta' => $source];
                    }
                }
            }

            $col = ['timelife','interval','takeprofit','stoploss','step_profit','back_profit','baseprofit','baseprofit_baseon','margin','allow_negative_price_rate',
                    'after_stoploss','enter_step','enter_package','baseprofit','stoploss','margin','enter_price'];
            foreach($col as $coll){
                $returnData[] = ['value' => $coll, 'meta' => 'param'];
            }
            return $returnData;
            
        } catch (\Exception $th) {
            return Reply::make(false, $th->getMessage());
        }
        
    }


    //
    
    //
    
   
   
    
}
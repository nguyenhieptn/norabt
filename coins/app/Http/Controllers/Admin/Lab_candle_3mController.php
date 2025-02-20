<?php
namespace App\Http\Controllers\Admin;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

use App\Helpers\Auth\Role;
use App\Helpers\Control\Ctrl;
use App\Helpers\DB\Edge;
use App\Helpers\DB\Models;
use Illuminate\Support\Facades\DB;
use App\Helpers\Request\Reply;
use App\Helpers\Uploader\FileFunc;
use App\Helpers\Token\JWToken;
use App\Http\Controllers\Controller;
use App\Helpers\Admin\LabSocket;


class Lab_candle_3mController extends Controller  
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

        $this->mainModel = Models::get('Admin/Lab_candle_3m');
        $this->mainModel->query_builder = DB::connection(Ctrl::get('control_lab_db', 'coin_crawler'))->table('lab_candle_3m');
        $this->tableName = LAB_CANDLE_3M_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[LAB_CANDLE_3M_ID] = true;

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
        $datas[LAB_CANDLE_3M_ID] = uniqid();
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
            $datas[$key][LAB_CANDLE_3M_ID] = uniqid();
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
        $mapData[LAB_CANDLE_3M_SYMBOL] = Edge::mapping(Models::get('Admin/Lab_watchlist'), null, LAB_WL_SYMBOL, LAB_WL_SYMBOL);
        Reply::finish(true, 'Success', $mapData);
    }

    public function suggest(Request $request)
    {
        $datas = $request->input('search', '');
        $suggestData = $this->mainModel->read([[[LAB_CANDLE_3M_SYMBOL, 'contain', $datas]]], function($builder){$builder->limit(20);});
        $suggest = [];
        if($suggestData['result']){
             
            $suggest = $suggestData['data']->mapWithKeys(function ($item){
                return [$item->{LAB_CANDLE_3M_ID} => $item->{LAB_CANDLE_3M_SYMBOL}];
            });
        }
        Reply::finish(true, '', $suggest);
    }

    public function filter(Request $request)
    {
        $datas = $request->all();
        $datas[FLAG_FILTER_LOGIC] = 'and';
        // $symbol = $datas['symbol'];
        $responseData = $this->mainModel->filter($datas);
        if(!$responseData['result']) Reply::finish($responseData);
        Reply::finish($responseData);
    }

    public function get(Request $request){
        $data = $request->input('data', []);
        $limit = $request->input('limit', null);
        $skip = $request->input('skip', null);
        $orderBy = $request->input('orderBy', null);
        $orderAsc = $request->input('asc', true);

        $selectColumn = array_keys($this->mainModel->struct);

        $result = $this->mainModel->read($data, function($db) use($limit, $skip, $orderBy, $orderAsc){
            if($orderBy !== null) $db->orderBy($orderBy, $orderAsc ? 'ASC' : 'DESC');
            if($skip !== null) $db->skip($skip);
            if($limit !== null) $db->limit($limit);
        }, false, $selectColumn);

        return $result;
    }


    // get show db from setting_lab
    public function showdb(Request $request)
    {
        $db_lab = $request->input('control_lab_db', null);
        $remote_server = $request->input('remote_server', 'local');
       
        $result=[];
        if($db_lab){
            if($remote_server == "" || $remote_server == 'local'){
                $this->Model = Models::get('Admin/Lab_candle_15m');
                $this->Model->query_builder = DB::connection($db_lab)->table('lab_candle_15m');

                $symbol = array( $this->Model->db()->select(LAB_CANDLE_15M_SYMBOL)->distinct()->get());

                $symbol = $symbol[0];

                
                
                foreach($symbol as $row){

                    $findSymbol = $row->{LAB_CANDLE_15M_SYMBOL};

                    $max = $this->Model->read([[[LAB_CANDLE_15M_SYMBOL, '=', $findSymbol], [LAB_CANDLE_15M_STARTPOINT, '=', null]]], function($builder){
                        $builder->orderBy(LAB_CANDLE_15M_CLOSE_TIME, 'desc')->first();
                    });

            

                    $min = $this->Model->read([[[LAB_CANDLE_15M_SYMBOL, '=', $findSymbol], [LAB_CANDLE_15M_STARTPOINT, '=', null]]], function($builder){
                        $builder->orderBy(LAB_CANDLE_15M_CLOSE_TIME, 'asc')->first();
                    });

                    if($max['result'] && $min['result'] ){
                
                        $max = $max['data'][0]->{LAB_CANDLE_15M_CLOSE_TIME};
                        $min = $min['data'][0]->{LAB_CANDLE_15M_CLOSE_TIME};
                    
                    }

                    $result[] = array(
                        'symbol' =>  $findSymbol,
                        'startTime' => $min,
                        'endTime' => $max,

                    );

                
                    
                }
            }else{
                $result = LabSocket::makeRemoteQuery($remote_server, 'account', 'checkData', ['database'=>$db_lab]);
                // var_dump($result['result']);
                if($result['result']){
                    $data = str_replace('\'','"', $result['data']);
                    // var_dump($data);
                    $result = json_decode($data);
                    // var_dump($result);
                }
            }
            return Reply::make(true, 'success',    $result );

        }
    }



    //
    
    //
    
   
   
    
}
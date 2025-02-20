<?php

namespace App\Http\Controllers\Admin;

use App\Helpers\Admin\Binancer;
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


class AccountsController extends Controller
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

        $this->mainModel = Models::get('Admin/Accounts');
        $this->tableName = ACCOUNTS_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[ACCOUNT_ID] = true;

        if(!Role::checkMonitor()) Reply::finish(false, ERROR_PERMISSION, ['data'=>'Please login by other account']); 

    }

    public function add(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas = array_diff_key($datas, $this->dependCols);
        $result = $this->mainModel->add([$datas]);
        if (!$result['result']) Reply::finish($result);
        Reply::finish(true, 'success', $datas);
    }

    public function addGetId(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        $datas = array_diff_key($datas, $this->dependCols);
        $datas[ACCOUNT_ID] = uniqid();
        $result = $this->mainModel->add([$datas]);
        if (!$result['result']) Reply::finish($result);
        Reply::finish(true, 'success', $datas);
    }

    public function adds(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        foreach ($datas as $key => $val) {
            $datas[$key] = array_diff_key($datas[$key], $this->dependCols);
        }
        Reply::finish($this->mainModel->add($datas));
    }

    public function addGetIds(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        foreach ($datas as $key => $val) {
            $datas[$key] = array_diff_key($datas[$key], $this->dependCols);
            $datas[$key][ACCOUNT_ID] = uniqid();
        }
        $result = $this->mainModel->add($datas);
        if (!$result['result']) Reply::finish($result);
        Reply::finish(true, 'success', $datas);
    }

    public function drop(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        if(!Checker::validate($datas[ACCOUNT_ID], 'Number')) return Reply::make(false, "Wrong format");
        exec('sudo systemctl stop binance_update@' . $datas[ACCOUNT_ID]);
        $datas =  $this->mainModel->keyToCondition($datas);
        $dropResult = $this->mainModel->drop([$datas]);
        Reply::finish($dropResult);
    }

    public function drops(Request $request)
    {
        $variables = $request->all();
        $datas = get($variables['data'], []);
        foreach ($datas as $key => $data) {
            if(!Checker::validate($data[ACCOUNT_ID], 'Number')) return Reply::make(false, "Wrong format");
            exec('sudo systemctl stop binance_update@' . $data[ACCOUNT_ID]);
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
        foreach ($datas[DATA_KEY] as $key => $data) {
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

    public function mapping()
    {
        $mapData = [];
        $mapData[ACCOUNT_TYPE] = (object)[ACCOUNT_TYPE_LAB => 'LAB', ACCOUNT_TYPE_REAL => 'Official'];
        $mapData[ACCOUNT_USER] = Edge::mapping(Models::get('Auth/Authentication'), null, AUTHEN_ID, AUTHEN_USERNAME);
        $mapData[ACCOUNT_COMPOUND] = ['0' => 'Disabled', '1' => 'Enabled'];
        Reply::finish(true, 'Success', $mapData);
    }

    public function suggest(Request $request)
    {
        $datas = $request->input('search', '');
        $suggestData = $this->mainModel->read([[[ACCOUNT_NAME, 'contain', $datas]]], function ($builder) {
            $builder->limit(20);
        });
        $suggest = [];
        if ($suggestData['result']) {

            $suggest = $suggestData['data']->mapWithKeys(function ($item) {
                return [$item->{ACCOUNT_ID} => $item->{ACCOUNT_NAME}];
            });
        }
        Reply::finish(true, '', $suggest);
    }

    public function filter(Request $request)
    {
        $datas = $request->all();
        $datas[FLAG_FILTER_LOGIC] = 'and';
        $responseData = $this->mainModel->filter($datas);
        if (!$responseData['result']) Reply::finish($responseData);
        foreach ($responseData['data'][DATA_TABLE] as $key => $val) {
            $responseData['data'][DATA_TABLE][$key]->{'update_service'} = Services::isActive('binance_update@' . $val->{ACCOUNT_ID});
        }
        Reply::finish($responseData);
    }

    public function getAccount(Request $request)
    {
        ob_start();
        $id = $request->input('id');
        $binancer = new Binancer($id);
        $info = $binancer->getAccountInfo();
        if (!$info['result']) Reply::finish(false, 'Can not get account info');
        $info = $info['data'];
        ob_end_clean();
        return Reply::make(true, 'success', ['availableBalance' => $info['totalWalletBalance'], 'reserve' => doubleval($binancer->getAccount()->{ACCOUNT_RESERVE})]);
    }


    // get postions from binance 
    public function getPositions(Request $request)
    {
        ob_start();
        $id = $request->input('id');
        $binancer = new Binancer($id);
        $info = $binancer->getAccountInfo();
        if (!$info['result']) Reply::finish(false, 'Can not get account info');
        $info = $info['data'];

        $positions = (array)$info['positions'];

        $result = [];
        foreach($positions as $row){
            if($row['positionAmt'] != 0) $result[] = $row;
        }
        ob_end_clean();
        return Reply::make(true, 'success',  ['positions' =>   $result ]);
    }

    //get trade of symbol from binance
    public function getTrade(Request $request)
    {
        ob_start();
        $id = $request->input('id');
        $symbol = $request->input('symbol');
        $startTime = $request->input('startTime' , null);
        $endTime = $request->input('endTime',null);
        $binancer = new Binancer($id);

        $info = $binancer->getAllTrade($symbol,$startTime,$endTime);
        if (!$info['result']) Reply::finish(false, 'Can not get account info');

        $info = $info['data'];

        ob_end_clean();
        return Reply::make(true, 'success',    $info );
    }

    
    //get trade of symbol from binance
    public function getIncom(Request $request)
    {
        ob_start();
        $id = $request->input('id');
        $incomType = $request->input('incomeType' , null);
        $binancer = new Binancer($id);

        $info = $binancer->getIncomeHistory($incomType , time() *1000 - 86400000 * 365 , time()*1000);
        if (!$info['result']) Reply::finish(false, 'Can not get account incom ');
        $info = $info['data'];
       
        ob_end_clean();
        return Reply::make(true, 'success',    $info );
    }



    public function startService(Request $request)
    {
        ob_start();
        $id = $request->input('id');
        if(!Checker::validate($id, 'Number')) return Reply::make(false, "Wrong format");
        $result = exec('sudo systemctl restart binance_update@' . $id);
        $this->mainModel->edit([
            DATA_KEY => [[[ACCOUNT_ID, '=', $id]]],
            DATA_EDITOR => [ACCOUNT_START_TIME => time(), ACCOUNT_STOP_TIME => null],
        ]);
        return Reply::make(true, 'success', $result);
    }

    public function stopService(Request $request)
    {
        ob_start();
        $id = $request->input('id');
        if(!Checker::validate($id, 'Number')) return Reply::make(false, "Wrong format");
        $trades = Models::get('Admin/Trades')->read([[[TRADE_ACCOUNT, '=', $id]]]);
        if (!$trades['result']) return $trades;
        $trades = $trades['data'];

        foreach ($trades as $trade) {
            $result = exec('sudo systemctl stop binance_event@' . $trade->{TRADE_SYMBOL} . '_' . $id);
        }

        $result = exec('sudo systemctl stop binance_update@' . $id);
        $this->mainModel->edit([
            DATA_KEY => [[[ACCOUNT_ID, '=', $id]]],
            DATA_EDITOR => [ACCOUNT_STOP_TIME => time()],
        ]);
        ob_end_clean();
        return Reply::make(true, 'success', $result);
    }

    public function restartTrading(Request $request)
    {
        $id = $request->input('id');
        $tradesModel = Models::get('Admin/Trades');

        $trades = $tradesModel->read([], function ($db) use ($id) {
            $db->whereIn(TRADE_ID, $id);
        });
        if (!$trades['result']) return $trades;
        $trades = $trades['data'];

        foreach ($trades as $trade) {

            $result = exec('sudo systemctl restart binance_event@' . $trade->{TRADE_SYMBOL} . '_' .  $trade->{TRADE_ACCOUNT});
            $tradesModel->edit([
                DATA_KEY => [[[TRADE_ID, '=', $trade->{TRADE_ID}]]],
                DATA_EDITOR => [TRADE_STOP_TIME => null, TRADE_START_TIME => time()]
            ]);
        }
        Reply::finish(true, 'Success');
    }

    public function stopTrading(Request $request)
    {

        $id = $request->input('id');
        if(!Checker::validate($id, 'Number')) return Reply::make(false, "Wrong format");
        $tradesModel = Models::get('Admin/Trades');
        $trades = $tradesModel->read([[[TRADE_ACCOUNT, '=', $id]]]);
        if (!$trades['result']) return $trades;
        $trades = $trades['data'];
        $tradeIds = [];
        foreach ($trades as $trade) {
            if (Services::isActive('binance_event@' . $trade->{TRADE_SYMBOL} . '_' . $trade->{TRADE_ACCOUNT})) {
                $result = exec('sudo systemctl stop binance_event@' . $trade->{TRADE_SYMBOL} . '_' . $trade->{TRADE_ACCOUNT});
                $tradesModel->edit([
                    DATA_KEY => [[[TRADE_ID, '=', $trade->{TRADE_ID}]]],
                    DATA_EDITOR => [TRADE_STOP_TIME => time()]
                ]);
                $tradeIds[] = $trade->{TRADE_ID};
            }
        }
        Reply::finish(true, 'Success', $tradeIds);
    }


    public function count()
    {
        return $this->mainModel->count();
    }








    //

    //




}

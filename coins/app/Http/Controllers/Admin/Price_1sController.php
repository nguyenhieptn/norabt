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


class Price_1sController extends Controller
{

    function __construct()
    {
        // Api for manage disks of system
        parent::__construct();

        $this->mainModel = Models::get('Admin/Price_1s');
        $this->tableName = PRICE_1S_TABLE;
        $this->mainModel->loadDepend();
        $this->dependCols = array_unique(array_column($this->mainModel->registerDepend, 1, 1));
        $this->dependCols[PRICE_1S_ID] = true;

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
        $datas[PRICE_1S_ID] = uniqid();
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
            $datas[$key][PRICE_1S_ID] = uniqid();
        }
        $result = $this->mainModel->add($datas);
        if (!$result['result']) Reply::finish($result);
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
        foreach ($datas as $key => $data) {
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
        Reply::finish(true, 'Success', $mapData);
    }

    public function suggest(Request $request)
    {
        $datas = $request->input('search', '');
        $suggestData = $this->mainModel->read([[[PRICE_1S_SYMBOL, 'contain', $datas]]], function ($builder) {
            $builder->limit(20);
        });
        $suggest = [];
        if ($suggestData['result']) {

            $suggest = $suggestData['data']->mapWithKeys(function ($item) {
                return [$item->{PRICE_1S_ID} => $item->{PRICE_1S_SYMBOL}];
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
        Reply::finish($responseData);
    }

    public function get(Request $request)
    {
        $data = $request->input('data', []);
        $limit = $request->input('limit', null);
        $skip = $request->input('skip', null);
        $orderBy = $request->input('orderBy', null);
        $orderAsc = $request->input('asc', true);

        $selectColumn = array_keys($this->mainModel->struct);

        $result = $this->mainModel->read($data, function ($db) use ($limit, $skip, $orderBy, $orderAsc) {
            if ($orderBy !== null) $db->orderBy($orderBy, $orderAsc ? 'ASC' : 'DESC');
            if ($skip !== null) $db->skip($skip);
            if ($limit !== null) $db->limit($limit);
        }, false, [
            PRICE_1S_ID,
            PRICE_1S_CLOSE,
            PRICE_1S_TIME
        ]);

        return $result;
    }

    public function getLineChart(Request $request)
    {
        $data = $request->input('data', []);
        $limit = $request->input('limit', null);
        $skip = $request->input('skip', null);
        $orderBy = $request->input('orderBy', null);
        $orderAsc = $request->input('asc', true);
        // $strategy = $request->input('strategy', null);
        $account = $request->input('account', null);
        $symbol = $request->input('symbol', null);
        $startTime = $request->input('startTime', null);

        $positionModel = Models::get('Admin/Testnet_results');
        $orderModel = Models::get('Admin/Testnet_order');
        $enterBaseModel = Models::Get('Admin/Testnet_enterbase');
        $profitBaseModel = Models::Get('Admin/Testnet_profitbase');

        $selectColumn = [
            TESTNET_RESULT_ID,
            TESTNET_RESULT_CAMPAIGN,
            TESTNET_RESULT_STRATEGY,
            TESTNET_RESULT_SYMBOL,
            TESTNET_RESULT_CHART,
            TESTNET_RESULT_ENTER_TIME,
            TESTNET_RESULT_ENTER_PRICE,
            TESTNET_RESULT_MATCHED_PRICE,
            TESTNET_RESULT_MATCHED_TIME,
            TESTNET_RESULT_MATCHED_QTY,
            TESTNET_RESULT_SELL_PRICE,
            TESTNET_RESULT_SELL_TIME,
            TESTNET_RESULT_PROFIT,
            TESTNET_RESULT_EVENT_PROFIT,
            TESTNET_RESULT_REAL_PROFIT,
            TESTNET_RESULT_PENDING,
            TESTNET_RESULT_PHASE,
            TESTNET_RESULT_BUDGET,
            TESTNET_RESULT_TYPE,
            TESTNET_RESULT_ACCOUNT
        ];

        $result = $this->mainModel->read($data, function ($db) use ($limit, $skip, $orderBy, $orderAsc) {
            if ($orderBy !== null) $db->orderBy($orderBy, $orderAsc ? 'ASC' : 'DESC');
            if ($skip !== null) $db->skip($skip);
            if ($limit !== null) $db->limit($limit);
        }, false, [
            PRICE_1S_ID,
            PRICE_1S_CLOSE,
            PRICE_1S_TIME
        ]);

        if (!$result['result']) return $result;
        $priceData = $result['data']->toArray();

        $positionData = [];
        $orderData = [];
        $enterBaseData = [];
        $profitBaseData = [];

        if (count($priceData) >= 100) {
            $endTime = $priceData[0]->{PRICE_1S_TIME};
            $startTime = $priceData[count($priceData) - 1]->{PRICE_1S_TIME};

            $positions = $positionModel->read([[
                // [TESTNET_RESULT_STRATEGY, '=', $strategy],
                [TESTNET_RESULT_ACCOUNT, '=', $account],
                [TESTNET_RESULT_SYMBOL, '=', $symbol],
                [TESTNET_RESULT_CHART, '>=', $startTime - 3*86400*1000],
                [TESTNET_RESULT_CHART, '<=', $endTime],
            ]], function ($db) {
                $db->orderBy(TESTNET_RESULT_CHART, 'DESC');
            }, false, $selectColumn);
            if (!$positions['result']) return $positions;
            $positions = $positions['data'];
            $ids = [];
            foreach ($positions as $position) {
                $ids[] = $position->{TESTNET_RESULT_ID};
                if($position->{TESTNET_RESULT_CHART} >= $startTime) $positionData[] = $position;
            }

            $orders = $orderModel->read([[
                [TESTNET_ORDER_TIME, '>=', $startTime],
                [TESTNET_ORDER_TIME, '<=', $endTime],
            ]], function ($db) use ($ids) {
                $db->whereIn(TESTNET_ORDER_ACTION, $ids)->orderBy(TESTNET_ORDER_TIME, 'DESC');
            });
            if (!$orders['result']) return $orders['result'];
            $orderData = $orders['data']->toArray();

            $enterBases = $enterBaseModel->read([[
                [ENTERBASE_TIME, '>=', $startTime],
                [ENTERBASE_TIME, '<=', $endTime],
            ]], function ($db) use ($ids) {
                $db->whereIn(ENTERBASE_ACTION, $ids)->orderBy(ENTERBASE_TIME, 'DESC');
            });
            if (!$enterBases['result']) return $enterBases['result'];
            $enterBaseData = $enterBases['data']->toArray();

            $profitBases = $profitBaseModel->read([[
                [PROFITBASE_TIME, '>=', $startTime],
                [PROFITBASE_TIME, '<=', $endTime],
            ]], function ($db) use ($ids) {
                $db->whereIn(PROFITBASE_ACTION, $ids)->orderBy(PROFITBASE_TIME, 'DESC');
            });
            if (!$profitBases['result']) return $profitBases['result'];
            $profitBaseData = $profitBases['data']->toArray();


        } else {

            $positions = $positionModel->read([[
                // [TESTNET_RESULT_STRATEGY, '=', $strategy],
                [TESTNET_RESULT_ACCOUNT, '=', $account],
                [TESTNET_RESULT_SYMBOL, '=', $symbol],
                [TESTNET_RESULT_CHART, '>=', $startTime - 3*86400*1000]
            ]], function ($db) {
                $db->orderBy(TESTNET_RESULT_CHART, 'DESC')->limit(1);
            }, false, $selectColumn);

            if (!$positions['result']) return $positions;
            $positions = $positions['data'];

            $ids = [];
            foreach ($positions as $position) {
                $ids[] = $position->{TESTNET_RESULT_ID};
                if($position->{TESTNET_RESULT_CHART} >= $startTime) $positionData[] = $position;
            }

            $orders = $orderModel->read([[[TESTNET_ORDER_TIME, '>=', $startTime]]], function ($db) use($ids) {
                $db->whereIn(TESTNET_ORDER_ACTION, $ids)->orderBy(TESTNET_ORDER_TIME, 'DESC');
            });
            if (!$orders['result']) return $orders['result'];
            $orderData = $orders['data']->toArray();


            $enterBases = $enterBaseModel->read([[[ENTERBASE_TIME, '>=', $startTime]]], function ($db) use($ids) {
                $db->whereIn(ENTERBASE_ACTION, $ids)->orderBy(ENTERBASE_TIME, 'DESC');
            });
            if (!$enterBases['result']) return $enterBases['result'];
            $enterBaseData = $enterBases['data']->toArray();

            $profitBases = $profitBaseModel->read([[[PROFITBASE_TIME, '>=', $startTime]]], function ($db) use($ids) {
                $db->whereIn(PROFITBASE_ACTION, $ids)->orderBy(PROFITBASE_TIME, 'DESC');
            });
            if (!$profitBases['result']) return $profitBases['result'];
            $profitBaseData = $profitBases['data']->toArray();
        }

        return Reply::make(true, 'Success', ['price' => $priceData, 'positions' => $positionData, 'orders' => $orderData, 'enterbase' => $enterBaseData, 'profitbase' => $profitBaseData]);
    }


    public function getLineChartExchange(Request $request)
    {
        $data = $request->input('data', []);
        $limit = $request->input('limit', null);
        $skip = $request->input('skip', null);
        $orderBy = $request->input('orderBy', null);
        $orderAsc = $request->input('asc', true);
        $account = $request->input('account', null);
        $symbol = $request->input('symbol', null);
        $startTime = $request->input('startTime', null);

        $positionModel = Models::get('Admin/Actions');
        $orderModel = Models::get('Admin/Orders');
        $enterBaseModel = Models::Get('Admin/Log_enterbase');
        $profitBaseModel = Models::Get('Admin/Log_profitbase');

        $selectColumn = [
            ACTION_ID,
            ACTION_STRATEGY,
            ACTION_SYMBOL,
            ACTION_CHART,
            ACTION_ENTER_TIME,
            ACTION_ENTER_PRICE,
            ACTION_MATCHED_PRICE,
            ACTION_MATCHED_TIME,
            ACTION_MATCHED_QTY,
            ACTION_SELL_PRICE,
            ACTION_SELL_TIME,
            ACTION_PROFIT,
            ACTION_EVENTPROFIT,
            ACTION_REALPROFIT,
            ACTION_PENDING,
            ACTION_PHASE,
            ACTION_BUDGET,
            ACTION_TYPE,
        ];

        $result = $this->mainModel->read($data, function ($db) use ($limit, $skip, $orderBy, $orderAsc) {
            if ($orderBy !== null) $db->orderBy($orderBy, $orderAsc ? 'ASC' : 'DESC');
            if ($skip !== null) $db->skip($skip);
            if ($limit !== null) $db->limit($limit);
        }, false, [
            PRICE_1S_ID,
            PRICE_1S_CLOSE,
            PRICE_1S_TIME
        ]);

        if (!$result['result']) return $result;
        $priceData = $result['data']->toArray();

        $positionData = [];
        $orderData = [];
        $enterBaseData = [];
        $profitBaseData = [];

        if (count($priceData) >= 100) {

            $endTime = $priceData[0]->{PRICE_1S_TIME};
            $startTime = $priceData[count($priceData) - 1]->{PRICE_1S_TIME};

            $positions = $positionModel->read([[
                [ACTION_ACCOUNT, '=', $account],
                [ACTION_SYMBOL, '=', $symbol],
                [ACTION_CHART, '>=', $startTime - 3*86400*1000],
                [ACTION_CHART, '<=', $endTime],
            ]], function ($db) {
                $db->orderBy(ACTION_CHART, 'DESC');
            }, false, $selectColumn);
            if (!$positions['result']) return $positions;
            $positions = $positions['data'];
            $ids = [];
            foreach ($positions as $position) {
                $ids[] = $position->{ACTION_ID};
                if($position->{ACTION_CHART} >= $startTime) $positionData[] = $position;
            }

            $orders = $orderModel->read([[
                [ORDER_TIME, '>=', $startTime],
                [ORDER_TIME, '<=', $endTime],
                [ORDER_QTY , '>', 0]
            ]], function ($db) use ($ids) {
                $db->whereIn(ORDER_ACTION, $ids)->orderBy(ORDER_TIME, 'DESC');
            });
            if (!$orders['result']) return $orders['result'];
            $orderData = $orders['data']->toArray();

            $enterBases = $enterBaseModel->read([[
                [LOG_ENTERBASE_TIME, '>=', $startTime],
                [LOG_ENTERBASE_TIME, '<=', $endTime],
            ]], function ($db) use ($ids) {
                $db->whereIn(LOG_ENTERBASE_ACTION, $ids)->orderBy(LOG_ENTERBASE_TIME, 'DESC');
            });
            if (!$enterBases['result']) return $enterBases['result'];
            $enterBaseData = $enterBases['data']->toArray();

            $profitBases = $profitBaseModel->read([[
                [LOG_PROFITBASE_TIME, '>=', $startTime],
                [LOG_PROFITBASE_TIME, '<=', $endTime],
            ]], function ($db) use ($ids) {
                $db->whereIn(LOG_PROFITBASE_ACTION, $ids)->orderBy(LOG_PROFITBASE_TIME, 'DESC');
            });
            if (!$profitBases['result']) return $profitBases['result'];
            $profitBaseData = $profitBases['data']->toArray();


        } else {

            $positions = $positionModel->read([[
                [ACTION_ACCOUNT, '=', $account],
                [ACTION_SYMBOL, '=', $symbol],
                [ACTION_CHART, '>=', $startTime - 3*86400*1000],
            ]], function ($db) {
                $db->orderBy(ACTION_CHART, 'DESC')->limit(1);
            }, false, $selectColumn);

            if (!$positions['result']) return $positions;
            $positions = $positions['data'];

            $ids = [];
            foreach ($positions as $position) {
                $ids[] = $position->{ACTION_ID};
                if($position->{ACTION_CHART} >= $startTime) $positionData[] = $position;
            }

            $orders = $orderModel->read([[[ORDER_TIME, '>=', $startTime], [ORDER_QTY , '>', 0]]], function ($db) use($ids) {
                $db->whereIn(ORDER_ACTION, $ids)->orderBy(ORDER_TIME, 'DESC');
            });
            if (!$orders['result']) return $orders['result'];
            $orderData = $orders['data']->toArray();


            $enterBases = $enterBaseModel->read([[[LOG_ENTERBASE_TIME, '>=', $startTime]]], function ($db) use($ids) {
                $db->whereIn(LOG_ENTERBASE_ACTION, $ids)->orderBy(LOG_ENTERBASE_TIME, 'DESC');
            });
            if (!$enterBases['result']) return $enterBases['result'];
            $enterBaseData = $enterBases['data']->toArray();

            $profitBases = $profitBaseModel->read([[[LOG_PROFITBASE_TIME, '>=', $startTime]]], function ($db) use($ids) {
                $db->whereIn(LOG_PROFITBASE_ACTION, $ids)->orderBy(LOG_PROFITBASE_TIME, 'DESC');
            });
            if (!$profitBases['result']) return $profitBases['result'];
            $profitBaseData = $profitBases['data']->toArray();
        }

        return Reply::make(true, 'Success', ['price' => $priceData, 'positions' => $positionData, 'orders' => $orderData, 'enterbase' => $enterBaseData, 'profitbase' => $profitBaseData]);
    }


    //

    //




}
